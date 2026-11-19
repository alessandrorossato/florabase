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
from starlette.convertors import (
    FloatConvertor,
    IntegerConvertor,
    PathConvertor,
    StringConvertor,
    UUIDConvertor,
)
from starlette.routing import PARAM_REGEX, Mount, Route, compile_path

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


@dataclass(frozen=True)
class RoutePattern:
    path: str
    methods: set[str] | None  # Mounts claim the matching prefix for every method.
    regex: re.Pattern[str]


def route_pattern(path: str, methods: set[str] | None) -> RoutePattern:
    regex, _, converters = compile_path(path)
    builtins = {
        "str": StringConvertor,
        "int": IntegerConvertor,
        "float": FloatConvertor,
        "uuid": UUIDConvertor,
        "path": PathConvertor,
    }
    for name, kind in PARAM_REGEX.findall(path):
        converter = converters[name]
        if type(converter) is not builtins.get(kind.removeprefix(":") or "str") or (
            converter.regex != type(converter).regex
        ):
            raise InventoryError(f"unsupported path converter at {path}")
    return RoutePattern(path, methods, regex)


def shadows(earlier: RoutePattern, later: RoutePattern) -> bool:
    if (
        earlier.methods is not None
        and later.methods is not None
        and earlier.methods.isdisjoint(later.methods)
    ):
        return False
    if not PARAM_REGEX.search(later.path):
        return earlier.regex.match(later.path) is not None
    if not PARAM_REGEX.search(earlier.path):
        # An exact match registered first reserves one URL from a later broader template.
        return False

    earlier_parts = earlier.path.split("/")
    later_parts = later.path.split("/")
    for left, right in zip(earlier_parts, later_parts, strict=False):
        if any(
            match[2] == ":path" for part in (left, right) for match in PARAM_REGEX.finditer(part)
        ):
            return True
        if not PARAM_REGEX.search(left) and not compile_path("/" + right)[0].fullmatch("/" + left):
            return False
        if not PARAM_REGEX.search(right) and not compile_path("/" + left)[0].fullmatch("/" + right):
            return False
        # For two variable segments keep looking for a disjoint literal or segment count.
        # Even Starlette's int and UUID patterns overlap on 32 decimal digits.
    return len(earlier_parts) == len(later_parts)


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
    application: FastAPI,
    prefix: str = "",
    ancestors: tuple[FastAPI, ...] = (),
    inherited_patterns: tuple[RoutePattern, ...] = (),
) -> Iterator[Operation]:
    if any(application is ancestor for ancestor in ancestors):
        raise InventoryError(f"recursive mount at {prefix or '/'}")
    if application.dependency_overrides:
        raise InventoryError(f"dependency overrides at {prefix or '/'}")

    prior_patterns = list(inherited_patterns)
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
            mount_pattern = route_pattern(path + "/{path:path}", None)
            yield from operations(route.app, path, (*ancestors, application), tuple(prior_patterns))
            # A Mount returns FULL at its prefix even if the child will return 404 or 405.
            prior_patterns.append(mount_pattern)
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
        pattern = route_pattern(path, methods)
        for prior in prior_patterns:
            if shadows(prior, pattern):
                shared_methods = methods if prior.methods is None else methods & prior.methods
                raise InventoryError(
                    f"duplicate or ambiguous operation: {', '.join(sorted(shared_methods))} {path} "
                    f"may be shadowed by earlier {prior.path}"
                )
        prior_patterns.append(pattern)
        for method in sorted(methods):
            if not re.fullmatch(r"[!#$%&'*+.^_`|~0-9A-Z-]+", method):
                raise InventoryError(f"invalid HTTP method at {path}")
            yield Operation(method, path, access)


def inventory(application: FastAPI) -> list[Operation]:
    return sorted(operations(application))


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
