"""Inventory the production FastAPI route table and enforce the ENG-03 public allowlist."""

import argparse
import json
import re
import sys
from collections import Counter
from collections.abc import Callable, Iterator
from dataclasses import asdict, dataclass
from enum import StrEnum

from fastapi import FastAPI
from fastapi.dependencies.models import Dependant
from fastapi.routing import APIRoute, iter_route_contexts
from starlette.routing import PARAM_REGEX, Mount, Route

from florabase.auth.dependencies import require_authenticated_actor, require_owner
from florabase.core.config import Environment, get_settings

# Reviewed against docs/release/acceptance-v1.md and the G-SEC release scope.
PUBLIC_OPERATIONS = frozenset(
    {
        ("POST", "/api/v1/auth/login"),  # Establishes the session.
        ("GET", "/api/v1/health"),  # Liveness probe.
        ("GET", "/api/v1/ready"),  # Readiness probe.
    }
)


class InventoryError(ValueError):
    pass


class Access(StrEnum):
    PUBLIC = "public"
    AUTHENTICATED = "authenticated"
    OWNER_RESTRICTED = "owner-restricted"


@dataclass(frozen=True, order=True)
class Operation:
    method: str
    path: str
    declared_access: Access


def dependencies(dependant: Dependant) -> Iterator[Dependant]:
    for child in dependant.dependencies:
        yield child
        yield from dependencies(child)


def declared_access(dependant: Dependant) -> Access:
    nodes = list(dependencies(dependant))
    if not any(node.call is require_authenticated_actor for node in nodes):
        return Access.PUBLIC
    for node in nodes:
        if node.call is require_owner and any(
            child.name == "actor" and child.call is require_authenticated_actor
            for child in node.dependencies
        ):
            return Access.OWNER_RESTRICTED
    return Access.AUTHENTICATED


def operations(
    application: FastAPI, prefix: str = "", ancestors: tuple[FastAPI, ...] = ()
) -> Iterator[Operation]:
    if any(application is ancestor for ancestor in ancestors):
        raise InventoryError(f"recursive mount at {prefix or '/'}")
    if application.dependency_overrides:
        raise InventoryError(f"dependency overrides at {prefix or '/'}")

    for context in iter_route_contexts(application.routes):
        route = context.route
        if context.path is None:
            raise InventoryError(
                f"unsupported route type {type(route).__name__} at {prefix or '/'}"
            )
        path = prefix + context.path
        if isinstance(route, Mount):
            if not isinstance(route.app, FastAPI):
                raise InventoryError(f"opaque mount at {path or '/'}")
            yield from operations(route.app, path, (*ancestors, application))
            continue
        if isinstance(route, APIRoute):
            provider = context.dependency_overrides_provider
            if getattr(provider, "dependency_overrides", None):
                raise InventoryError(f"dependency overrides at {path}")
            dependant = context.dependant
            if not isinstance(dependant, Dependant):
                raise InventoryError(f"missing dependency graph at {path}")
            access = declared_access(dependant)
        elif type(route) is Route:
            access = Access.PUBLIC
        else:
            raise InventoryError(f"unsupported route type {type(route).__name__} at {path}")

        methods = context.methods
        if not path.startswith("/") or not methods:
            raise InventoryError(f"missing path or HTTP methods at {path or '/'}")
        for method in sorted(methods):
            if not re.fullmatch(r"[!#$%&'*+.^_`|~0-9A-Z-]+", method):
                raise InventoryError(f"invalid HTTP method at {path}")
            yield Operation(method, path, access)


def inventory(application: FastAPI) -> list[Operation]:
    by_template: dict[tuple[str, str], Operation] = {}
    for operation in operations(application):
        # Parameter names do not affect matching. Conservatively flag matching shapes even
        # when their converters differ. Preserve the actual templates and trailing slashes.
        key = (operation.method, PARAM_REGEX.sub("{}", operation.path))
        if key in by_template:
            prior = by_template[key]
            raise InventoryError(
                f"duplicate or ambiguous operation: {operation.method} "
                f"{prior.path} and {operation.path}"
            )
        by_template[key] = operation
    return sorted(by_template.values())


def production_application() -> FastAPI:
    if get_settings().environment is not Environment.PRODUCTION:
        raise InventoryError("expected FLORABASE_ENVIRONMENT=production")

    from florabase.main import app

    return app


def run_check(build_app: Callable[[], FastAPI], *, output_format: str) -> int:
    try:
        rows = inventory(build_app())
    except Exception as error:
        # Framework startup errors can include settings values. Only report their type.
        reason = str(error) if isinstance(error, InventoryError) else type(error).__name__
        if output_format == "json":
            sys.stdout.write(
                json.dumps({"status": "error", "error": reason}, sort_keys=True) + "\n"
            )
        else:
            sys.stderr.write(f"API route inventory incomplete: {reason}\n")
        return 2

    public = {(row.method, row.path) for row in rows if row.declared_access is Access.PUBLIC}
    unexpected = sorted(public - PUBLIC_OPERATIONS)
    stale = sorted(PUBLIC_OPERATIONS - public)
    status = "fail" if unexpected or stale else "pass"
    counts = Counter(row.declared_access for row in rows)
    summary = {access.value: counts[access] for access in Access}
    if output_format == "json":
        report = {
            "status": status,
            "operations": [asdict(row) for row in rows],
            "counts": {"total": len(rows), **summary},
            "unexpected_public": [{"method": method, "path": path} for method, path in unexpected],
            "stale_allowlist": [{"method": method, "path": path} for method, path in stale],
        }
        sys.stdout.write(json.dumps(report, indent=2, sort_keys=True) + "\n")
    else:
        for row in rows:
            sys.stdout.write(f"{row.method:7} {row.path} [{row.declared_access}]\n")
        for label, violations in (("unexpected public", unexpected), ("stale allowlist", stale)):
            for method, path in violations:
                sys.stderr.write(f"{label}: {method} {path}\n")
        totals = ", ".join(f"{count} {access}" for access, count in summary.items())
        sys.stdout.write(f"ENG-03 {status.upper()}: {len(rows)} operations ({totals})\n")
    return 1 if status == "fail" else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args()
    return run_check(production_application, output_format=args.format)


if __name__ == "__main__":
    raise SystemExit(main())
