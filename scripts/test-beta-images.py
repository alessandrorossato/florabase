#!/usr/bin/env python3
"""Adversarial release-identity and publication-boundary regressions, without Docker."""

from __future__ import annotations

import ast
import base64
import copy
import email.message
import hashlib
import importlib.util
import io
import json
import os
import re
import subprocess
import sys
import tarfile
import tempfile
import textwrap
import unittest
import urllib.error
import urllib.parse
import urllib.request
import urllib.response
from contextlib import nullcontext
from http.client import HTTPMessage
from pathlib import Path
from typing import Any, ClassVar
from unittest.mock import Mock, patch

import beta_release
from beta_release import (
    build_application_image,
    check_platform,
    compose_template,
    inputs,
    read,
    registry_record,
    release_attestation_inputs,
    release_finalization_inputs,
    save_postgres_oci_evidence,
    saved_descriptors,
    validate_manifest,
    validate_release_assets,
    validate_scan,
)
from smoke_beta_runtime_client import Client

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("checks", ROOT / "scripts/beta-release-checks.py")
assert spec and spec.loader
checks = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checks)


def load_tool(name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / (name + ".py"))
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


tooling = load_tool("release-tools")
publisher = load_tool("publish-beta-images")


class PortableSmokeHeaders(unittest.TestCase):
    smoke: ClassVar[Any]

    @classmethod
    def setUpClass(cls) -> None:
        cls.smoke = load_tool("smoke-portable-compose")

    def setUp(self) -> None:
        self.headers = HTTPMessage()
        self.headers["X-Content-Type-Options"] = "nosniff"
        self.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        self.headers["X-Frame-Options"] = "DENY"
        self.headers["Content-Security-Policy"] = (
            "default-src 'none'; script-src 'self'; style-src 'self'; style-src-attr 'unsafe-inline'; "
            "img-src 'self' data: blob: https:; font-src 'self'; connect-src 'self'; "
            "manifest-src 'self'; worker-src 'self'; object-src 'none'; base-uri 'none'; "
            "form-action 'self'; frame-ancestors 'none'"
        )
        self.client = Mock(spec=Client)
        self.client.request.return_value = (b"", self.headers)

    def test_missing_security_headers_fail_public_smoke(self) -> None:
        for name, value in self.headers.items():
            with self.subTest(name=name):
                del self.headers[name]
                with self.assertRaisesRegex(RuntimeError, rf"GET /: expected {name}"):
                    self.smoke.exercise_bundled_headers(self.client)
                self.headers[name] = value

    def test_incorrect_security_headers_fail_public_smoke(self) -> None:
        for name, value in self.headers.items():
            with self.subTest(name=name):
                self.headers.replace_header(name, "incorrect")
                with self.assertRaisesRegex(RuntimeError, rf"GET /: expected {name}"):
                    self.smoke.exercise_bundled_headers(self.client)
                self.headers.replace_header(name, value)

    def test_duplicate_nosniff_fails_authenticated_thumbnail_smoke(self) -> None:
        self.headers["Cache-Control"] = "private, max-age=86400, must-revalidate"
        self.headers["x-content-type-options"] = "nosniff"
        with self.assertRaisesRegex(RuntimeError, "X-Content-Type-Options"):
            self.smoke.exercise_authenticated_thumbnail(self.client, "/thumbnail")

    def test_missing_incorrect_and_duplicate_cache_fail(self) -> None:
        for values in ([], ["public"], ["no-cache", "no-cache"]):
            with self.subTest(values=values):
                for value in values:
                    self.headers["Cache-Control"] = value
                with self.assertRaisesRegex(RuntimeError, "GET /: expected Cache-Control"):
                    self.smoke.exercise_bundled_headers(self.client)
                del self.headers["Cache-Control"]

    def test_unexpected_cache_header_fails(self) -> None:
        self.headers["Cache-Control"] = "public"
        with self.assertRaisesRegex(RuntimeError, "GET /healthz: expected Cache-Control"):
            self.smoke.require_response_header("/healthz", self.headers, "Cache-Control", None)

    def test_valid_headers_and_cache_pass(self) -> None:
        self.smoke.require_bundled_headers("/", self.headers)
        self.smoke.require_response_header("/healthz", self.headers, "Cache-Control", None)
        self.headers["Cache-Control"] = "private, max-age=86400, must-revalidate"
        with patch("sys.stdout", new=io.StringIO()):
            self.smoke.exercise_authenticated_thumbnail(self.client, "/thumbnail")
        self.client.request.assert_called_once_with("/thumbnail")


class PortableSmokeEvidence(unittest.TestCase):
    smoke: ClassVar[Any]
    images: ClassVar[dict[str, str]] = {
        "db": "postgres-fixture",
        "backend": "backend-fixture",
        "frontend": "frontend-fixture",
    }
    head = "20261009_0042"
    media_id = "00000000-0000-7000-8000-000000000000"
    content_url = f"/api/v1/attachments/{media_id}/content"
    thumbnail_url = f"/api/v1/media-assets/{media_id}/thumbnail"
    verified = b"Verified 1 stored attachment file(s) against database metadata\n"

    @classmethod
    def setUpClass(cls) -> None:
        cls.smoke = load_tool("smoke-portable-compose")

    def config(
        self,
        images: dict[str, str],
        *,
        names: dict[str, str] | None = None,
        users: dict[str, str] | None = None,
        networks: dict[str, Any] | None = None,
        service_networks: dict[str, dict[str, Any]] | None = None,
    ) -> bytes:
        container_names = names if names is not None else self.smoke.CONTAINER_NAMES
        default_service_networks: dict[str, dict[str, Any]] = {
            "db": {"internal": None},
            "backend": {"internal": None, "app": None},
            "frontend": {"app": None},
        }
        if service_networks:
            default_service_networks.update(service_networks)
        services: dict[str, Any] = {
            name: {
                "image": ref,
                "container_name": container_names.get(name),
                "networks": default_service_networks.get(name, {}),
            }
            for name, ref in images.items()
        }
        for name, user in (users or {}).items():
            services[name]["user"] = user
        top_networks = networks if networks is not None else {"default": {}}
        return json.dumps({"services": services, "networks": top_networks}).encode()

    def stack(self, directory: Path) -> Any:
        return self.smoke.Stack(directory / "source", directory / "c.yaml", "fixture", self.images)

    def test_service_evidence_requires_the_three_images_names_and_non_root_services(self) -> None:
        latest = self.smoke.LATEST_IMAGES
        images = {
            "db": "postgres-fixture",
            "backend": "backend-fixture",
            "frontend": "frontend-fixture",
        }
        with tempfile.TemporaryDirectory() as temporary:
            stack = self.stack(Path(temporary))
            for config, message in (
                (self.config({"db": latest["db"]}), "expected db, backend, frontend"),
                (
                    self.config(latest, networks={"internal": {"internal": True}, "app": {}}),
                    "expected default network only",
                ),
                (self.config({**latest, "frontend": "other"}), "incorrect frontend image"),
                (
                    self.config(latest, names={**self.smoke.CONTAINER_NAMES, "db": "other"}),
                    "incorrect db image",
                ),
                (self.config(latest, users={"backend": "0:0"}), "incorrect backend image"),
            ):
                with (
                    self.subTest(message=message),
                    patch.object(stack, "compose", return_value=config),
                    self.assertRaisesRegex(RuntimeError, message),
                ):
                    self.smoke.require_services(stack, images)
            with (
                patch.object(
                    stack,
                    "compose",
                    side_effect=[self.config(latest), self.config({**images, "frontend": "other"})],
                ),
                self.assertRaisesRegex(RuntimeError, "Override configuration: incorrect frontend"),
            ):
                self.smoke.require_services(stack, images)
            with patch.object(
                stack,
                "compose",
                side_effect=[self.config(latest), self.config(images)],
            ):
                self.smoke.require_services(stack, images)

    def test_refusal_requires_a_failed_deployment_and_the_service_message(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            stack = self.stack(Path(temporary))
            for code, logs, message in (
                (0, b"refused: marker", "was not refused"),
                (1, b"another reason", "expected 'marker'"),
            ):
                with (
                    self.subTest(code=code),
                    patch.object(
                        self.smoke, "run", return_value=subprocess.CompletedProcess([], code)
                    ),
                    patch.object(stack, "compose", return_value=logs),
                    self.assertRaisesRegex(RuntimeError, message),
                ):
                    stack.refuse("db", "marker", "probe")
            with (
                patch.object(self.smoke, "run", return_value=subprocess.CompletedProcess([], 1)),
                patch.object(stack, "compose", return_value=b"REFUSED: marker") as compose,
            ):
                stack.refuse("db", "marker", "probe")
            compose.assert_called_with("stop")

    def test_secret_evidence_covers_every_service_log(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            stack = self.stack(Path(temporary))
            with patch.object(stack, "compose", return_value=b"x secret-canary y") as compose:
                with self.assertRaisesRegex(RuntimeError, "probe: secret in logs") as error:
                    self.smoke.require_no_secret(stack, ("secret-canary",), "probe")
                self.assertNotIn("canary", str(error.exception))
            compose.assert_called_once_with("logs", "--no-color", *self.smoke.SERVICES)

    def test_login_requires_json_csrf_and_a_usable_secure_cookie(self) -> None:
        client = Client("http://127.0.0.1:8080", self.smoke.ORIGIN)
        headers = HTTPMessage()
        headers["Set-Cookie"] = (
            "__Host-florabase-session=session-token; HttpOnly; Max-Age=2592000; Path=/; SameSite=strict; Secure"
        )
        valid = b'{"csrf_token":"csrf-token"}'
        for data, response_headers, message in (
            (b"not-json", headers, "invalid JSON response"),
            (b"[]", headers, "expected a JSON object"),
            (b"{}", headers, "missing or invalid CSRF token"),
            (b'{"csrf_token":123}', headers, "missing or invalid CSRF token"),
            (valid, HTTPMessage(), "missing or invalid secure session cookie"),
        ):
            with (
                self.subTest(message=message, data=data),
                patch.object(client, "request", return_value=(data, response_headers)),
                self.assertRaisesRegex(RuntimeError, message),
            ):
                client.login("owner", "password-fixture")
        self.assertEqual((client.cookie, client.csrf), ("", ""))
        with patch.object(client, "request", return_value=(valid, headers)):
            client.login("owner", "password-fixture")
        self.assertEqual(
            (client.cookie, client.csrf), ("__Host-florabase-session=session-token", "csrf-token")
        )

    def test_session_cookie_definitions_are_unambiguous(self) -> None:
        client = Client("http://127.0.0.1:8080", self.smoke.ORIGIN)
        cookie = "__Host-florabase-session"
        # Match the pinned backend serializer's secure login and password-change output.
        issued = (
            f"{cookie}=issued-fixture; HttpOnly; Max-Age=2592000; Path=/; SameSite=strict; Secure"
        )
        positive = {
            "backend": (issued,),
            "ordering, casing and horizontal whitespace": (
                f"\t{cookie}=issued-fixture ;\tSECURE ; sAmEsItE=STRICT; PATH=/ ; max-age=86400; httpONLY\t",
            ),
            "unrelated cookies": (
                'preferences="__Host-florabase-session=unrelated;theme=dark"',
                issued,
                "view=compact; Path=/",
            ),
        }
        for case, fields in positive.items():
            with self.subTest(case=case):
                headers = HTTPMessage()
                for field in fields:
                    headers.add_header("Set-Cookie", field)
                client.accept_session(b'{"csrf_token":"accepted-csrf"}', headers, "login")
                self.assertEqual(
                    (client.cookie, client.csrf), (f"{cookie}=issued-fixture", "accepted-csrf")
                )

        insecure = f"{cookie}=unvalidated-fixture; Path=/"
        duplicate = issued.replace("issued-fixture", "unvalidated-fixture")
        rejected = {
            "valid then insecure": (issued, insecure),
            "insecure then valid": (insecure, issued),
            "two valid tokens": (issued, duplicate),
            "same token twice": (issued, issued),
            "combined definitions": (issued + "; " + insecure,),
            "comma-separated definitions": (issued + ", " + duplicate,),
            "space-separated definitions": (issued + " " + duplicate,),
            "malformed second definition": (issued, cookie + "; Secure"),
            "missing session": (),
        }
        for case, original, malformed in (
            ("SOL path", "Path=/", "Path=/other Path=/"),
            ("SOL SameSite", "SameSite=strict", "SameSite=Lax SameSite=Strict"),
            ("reversed path", "Path=/", "Path=/ Path=/other"),
            ("reversed SameSite", "SameSite=strict", "SameSite=Strict SameSite=Lax"),
            ("identical path", "Path=/", "Path=/; PATH=/"),
            ("identical flag", "Secure", "Secure; SECURE"),
            ("conflicting paths", "Path=/", "Path=/other; Path=/"),
            ("conflicting SameSite", "SameSite=strict", "SameSite=Lax; SameSite=Strict"),
            ("valued Secure", "Secure", "Secure=1"),
            ("empty Secure assignment", "Secure", "Secure="),
            ("valued HttpOnly", "HttpOnly", "HttpOnly=true"),
            ("invalid path", "Path=/", "Path=/other"),
            ("invalid SameSite", "SameSite=strict", "SameSite=Lax"),
            ("invalid Max-Age", "Max-Age=2592000", "Max-Age=0"),
            ("embedded assignment", "Max-Age=2592000", "Max-Age=2592000 Expires=tomorrow"),
            ("tab-separated assignment", "Path=/", "Path=/other\tPath=/"),
            ("whitespace inside assignment", "Path=/", "Path= /"),
            ("vertical whitespace", "Path=/", "Path=/\v"),
            ("quoted token", "issued-fixture", '"issued-fixture"'),
            ("quoted path", "Path=/", 'Path="/"'),
            ("quoted semicolon", "Path=/", 'Path="/;other=value"'),
            ("empty token", "issued-fixture", ""),
        ):
            rejected[case] = (issued.replace(original, malformed),)
        for attribute in ("HttpOnly", "Max-Age=2592000", "Path=/", "SameSite=strict", "Secure"):
            rejected[f"missing {attribute}"] = (issued.replace(f"; {attribute}", ""),)
        for extra in ("Domain=", "$Domain=fixture.invalid", "Unexpected=value", ""):
            rejected[f"extra attribute {extra!r}"] = (issued + "; " + extra,)

        for case, fields in rejected.items():
            with self.subTest(case=case):
                headers = HTTPMessage()
                for field in fields:
                    headers.add_header("Set-Cookie", field.replace("issued-fixture", "new-fixture"))
                with self.assertRaisesRegex(RuntimeError, "session cookie"):
                    client.accept_session(b'{"csrf_token":"unvalidated-csrf"}', headers, "login")
                self.assertEqual(
                    (client.cookie, client.csrf), (f"{cookie}=issued-fixture", "accepted-csrf")
                )

        response = urllib.response.addinfourl(io.BytesIO(b"ok"), HTTPMessage(), client.base, 200)
        with patch.object(client.opener, "open", return_value=response) as transport:
            client.request("/session", "POST")
        request = transport.call_args.args[0]
        self.assertEqual(request.get_header("Cookie"), f"{cookie}=issued-fixture")
        self.assertEqual(request.get_header("X-csrf-token"), "accepted-csrf")

    def test_protocol_failures_exit_with_sanitized_tracebacks(self) -> None:
        child = textwrap.dedent("""\
            import io
            import sys
            from http.client import HTTPException, HTTPResponse
            from unittest.mock import Mock, patch

            from smoke_beta_runtime_client import Client

            case, marker = sys.argv[1:]
            wire = (
                (marker + "\\r\\n\\r\\n").encode() if case == "status" else
                b"HTTP/1.1 200 OK\\r\\nContent-Length: 256\\r\\n\\r\\n" + marker.encode()
            )
            sock = Mock()
            sock.makefile.return_value = io.BytesIO(wire)
            def open_response(*args, **kwargs):
                response = HTTPResponse(sock)
                response.begin()
                if case == "read":
                    response.read = Mock(side_effect=HTTPException(marker))
                return response

            client = Client("http://127.0.0.1:8080", "https://fixture.invalid")
            with patch.object(client.opener, "open", side_effect=open_response):
                client.request("/status?check=" + marker)
            print("unexpected success")
            """)
        marker = "synthetic-protocol-secret-marker"
        for case in ("status", "truncated", "read"):
            with self.subTest(case=case):
                result = subprocess.run(
                    [sys.executable, *(["-O"] * sys.flags.optimize), "-c", child, case, marker],
                    cwd=ROOT / "scripts",
                    capture_output=True,
                    text=True,
                    timeout=15,
                    check=False,
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout, "")
                self.assertIn("Traceback (most recent call last)", result.stderr)
                self.assertIn("RuntimeError: GET /status: invalid HTTP response", result.stderr)
                self.assertNotIn(marker, result.stderr)
                self.assertNotIn("During handling of the above exception", result.stderr)

    def test_expected_http_success_and_error_return_body_and_headers(self) -> None:
        client = Client("http://127.0.0.1:8080", self.smoke.ORIGIN)
        headers = HTTPMessage()
        body = b'{"fixture":"body"}'
        response = urllib.response.addinfourl(io.BytesIO(body), headers, client.base, 200)
        refused = urllib.error.HTTPError(client.base, 401, "fixture", headers, io.BytesIO(body))
        with patch.object(client.opener, "open", side_effect=[response, refused]):
            self.assertEqual(client.request("/ready"), (body, headers))
            self.assertEqual(client.request("/session", expected=401), (body, headers))

    def test_password_change_and_reset_require_complete_secret_free_evidence(self) -> None:
        initial_password = "original-password-fixture"
        changed_password = "changed-password-fixture"
        reset_password = "reset-password-fixture"
        path = b"/api/v1/auth/password"
        owner = json.dumps(
            {"owner": True, "login_name": self.smoke.OWNER, "canonical_origin": self.smoke.ORIGIN}
        ).encode()
        headers = HTTPMessage()
        headers["Set-Cookie"] = (
            "__Host-florabase-session=rotated-session; HttpOnly; Max-Age=2592000; Path=/; SameSite=strict; Secure"
        )

        for fault, message in {
            "": "",
            "rotation": "session credentials did not rotate",
            "session": "incorrect owner",
            "revocation": "expected 401, got 200",
            "logs": "backend: credential access log evidence is incomplete",
            "log-secret": "backend: sensitive value in credential logs",
            "reset": "missing commit confirmation",
        }.items():
            with self.subTest(fault=fault):
                first = Client("http://127.0.0.1:8080", self.smoke.ORIGIN)
                first.cookie = "__Host-florabase-session=original-session"
                first.csrf = "original-csrf"
                other = Mock(
                    spec=Client, cookie="__Host-florabase-session=other-session", csrf="other-csrf"
                )
                if fault == "revocation":
                    other.request.side_effect = RuntimeError(
                        "GET /api/v1/auth/session: expected 401, got 200"
                    )
                stack = Mock(spec=self.smoke.Stack)
                stack.login.side_effect = [first, other, Mock(spec=Client), Mock(spec=Client)]
                frontend_logs = path + b"\n" + path
                backend_logs = b"" if fault == "logs" else frontend_logs
                if fault == "log-secret":
                    backend_logs += b" auth-query-query-fixture"
                stack.compose.side_effect = [frontend_logs, backend_logs, b""]
                stack.backend.return_value = {
                    "reset": b"no evidence",
                }.get(fault, b"Owner password reset committed. Sign in again.\n")
                csrf = b"original-csrf" if fault == "rotation" else b"rotated-csrf"
                response = [
                    (b'{"csrf_token":"' + csrf + b'"}', headers),
                    (b"{}" if fault == "session" else owner, headers),
                    (b"", headers),
                ]
                with (
                    patch.object(first, "request", side_effect=response),
                    patch.object(first, "json"),
                    patch.object(
                        self.smoke.secrets,
                        "token_hex",
                        side_effect=[changed_password, reset_password, "query-fixture"],
                    ),
                ):
                    if message:
                        with self.assertRaisesRegex(RuntimeError, message) as error:
                            self.smoke.exercise_credentials(stack, initial_password)
                        self.assertNotIn("-fixture", str(error.exception))
                    else:
                        self.assertEqual(
                            self.smoke.exercise_credentials(stack, initial_password), reset_password
                        )
                        other.request.assert_called_once_with("/api/v1/auth/session", expected=401)
                        stack.login.assert_called_with(reset_password)
                        self.assertEqual(
                            stack.backend.call_args.kwargs["secret"], reset_password.encode()
                        )

    def test_http_status_and_diagnostics_do_not_accept_redirect_or_leak_values(self) -> None:
        class Response(urllib.response.addinfourl):
            msg = "fixture"

        client = Client("http://127.0.0.1:8080", self.smoke.ORIGIN)
        path = "/api/v1/auth/password"
        headers = HTTPMessage()
        headers["Location"] = "/success-after-redirect"
        for status in (302, 401, 500):
            response = Response(io.BytesIO(b"body-canary"), headers, client.base + path, status)
            success = Response(
                io.BytesIO(b"ok"), HTTPMessage(), client.base + "/success-after-redirect", 200
            )
            with (
                response,
                success,
                self.subTest(status=status),
                patch.object(
                    urllib.request.HTTPHandler, "http_open", side_effect=[response, success]
                ) as transport,
                self.assertRaisesRegex(RuntimeError, f"expected 200, got {status}") as error,
            ):
                # Build the opener while its transport is patched so the real redirect logic runs.
                Client(client.base, self.smoke.ORIGIN).request(path + "?token=query-canary")
            self.assertNotIn("canary", str(error.exception))
            self.assertEqual(transport.call_count, 1)

    def test_compose_requires_subprocess_status_and_refusal_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            stack = self.smoke.Stack(
                directory / "source", directory / "asset.yaml", "fixture", self.images
            )
            for code, stderr, refusal in (
                (4, b"stderr-canary", None),
                (0, b"expected marker stderr-canary", "expected marker"),
                (1, b"stderr-canary", "expected marker"),
                (125, b"expected marker stderr-canary", "expected marker"),
            ):
                with (
                    self.subTest(code=code, refusal=refusal),
                    patch.object(
                        self.smoke,
                        "run",
                        return_value=subprocess.CompletedProcess(
                            [], code, b"stdout-canary", stderr
                        ),
                    ),
                    self.assertRaisesRegex(RuntimeError, rf"compose run.*exit {code}") as error,
                ):
                    stack.backend("fixture", failure=refusal)
                self.assertNotIn("canary", str(error.exception))
            for code, refusal in ((0, None), (1, "expected marker")):
                with patch.object(
                    self.smoke,
                    "run",
                    return_value=subprocess.CompletedProcess(
                        [], code, b"payload", b"expected marker"
                    ),
                ):
                    self.assertEqual(stack.backend("fixture", failure=refusal), b"payload")
            for stdout, stderr in ((b"secret-canary", b""), (b"", b"secret-canary")):
                with (
                    patch.object(
                        self.smoke,
                        "run",
                        return_value=subprocess.CompletedProcess([], 0, stdout, stderr),
                    ),
                    self.assertRaisesRegex(
                        RuntimeError, "offline password reset: password in output"
                    ) as error,
                ):
                    stack.backend(
                        "fixture", check="offline password reset", secret=b"secret-canary"
                    )
                self.assertNotIn("canary", str(error.exception))

    def test_publisher_passes_trusted_inputs_and_propagates_smoke_exit(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "scripts").mkdir()
            child = root / "scripts/smoke-portable-compose.py"
            child.write_text(
                "import json, sys\nprint(json.dumps(sys.argv[1:]))\nraise SystemExit(7)\n"
            )
            log = root / "portable.log"
            asset = root / "portable-compose.yaml"
            with self.assertRaises(subprocess.CalledProcessError) as error:
                publisher.run_portable_smoke(
                    root, asset, {**self.images, "postgresql": self.images["db"]}, self.head, log
                )
            self.assertEqual(error.exception.returncode, 7)
            self.assertEqual(
                json.loads(log.read_text()),
                [
                    str(asset),
                    self.images["backend"],
                    "--frontend-image",
                    self.images["frontend"],
                    "--postgres-image",
                    self.images["db"],
                    "--alembic-head",
                    self.head,
                ],
            )


class PortableSmokeOptimization(unittest.TestCase):
    def test_portable_controls_are_independent_of_python_optimization(self) -> None:
        for flags, env_override in ((["-O"], {}), ([], {"PYTHONOPTIMIZE": "1"})):
            with self.subTest(flags=flags, env_override=env_override):
                env = {key: value for key, value in os.environ.items() if key != "PYTHONOPTIMIZE"}
                env.update(env_override)
                # Select only the portable controls so the child cannot run this launcher again.
                result = subprocess.run(
                    [
                        sys.executable,
                        *flags,
                        __file__,
                        "PortableSmokeHeaders",
                        "PortableSmokeEvidence",
                    ],
                    env=env,
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=30,
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


def policy() -> dict[str, Any]:
    return {
        "candidate_platform": "linux/amd64",
        "publication": {"host_approval_required": False},
        "deployment_acceptance": {"status": "pending"},
    }


def candidate() -> dict[str, Any]:
    locked = inputs(ROOT)
    ref = "ghcr.io/alessandrorossato/florabase-backend@sha256:" + "a" * 64
    image = {
        "reference": ref,
        "index_digest": "sha256:" + "a" * 64,
        "platform_digest": "sha256:" + "b" * 64,
        "platform": "linux/amd64",
    }
    return {
        "schema_version": 3,
        "distribution": "registry-candidate",
        "version": locked["version"],
        "source": {
            "url": "https://github.com/alessandrorossato/florabase",
            "revision": "c" * 40,
            "dirty": False,
        },
        "platforms": ["linux/amd64"],
        "alembic_head": "20261013_0042",
        "images": {
            "backend": image,
            "frontend": {
                **image,
                "reference": ref.replace("backend", "frontend").replace("a" * 64, "d" * 64),
                "index_digest": "sha256:" + "d" * 64,
                "platform_digest": "sha256:" + "e" * 64,
            },
        },
        "postgresql": locked["postgresql"],
        "compose_template": compose_template(ROOT),
        "build_inputs": locked,
        "workflow": {"run_id": "1", "run_attempt": "1"},
    }


class ReleaseTests(unittest.TestCase):
    def test_current_candidate_inputs_and_platform_policy(self) -> None:
        self.assertEqual(
            inputs(ROOT)["buildkit"],
            "moby/buildkit:v0.34.2@sha256:c5f8862f52499773af85bc07695b2379ef08e8002352b0df2c4864c91d78dabe",
        )
        committed = json.loads((ROOT / "release/platform.json").read_text())
        check_platform(committed)
        inputs(ROOT, publication=True)
        # Publication does not depend on any host; actual-host acceptance is not claimed.
        self.assertEqual(committed["deployment_acceptance"]["status"], "pending")
        self.assertNotIn("host", committed)
        self.assertNotIn("operator", committed)

    def test_release_channels_match_manifest_compose_and_draft_command(self) -> None:
        for version, prerelease in (
            ("0.1.0-beta.42", True),
            ("1.0.0-rc.1", True),
            ("1.0.0", False),
        ):
            with self.subTest(version=version):
                value = candidate()
                value["version"] = value["build_inputs"]["version"] = version
                with patch(
                    "beta_release.read",
                    side_effect=lambda path, locked=value["build_inputs"]: (
                        locked if path.name == "inputs.json" else read(path)
                    ),
                ):
                    validate_manifest(value)
                names = (
                    "RELEASE.md",
                    "release-manifest.json",
                    beta_release.POSTGRES_SBOM,
                    f"florabase-{version}-source.tar.gz",
                )
                inventory = {name: (42, "sha256:" + "a" * 64) for name in names}
                request = release_finalization_inputs(value, value["source"]["revision"], inventory)
                self.assertEqual(request["tag"], f"v{version}")
                self.assertIs(request["prerelease"], prerelease)
                command = publisher.release_create_command(request, Path("/tmp/assets"))
                self.assertEqual("--prerelease" in command, prerelease)
                self.assertIn("--draft", command)
                self.assertIn("--verify-tag", command)
        for version in ("0.1.0", "1.0.0-rc.0", "1.0.0-rc.01", "1.0.0-beta.1", "latest"):
            with self.subTest(version=version), self.assertRaises(ValueError):
                value = candidate()
                value["version"] = value["build_inputs"]["version"] = version
                validate_manifest(value)

    def test_v1_scope_requires_supported_flag_and_propagates_checker_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            scripts = root / "scripts"
            scripts.mkdir()
            checker = scripts / "check-features.py"
            beta_release.require_release_scope(root, "0.1.0-beta.6")
            checker.write_text("print('feature graph valid')\n")
            with self.assertRaisesRegex(ValueError, "DOC-02 checker"):
                beta_release.require_release_scope(root, "1.0.0-rc.1")
            checker.write_text(
                "import sys\n"
                "if sys.argv[1:] == ['--help']:\n"
                "    print('--release-candidate')\n"
                "else:\n"
                "    if sys.argv[1:] != ['--release-candidate']:\n"
                "        sys.exit(2)\n"
                "    sys.exit(3)\n"
            )
            with self.assertRaises(subprocess.CalledProcessError) as error:
                beta_release.require_release_scope(root, "1.0.0-rc.1")
            self.assertEqual(error.exception.returncode, 3)
            checker.write_text(checker.read_text().replace("sys.exit(3)", "sys.exit(0)"))
            beta_release.require_release_scope(root, "1.0.0")

    def test_postgres_oci_evidence_hash_checks_index_manifest_and_config(self) -> None:
        config = json.dumps({"created": "2025-11-06T00:00:00Z"}, separators=(",", ":")).encode()
        config_digest = "sha256:" + hashlib.sha256(config).hexdigest()
        platform = {
            "schemaVersion": 2,
            "mediaType": "application/vnd.oci.image.manifest.v1+json",
            "config": {"digest": config_digest, "size": len(config)},
            "layers": [{"digest": "sha256:" + "a" * 64, "size": 42}],
        }
        platform_raw = json.dumps(platform, separators=(",", ":")).encode()
        platform_digest = "sha256:" + hashlib.sha256(platform_raw).hexdigest()
        index = {
            "schemaVersion": 2,
            "mediaType": "application/vnd.oci.image.index.v1+json",
            "manifests": [
                {
                    "mediaType": "application/vnd.oci.image.manifest.v1+json",
                    "digest": platform_digest,
                    "size": len(platform_raw),
                    "platform": {"architecture": "amd64", "os": "linux"},
                }
            ],
        }
        index_raw = json.dumps(index, separators=(",", ":")).encode()
        index_digest = "sha256:" + hashlib.sha256(index_raw).hexdigest()
        with tempfile.TemporaryDirectory() as temporary:
            with (
                patch(
                    "beta_release.subprocess.check_output",
                    side_effect=[index_raw + b"\n", platform_raw + b"\n"],
                ),
                patch(
                    "beta_release.run",
                    return_value=json.dumps({"digest": index_digest}),
                ),
                patch("beta_release.urllib.request.urlopen", return_value=FakeResponse(config, {})),
            ):
                save_postgres_oci_evidence(
                    "127.0.0.1:5055/florabase-postgres:18.6-alpine-florabase.1",
                    5055,
                    Path(temporary),
                )
            evidence = json.loads((Path(temporary) / "postgres-oci-evidence.json").read_text())
        self.assertEqual(evidence["index_digest"], index_digest)
        self.assertEqual(evidence["platform_digest"], platform_digest)
        self.assertEqual(evidence["configuration_digest"], config_digest)
        self.assertEqual(evidence["layer_descriptors"], platform["layers"])
        raw = evidence["raw_documents_base64"]
        self.assertEqual(base64.b64decode(raw["index"]), index_raw)
        self.assertEqual(base64.b64decode(raw["platform_manifest"]), platform_raw)
        self.assertEqual(base64.b64decode(raw["configuration"]), config)

    def test_production_build_keeps_disposable_registry_port_in_digest_reference(self) -> None:
        digest = "sha256:" + "a" * 64
        with tempfile.TemporaryDirectory() as temporary:
            metadata = Path(temporary) / "metadata.json"

            def build(*args: Any, **kwargs: Any) -> None:
                metadata.write_text(json.dumps({"containerimage.digest": digest}))

            with patch("beta_release.subprocess.run", side_effect=build) as invocation:
                reference = build_application_image(
                    ROOT,
                    "rehearsal-builder",
                    "backend",
                    "127.0.0.1:5055/alessandrorossato/florabase-backend:candidate",
                    "0.1.0-beta.3",
                    "c" * 40,
                    1762387200,
                    "scanner@sha256:" + "b" * 64,
                    metadata,
                )
        self.assertEqual(
            reference,
            "127.0.0.1:5055/alessandrorossato/florabase-backend@" + digest,
        )
        command = invocation.call_args.args[0]
        self.assertIn("--provenance=mode=max", command)
        self.assertIn("--target", command)
        self.assertEqual(command[command.index("--target") + 1], "runtime")

    def test_attestation_inputs_are_exact_immutable_subjects_without_creating_attestations(
        self,
    ) -> None:
        value = candidate()
        host = "127.0.0.1:5055"
        refs = {
            "backend": f"{host}/alessandrorossato/florabase-backend@sha256:{'a' * 64}",
            "frontend": f"{host}/alessandrorossato/florabase-frontend@sha256:{'d' * 64}",
            "postgresql": f"{host}/alessandrorossato/florabase-postgres@{value['postgresql']['index_digest']}",
        }
        for service in value["images"]:
            value["images"][service]["reference"] = refs[service]
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "release-manifest.json"
            path.write_text(json.dumps(value))
            result = release_attestation_inputs(
                value,
                refs,
                path,
                value["source"]["revision"],
                ".github/workflows/beta-images.yml",
                {},
                host,
            )
        self.assertEqual(result["source_sha"], value["source"]["revision"])
        self.assertEqual(set(result["subjects"]), {"backend", "frontend", "postgresql"})
        self.assertEqual(result["file_subjects"], {})
        self.assertFalse(result["attestations_created"])
        with self.assertRaises(ValueError):
            release_attestation_inputs(
                value,
                {**refs, "backend": refs["backend"].replace("a" * 64, "z" * 64)},
                path,
                value["source"]["revision"],
                ".github/workflows/beta-images.yml",
                {},
                host,
            )
        for assets in (
            {"compose.yaml": "sha256:" + "c" * 64},
            {"compose.yaml": "sha256:" + "c" * 64, "florabasectl.py": "x"},
        ):
            with self.assertRaises(ValueError):
                release_attestation_inputs(
                    value,
                    refs,
                    path,
                    value["source"]["revision"],
                    ".github/workflows/beta-images.yml",
                    assets,
                    host,
                )

    def test_release_finalization_inputs_match_protected_draft_request_without_api_call(
        self,
    ) -> None:
        value = candidate()
        sha = value["source"]["revision"]
        names = (
            "RELEASE.md",
            "release-manifest.json",
            beta_release.POSTGRES_SBOM,
            f"florabase-{value['version']}-source.tar.gz",
        )
        assets = {name: (21, "sha256:" + "a" * 64) for name in names}
        result = release_finalization_inputs(value, sha, assets)
        self.assertEqual(result["tag"], "v" + value["version"])
        self.assertEqual(result["target_commitish"], sha)
        self.assertTrue(result["draft"])
        self.assertEqual(result["prerelease"], "-" in value["version"])
        self.assertTrue(result["verify_tag"])
        self.assertFalse(result["release_api_called"])
        self.assertEqual(result["release_notes_sha256"], assets["RELEASE.md"][1])
        with self.assertRaises(ValueError):
            release_finalization_inputs(value, "d" * 40, assets)
        with self.assertRaises(ValueError):
            release_finalization_inputs(
                value, sha, {**assets, "unexpected.txt": assets["RELEASE.md"]}
            )

    def test_platform_policy_requires_supported_platform_and_separate_deployment(self) -> None:
        check_platform(policy())
        accepted = policy()
        accepted["deployment_acceptance"]["status"] = "accepted"
        accepted["deployment_acceptance"]["evidence"] = [{"host": "h", "reference": "r"}]
        check_platform(accepted)
        invalid = []
        for key in ("candidate_platform", "publication", "deployment_acceptance"):
            value = policy()
            del value[key]
            invalid.append(value)
        for platform in ("linux/arm64", "windows/amd64", None):
            value = policy()
            value["candidate_platform"] = platform
            invalid.append(value)
        for required in (True, None, "false"):
            value = policy()
            value["publication"]["host_approval_required"] = required
            invalid.append(value)
        for status in ("", "approved", None):
            value = policy()
            value["deployment_acceptance"]["status"] = status
            invalid.append(value)
        bad_evidence: list[Any] = [
            None,
            [],
            "text",
            [{}],
            ["text"],
            [{"host": "h"}],
            [{"host": "h", "reference": " "}],
            [{"host": 1, "reference": "r"}],
            [{"host": "h", "reference": "r"}, {"host": "h"}],
        ]
        for evidence in bad_evidence:
            value = policy()
            value["deployment_acceptance"]["status"] = "accepted"
            if evidence is not None:
                value["deployment_acceptance"]["evidence"] = evidence
            invalid.append(value)
        for key in ("publication", "deployment_acceptance"):
            malformed_values: list[Any] = [None, [], "x", 1, True]
            for malformed in malformed_values:
                value = policy()
                value[key] = malformed
                invalid.append(value)
        for value in invalid:
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "PUBLICATION BLOCKED"):
                    check_platform(value)

    def test_platform_file_missing_or_not_an_object_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "platform.json"
            with self.assertRaises(FileNotFoundError):
                read(path)
            for text in ("[]", '"x"', "1", "null", "{", ""):
                path.write_text(text)
                with self.subTest(text=text), self.assertRaises(ValueError):
                    check_platform(read(path))
            path.write_text("{}")
            with self.assertRaisesRegex(ValueError, "PUBLICATION BLOCKED"):
                check_platform(read(path))

    def test_immutable_manifest_and_mutations(self) -> None:
        valid = candidate()
        validate_manifest(valid)
        mutations = [
            ("platforms", ["linux/arm64"]),
            ("schema_version", 1),
            ("version", "latest"),
            ("distribution", "local-candidate"),
        ]
        for field, invalid in mutations:
            changed = copy.deepcopy(valid)
            changed[field] = invalid
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_manifest(changed)
        for field, invalid in (
            ("reference", "ghcr.io/example/backend:latest"),
            ("index_digest", "sha256:" + "f" * 64),
            ("platform_digest", "bad"),
            ("platform", "linux/arm64"),
        ):
            changed = copy.deepcopy(valid)
            changed["images"]["backend"][field] = invalid
            with self.subTest(image=field), self.assertRaises(ValueError):
                validate_manifest(changed)
        for field, invalid in (
            ("reference", "postgres:18.6-alpine"),
            ("repository", "docker.io/library/postgres"),
            ("version", "18.6-alpine"),
            ("platform_digest", "bad"),
            ("platform", "linux/arm64"),
            ("source_date_epoch", "1762387200"),
        ):
            changed = copy.deepcopy(valid)
            changed["postgresql"][field] = invalid
            changed["build_inputs"]["postgresql"] = changed["postgresql"]
            with self.subTest(postgres=field), self.assertRaises(ValueError):
                validate_manifest(changed)
        for field, invalid in (
            ("repository", "ghcr.io/example/postgres"),
            ("index_digest", "sha256:" + "f" * 64),
            ("platform", "linux/arm64"),
        ):
            changed = copy.deepcopy(valid)
            changed["postgresql"]["upstream"][field] = invalid
            changed["build_inputs"]["postgresql"] = changed["postgresql"]
            with self.subTest(upstream=field), self.assertRaises(ValueError):
                validate_manifest(changed)
        for change in (
            {},
            {"compose.yaml": "unpinned"},
            {**compose_template(ROOT), "extra": "sha256:" + "a" * 64},
            {**compose_template(ROOT), "florabasectl.py": "sha256:" + "a" * 64},
        ):
            changed = copy.deepcopy(valid)
            changed["compose_template"] = change
            with self.subTest(bundle=sorted(change)), self.assertRaises(ValueError):
                validate_manifest(changed)
        # The official image itself is no longer an acceptable release database identity.
        changed = copy.deepcopy(valid)
        changed["postgresql"] = dict(changed["postgresql"]["upstream"])
        with self.assertRaises(ValueError):
            validate_manifest(changed)

    def test_dirty_or_inconsistent_release_metadata_refuses(self) -> None:
        for field, invalid in (("dirty", True), ("revision", "not-a-commit")):
            value = candidate()
            value["source"][field] = invalid
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_manifest(value)
        value = candidate()
        value["build_inputs"]["version"] = "0.1.0-beta.99"
        with self.assertRaises(ValueError):
            validate_manifest(value)

    def test_local_evidence_cannot_claim_registry_pull_acceptance(self) -> None:
        value = candidate()
        value["distribution"] = "local-candidate"
        value["images"] = {
            name: {"reference": "sha256:" + "f" * 64, "platform": "linux/amd64"}
            for name in ("backend", "frontend")
        }
        validate_manifest(value, local=True)
        with self.assertRaises(ValueError):
            validate_manifest(value)

    def test_check_names_from_other_sources_or_commits_do_not_approve_release(
        self,
    ) -> None:
        sha = "c" * 40
        valid = [
            {
                "name": name,
                "head_sha": sha,
                "conclusion": "success",
                "status": "completed",
            }
            for name in ("quality", "integration", "build", "release-migration")
        ]
        self.assertTrue(checks.approved_ci_jobs(valid, sha))
        self.assertFalse(checks.approved_ci_jobs(valid[:-1], sha))
        self.assertFalse(checks.approved_ci_jobs([*valid, valid[0]], sha))
        for field, invalid in (
            ("head_sha", "d" * 40),
            ("conclusion", "failure"),
            ("status", "in_progress"),
        ):
            changed = copy.deepcopy(valid)
            changed[0][field] = invalid
            with self.subTest(field=field):
                self.assertFalse(checks.approved_ci_jobs(changed, sha))

    def test_canonical_ci_producer_identity(self) -> None:
        valid = {
            "path": ".github/workflows/ci.yml",
            "head_sha": "a" * 40,
            "head_branch": "main",
            "event": "push",
            "status": "completed",
            "conclusion": "success",
            "repository": {"full_name": "owner/repo"},
            "head_repository": {"full_name": "owner/repo"},
        }
        self.assertTrue(checks.approved_ci_run(valid, "a" * 40, "owner/repo"))
        for field in valid:
            changed = {**valid, field: None}
            with self.subTest(field=field):
                self.assertFalse(checks.approved_ci_run(changed, "a" * 40, "owner/repo"))
        self.assertFalse(
            checks.approved_ci_run(
                {**valid, "path": ".github/workflows/spoof.yml"}, "a" * 40, "owner/repo"
            )
        )

    def test_required_main_evidence_reuses_latest_jobs_only_within_the_exact_run(self) -> None:
        sha = "a" * 40
        repo = "owner/repo"
        approved = {
            "id": 42,
            "run_attempt": 2,
            "path": ".github/workflows/ci.yml",
            "head_sha": sha,
            "head_branch": "main",
            "event": "push",
            "status": "completed",
            "conclusion": "success",
            "repository": {"full_name": repo},
            "head_repository": {"full_name": repo},
        }
        jobs = [
            {
                "name": name,
                "head_sha": sha,
                "status": "completed",
                "conclusion": "success",
                "run_attempt": 2 if name == "release-migration" else 1,
            }
            for name in ("quality", "integration", "build", "release-migration")
        ]
        required = {job["name"] for job in jobs}
        for evidence in (jobs, jobs[:-1]):
            with (
                self.subTest(complete=evidence == jobs),
                patch.object(
                    checks,
                    "run",
                    side_effect=[
                        json.dumps(
                            [
                                {
                                    "workflow_runs": [
                                        {**approved, "id": 11, "head_sha": "b" * 40},
                                        approved,
                                    ]
                                }
                            ]
                        ),
                        json.dumps([{"jobs": evidence}]),
                    ],
                ) as api,
            ):
                if evidence == jobs:
                    checks.require_workflow(repo, sha, "ci.yml", required)
                else:
                    with self.assertRaisesRegex(ValueError, "exact main SHA"):
                        checks.require_workflow(repo, sha, "ci.yml", required)
                self.assertEqual(api.call_count, 2)
                self.assertIn("/runs/42/jobs?filter=latest", api.call_args.args[-1])

    def test_release_identity_refuses_before_registry_access(self) -> None:
        sha = "c" * 40
        valid = {
            "GITHUB_ACTIONS": "true",
            "GITHUB_REF": "refs/heads/main",
            "GITHUB_SHA": sha,
            "GITHUB_EVENT_NAME": "workflow_dispatch",
            "GITHUB_REPOSITORY": "alessandrorossato/florabase",
            "GITHUB_WORKFLOW_REF": "alessandrorossato/florabase/.github/workflows/beta-images.yml@refs/heads/main",
            "RUNNER_ENVIRONMENT": "github-hosted",
            "APPROVED_SHA": sha,
        }
        with (
            patch.dict(os.environ, valid, clear=True),
            patch.object(publisher, "run", return_value=""),
        ):
            publisher.require_publication_identity(sha)
            for field in valid:
                with (
                    self.subTest(field=field),
                    patch.dict(os.environ, {field: ""}),
                    self.assertRaises(ValueError),
                ):
                    publisher.require_publication_identity(sha)
        with (
            patch.dict(os.environ, valid, clear=True),
            patch.object(publisher, "run", return_value=" M file"),
            self.assertRaises(ValueError),
        ):
            publisher.require_publication_identity(sha)

    def test_failed_security_or_smoke_cannot_promote_a_pair(self) -> None:
        sha = "c" * 40
        environment = {
            "GITHUB_ACTIONS": "true",
            "GITHUB_REF": "refs/heads/main",
            "GITHUB_SHA": sha,
            "GITHUB_EVENT_NAME": "workflow_dispatch",
            "GITHUB_REPOSITORY": "alessandrorossato/florabase",
            "GITHUB_WORKFLOW_REF": "alessandrorossato/florabase/.github/workflows/beta-images.yml@refs/heads/main",
            "RUNNER_ENVIRONMENT": "github-hosted",
            "APPROVED_SHA": sha,
            "GITHUB_RUN_ID": "1",
            "GITHUB_RUN_ATTEMPT": "1",
            "GITHUB_ACTOR": "fixture",
            "REGISTRY_TOKEN": "fixture-only",
        }

        def output(*args: str) -> str:
            if args[:2] == ("git", "rev-parse"):
                return sha
            if args[:2] == ("git", "status"):
                return ""
            return "0"

        def execute(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
            if "--metadata-file" in command:
                path = Path(command[command.index("--metadata-file") + 1])
                path.write_text(
                    json.dumps(
                        {
                            "containerimage.digest": "sha256:"
                            + ("a" if "backend" == command[-1] else "d") * 64
                        }
                    )
                )
            return subprocess.CompletedProcess(command, 0)

        for failing, phase in (
            ("local_postgres_identity", "CANDIDATES"),
            ("scan_images", "SCAN/SMOKE"),
            ("run_artifact_smoke", "SCAN/SMOKE"),
        ):
            with (
                self.subTest(failing=failing),
                tempfile.TemporaryDirectory() as temporary,
            ):
                target = Path(temporary) / "output"
                with (
                    patch.dict(os.environ, environment, clear=True),
                    patch.object(sys, "argv", ["publish", "--output", str(target)]),
                    patch.object(publisher, "check_toolchain"),
                    patch.object(
                        publisher,
                        "disposable_registry",
                        return_value=nullcontext(("127.0.0.1:5055", 5055)),
                    ),
                    patch.object(publisher, "run", side_effect=output),
                    patch.object(publisher, "manifest", return_value=candidate()),
                    patch.object(publisher, "published_digest", return_value=None),
                    patch.object(publisher, "scan_images"),
                    patch.object(publisher, "run_artifact_smoke"),
                    patch.object(publisher, "software_bill_of_materials"),
                    patch.object(
                        publisher,
                        "local_postgres_identity",
                        return_value={
                            field: inputs(ROOT)["postgresql"][field]
                            for field in ("index_digest", "platform_digest")
                        },
                    ),
                    patch.object(
                        publisher,
                        failing,
                        side_effect=ValueError("fixture gate blocked"),
                    ),
                    patch.object(publisher.subprocess, "run", side_effect=execute) as commands,
                ):
                    with self.assertRaisesRegex(ValueError, "fixture gate blocked"):
                        publisher.main()
                    self.assertEqual(
                        read(target / "diagnostics/publication-state.json")["stages"][phase][
                            "status"
                        ],
                        "failed",
                    )
                    self.assertFalse((target / "RELEASE.md").exists())
                    self.assertFalse(
                        any(
                            call.args[0][:4] == ["docker", "buildx", "imagetools", "create"]
                            for call in commands.call_args_list
                        )
                    )

    def test_scan_requires_complete_unsuppressed_exact_bytes(self) -> None:
        digest = "sha256:" + "a" * 64
        valid: dict[str, Any] = {
            "SchemaVersion": 2,
            "ArtifactType": "container_image",
            "Metadata": {"ImageID": digest},
            "Results": [{"Class": "os-pkgs", "Packages": [{"Name": "fixture"}]}],
        }
        validate_scan(valid, digest)
        for service in ("backend", "frontend", "postgresql"):
            with self.subTest(service=service), self.assertRaisesRegex(ValueError, "inventory"):
                validate_scan(valid, digest, service)
        for change in (
            {},
            {**valid, "Results": []},
            {**valid, "Metadata": {"ImageID": "wrong"}},
            {**valid, "Results": [{"Class": "os-pkgs"}]},
            {**valid, "ExperimentalModifiedFindings": ["ignored"]},
        ):
            with self.subTest(change=change), self.assertRaises(ValueError):
                validate_scan(change, digest)
        for field in ("Secrets", "Vulnerabilities", "ExperimentalModifiedFindings"):
            changed = copy.deepcopy(valid)
            changed["Results"][0][field] = [{"Severity": "HIGH"}]
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_scan(changed, digest)

    def test_postgres_scan_requires_alpine_inventory_and_no_gosu(self) -> None:
        digest = "sha256:" + "a" * 64
        alpine = {
            "Class": "os-pkgs",
            "Type": "alpine",
            "Packages": [{"Name": name} for name in ("musl", "busybox", "libssl3", "tzdata")],
        }
        valid: dict[str, Any] = {
            "SchemaVersion": 2,
            "ArtifactType": "container_image",
            "Metadata": {"ImageID": digest},
            "Results": [alpine],
        }
        validate_scan(valid, digest, "postgresql")
        with_gosu = copy.deepcopy(valid)
        with_gosu["Results"].append(
            {
                "Target": "usr/local/bin/gosu",
                "Class": "lang-pkgs",
                "Type": "gobinary",
                "Packages": [{"Name": "stdlib"}],
            }
        )
        with self.assertRaisesRegex(ValueError, "gosu"):
            validate_scan(with_gosu, digest, "postgresql")
        partial = copy.deepcopy(valid)
        partial["Results"][0]["Packages"] = [{"Name": "musl"}]
        with self.assertRaisesRegex(ValueError, "inventory"):
            validate_scan(partial, digest, "postgresql")

    def test_postgres_inputs_bind_dockerfile_and_reproducible_pins(self) -> None:
        import beta_release

        pinned = inputs(ROOT)["postgresql"]
        self.assertEqual(pinned["repository"], beta_release.POSTGRES_REPOSITORY)
        self.assertEqual(pinned["upstream"]["repository"], "docker.io/library/postgres")
        dockerfile = (ROOT / "postgres/Dockerfile").read_text()
        self.assertIn("\nFROM " + pinned["upstream"]["reference"] + "\n", dockerfile)
        self.assertIn("COPY LICENSE /usr/share/licenses/florabase/LICENSE", dockerfile)
        self.assertIn("    && rm /usr/local/bin/gosu \\\n", dockerfile)
        # The upstream entrypoint (sourced first by docker-ensure-initdb.sh) refuses root too.
        self.assertIn("sed -i '1a florabase-postgres-refuse-root || exit 64'", dockerfile)
        self.assertIn('= "florabase-postgres-refuse-root || exit 64"', dockerfile)
        self.assertIn("^source /usr/local/bin/docker-entrypoint.sh$", dockerfile)
        self.assertIn("USER 70:70\n", dockerfile)
        self.assertIn('ENTRYPOINT ["florabase-postgres-entrypoint"]', dockerfile)
        for drift in (
            dockerfile.replace(pinned["upstream"]["index_digest"], "sha256:" + "f" * 64, 1),
            dockerfile.replace(f'version="{pinned["version"]}"', 'version="other"'),
            dockerfile.replace("FROM ", "ARG BASE\nFROM ", 1),
        ):
            with tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                for path in (
                    "release/inputs.json",
                    "frontend/package.json",
                    "backend/src/florabase/__init__.py",
                    "backend/pyproject.toml",
                    "backend/Dockerfile",
                    "frontend/Dockerfile",
                    "LICENSE",
                    "backend/LICENSE",
                    "frontend/LICENSE",
                    "postgres/LICENSE",
                    "postgres/Dockerfile",
                ):
                    (root / path).parent.mkdir(parents=True, exist_ok=True)
                    (root / path).write_bytes((ROOT / path).read_bytes())
                inputs(root)
                (root / "postgres/Dockerfile").write_text(drift)
                with self.assertRaisesRegex(ValueError, "PostgreSQL Dockerfile|base image"):
                    inputs(root)
        beta_release.require_pinned_postgres(
            {"index_digest": pinned["index_digest"], "platform_digest": pinned["platform_digest"]},
            pinned,
        )
        with self.assertRaisesRegex(ValueError, "not reproducible"):
            beta_release.require_pinned_postgres(
                {
                    "index_digest": "sha256:" + "f" * 64,
                    "platform_digest": pinned["platform_digest"],
                },
                pinned,
            )

    def test_postgres_entrypoint_refuses_root_and_guards_data_directory(self) -> None:
        guard = ROOT / "postgres/florabase-postgres-entrypoint.sh"
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            bin_dir = base / "bin"
            bin_dir.mkdir()
            pg_root = base / "data"
            for sub in ("postgres", "media", "state"):
                (pg_root / sub).mkdir(parents=True)
            (bin_dir / "docker-entrypoint.sh").write_text(
                '#!/bin/sh\necho "upstream=$* pgdata=$PGDATA pw=${POSTGRES_PASSWORD:-}" > "$MARKER"\n'
            )
            (bin_dir / "florabase-postgres-refuse-root").write_bytes(
                (ROOT / "postgres/florabase-postgres-refuse-root.sh").read_bytes()
            )
            (bin_dir / "stat").write_text(
                "#!/bin/sh\n"
                'fmt="$2"; path="$3"\n'
                'case "$path" in\n'
                '  */postgres) owner="${PG_OWNER:-70:70}"; mode="${PG_MODE:-700}" ;;\n'
                '  */media) owner="${MEDIA_OWNER:-10001:10001}"; mode="${MEDIA_MODE:-700}" ;;\n'
                '  */state) owner="${STATE_OWNER:-10001:10001}"; mode="${STATE_MODE:-755}" ;;\n'
                '  *) owner="0:0"; mode="755" ;;\n'
                "esac\n"
                'if [ "$fmt" = "%u:%g" ]; then echo "$owner"; else echo "$mode"; fi\n'
            )
            (bin_dir / "pg_controldata").write_text(
                '#!/bin/sh\necho "Database system identifier:           ${CLUSTER_ID:-999}"\n'
            )
            for name in (
                "docker-entrypoint.sh",
                "florabase-postgres-refuse-root",
                "stat",
                "pg_controldata",
            ):
                (bin_dir / name).chmod(0o755)

            def invoke(
                uid: str = "70", extra: dict[str, str] | None = None
            ) -> tuple[subprocess.CompletedProcess[str], Path]:
                (bin_dir / "id").write_text(f"#!/bin/sh\necho {uid}\n")
                (bin_dir / "id").chmod(0o755)
                marker = base / "upstream-ran"
                marker.unlink(missing_ok=True)
                env = {
                    "PATH": f"{bin_dir}:/usr/bin:/bin",
                    "MARKER": str(marker),
                    "FLORABASE_PG_ROOT": str(pg_root),
                    "FLORABASE_REFUSAL_BACKOFF_SECONDS": "0",
                    "PG_MAJOR": "18",
                    "FLORABASE_DB_PASSWORD": "stack-password",
                }
                if extra:
                    env.update(extra)
                res = subprocess.run(
                    ["/bin/sh", str(guard), "postgres", "-c", "timezone=UTC"],
                    env=env,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                return res, marker

            # Root is refused immediately with exit 64 before touching disk.
            root_res, ran = invoke(uid="0")
            self.assertEqual(root_res.returncode, 64)
            self.assertIn("refusing to run as root", root_res.stderr)
            self.assertFalse(ran.exists())

            # Wrong ownership or mode is refused with pointer to docs/installation.md.
            bad_owner, ran = invoke(extra={"PG_OWNER": "1000:1000"})
            self.assertEqual(bad_owner.returncode, 1)
            self.assertIn("docs/installation.md", bad_owner.stderr)
            self.assertFalse(ran.exists())

            # Stray file without marker is refused.
            (pg_root / "stray").write_text("x")
            stray_res, ran = invoke()
            self.assertEqual(stray_res.returncode, 1)
            self.assertIn("no installation marker", stray_res.stderr)
            self.assertFalse(ran.exists())
            (pg_root / "stray").unlink()

            # Fresh empty folders succeed, touch postgres/installation.pending, map password & PGDATA.
            ok, ran = invoke()
            self.assertEqual(ok.returncode, 0, ok.stderr)
            self.assertIn("upstream=postgres -c timezone=UTC", ran.read_text())
            self.assertIn(f"pgdata={pg_root}/postgres/18/docker", ran.read_text())
            self.assertIn("pw=stack-password", ran.read_text())
            self.assertTrue((pg_root / "postgres/installation.pending").exists())

            # Pending first-install retry allows existing cluster under postgres/.
            cluster = pg_root / "postgres/18/docker"
            cluster.mkdir(parents=True)
            (cluster / "PG_VERSION").write_text("18\n")
            retry_ok, ran = invoke()
            self.assertEqual(retry_ok.returncode, 0, retry_ok.stderr)

            # Removing pending while cluster exists and marker is absent refuses.
            (pg_root / "postgres/installation.pending").unlink()
            no_marker, ran = invoke()
            self.assertEqual(no_marker.returncode, 1)
            self.assertIn("no installation marker", no_marker.stderr)

            # Marker checks: wrong major, mismatched cluster ID, missing cluster, then exact match.
            inst = pg_root / "state/installation.env"
            inst.write_text(
                "FLORABASE_INSTALLATION_ID=ab12\nFLORABASE_PG_MAJOR=17\nFLORABASE_PG_SYSTEM_ID=999\n"
            )
            self.assertIn("uses PostgreSQL 17", invoke()[0].stderr)
            inst.write_text(
                "FLORABASE_INSTALLATION_ID=ab12\nFLORABASE_PG_MAJOR=18\nFLORABASE_PG_SYSTEM_ID=1\n"
            )
            self.assertIn("another PostgreSQL cluster", invoke()[0].stderr)
            inst.write_text(
                "FLORABASE_INSTALLATION_ID=ab12\nFLORABASE_PG_MAJOR=18\nFLORABASE_PG_SYSTEM_ID=999\n"
            )
            (pg_root / "postgres/installation.pending").touch()
            matched, ran = invoke()
            self.assertEqual(matched.returncode, 0, matched.stderr)
            self.assertFalse((pg_root / "postgres/installation.pending").exists())
            (cluster / "PG_VERSION").unlink()
            self.assertIn("database folder is missing or empty", invoke()[0].stderr)

    def test_backend_entrypoint_and_start_scripts_order_steps_and_scrub_owner_env(self) -> None:
        entrypoint = ROOT / "backend/florabase-backend-entrypoint.sh"
        start = ROOT / "backend/florabase-start.sh"
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            res = subprocess.run(
                ["/bin/sh", str(entrypoint), "/bin/sh", "-c", 'printf "%s" "$PGPASSWORD"'],
                env={"PATH": "/usr/bin:/bin", "FLORABASE_DB_PASSWORD": "derived-pw"},
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertEqual(res.stdout, "derived-pw")

            bin_dir = base / "bin"
            bin_dir.mkdir()
            log = base / "calls.log"
            fake_python = bin_dir / "python"
            fake_python.write_text(
                "#!/bin/sh\n"
                f'echo "$* owner=${{FLORABASE_OWNER_PASSWORD:-unset}}" >> "{log}"\n'
                'if [ "${FAIL_STEP:-}" = "$3" ]; then exit 1; fi\n'
                "exit 0\n"
            )
            fake_python.chmod(0o755)
            base_env = {
                "PATH": f"{bin_dir}:/usr/bin:/bin",
                "FLORABASE_OWNER_LOGIN": "owner",
                "FLORABASE_OWNER_PASSWORD": "secret-owner-password",
                "FLORABASE_REFUSAL_BACKOFF_SECONDS": "0",
            }
            ok = subprocess.run(
                ["/bin/sh", str(start)], env=base_env, capture_output=True, text=True
            )
            self.assertEqual(ok.returncode, 0, ok.stderr)
            self.assertEqual(
                log.read_text().splitlines(),
                [
                    "-m florabase.db.release_schema wait-db owner=secret-owner-password",
                    "-m florabase.db.release_schema deploy owner=secret-owner-password",
                    "-m florabase.db.release_schema serve owner=unset",
                ],
            )
            log.unlink()
            failed = subprocess.run(
                ["/bin/sh", str(start)],
                env={**base_env, "FAIL_STEP": "deploy"},
                capture_output=True,
                text=True,
            )
            self.assertEqual(failed.returncode, 1)
            self.assertEqual(
                log.read_text().splitlines(),
                [
                    "-m florabase.db.release_schema wait-db owner=secret-owner-password",
                    "-m florabase.db.release_schema deploy owner=secret-owner-password",
                ],
            )

    def test_postgres_build_context_normalizes_checkout_license_mode(self) -> None:
        import beta_release

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            license_path = root / "postgres/LICENSE"
            license_path.parent.mkdir()
            license_path.write_text("license")
            license_path.chmod(0o644)
            with beta_release.normalized_postgres_context(root):
                self.assertEqual(license_path.stat().st_mode & 0o777, 0o664)
            self.assertEqual(license_path.stat().st_mode & 0o777, 0o644)

    def test_publication_attests_and_pins_postgres(self) -> None:
        workflow = (ROOT / ".github/workflows/beta-images.yml").read_text()
        self.assertIn("subject-digest: ${{ steps.pair.outputs.postgresql_digest }}", workflow)
        source = (ROOT / "scripts/publish-beta-images.py").read_text()
        self.assertIn(
            "subject-path: ${{ runner.temp }}/beta-release/assets/release-manifest.json", workflow
        )
        for name in (
            "compose.yaml",
            "portable-compose.yaml",
            "florabasectl.py",
            "florabase.env.example",
        ):
            self.assertNotIn(name, workflow)
        # The rebuild check must not gate every release: the publisher runs it only for an
        # unpublished identity, so a superseded Alpine pin never blocks application releases.
        self.assertNotIn("postgres-identity --check", workflow)
        self.assertEqual(workflow.count("version: v0.38.1"), 1)
        self.assertIn("version: " + publisher.BUILDX_VERSION, workflow)
        # Registry manifest lookups distinguish absence from outages and authorization failures.
        self.assertNotIn("/packages", source)

    def test_shared_or_symlinked_executable_cache_refuses(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            cache = root / "cache"
            tooling.secure_cache(cache)
            self.assertEqual(cache.stat().st_mode & 0o777, 0o700)
            cache.chmod(0o777)
            with self.assertRaisesRegex(ValueError, "unsafe release cache"):
                tooling.secure_cache(cache)
            cache.chmod(0o700)
            link = root / "symlink"
            link.symlink_to(cache, target_is_directory=True)
            with self.assertRaises(ValueError):
                tooling.secure_cache(link)
            (cache / "lock").symlink_to(root / "victim")
            with self.assertRaises((ValueError, FileNotFoundError)):
                tooling.secure_cache(cache)
            (cache / "lock").unlink()
            (cache / "python").write_text("malicious executable")
            (cache / "python").chmod(0o777)
            with self.assertRaises(ValueError):
                tooling.secure_cache(cache)

    def test_authenticated_paginated_draft_lookup_and_id_revalidation(self) -> None:
        import beta_release

        self.assertTrue(
            hasattr(beta_release, "locate_draft_release"),
            "draft lookup must use listing and numeric ID",
        )
        tag, sha, repo = "v0.1.0-beta.1", "c" * 40, "alessandrorossato/florabase"
        draft = {
            "id": 42,
            "tag_name": tag,
            "draft": True,
            "target_commitish": "main",
            "url": f"https://api.github.com/repos/{repo}/releases/42",
            "assets": [],
        }

        def api(*args: str) -> str:
            if args[-1] == f"repos/{repo}/git/ref/tags/{tag}":
                return json.dumps(
                    {"ref": f"refs/tags/{tag}", "object": {"type": "commit", "sha": sha}}
                )
            if "/releases/tags/" in args[-1]:
                raise subprocess.CalledProcessError(
                    1, args, stderr="404 published release not found"
                )
            if "--paginate" in args:
                self.assertIn("--slurp", args)
                return json.dumps([[{"tag_name": "unrelated"}], [draft]])
            self.assertEqual(args[-1], f"repos/{repo}/releases/42")
            return json.dumps(draft)

        with (
            patch.dict(os.environ, {"GH_TOKEN": "fixture"}),
            patch("beta_release.run", side_effect=api),
        ):
            self.assertEqual(beta_release.locate_draft_release(repo, tag, sha), draft)
        mutations = [
            {**draft, "id": 43},
            {**draft, "draft": False},
            {**draft, "tag_name": "stale"},
            {**draft, "url": "foreign"},
            {**draft, "assets": [{"id": 1, "state": "new"}]},
        ]
        for value in mutations:
            with (
                self.subTest(value=value),
                patch.dict(os.environ, {"GH_TOKEN": "fixture"}),
                patch(
                    "beta_release.run",
                    side_effect=[json.dumps([[draft]]), json.dumps(value)],
                ),
                self.assertRaises(ValueError),
            ):
                beta_release.locate_draft_release(repo, tag, sha)
        for pages in [[], [[]], [[draft], [draft]], [[{**draft, "draft": False}]]]:
            with (
                self.subTest(pages=pages),
                patch.dict(os.environ, {"GH_TOKEN": "fixture"}),
                patch("beta_release.run", return_value=json.dumps(pages)),
                self.assertRaises(ValueError),
            ):
                beta_release.locate_draft_release(repo, tag, sha)
        with (
            patch.dict(os.environ, {"GH_TOKEN": "fixture"}),
            patch("beta_release.run", side_effect=subprocess.CalledProcessError(1, "gh")),
            self.assertRaises(subprocess.CalledProcessError),
        ):
            beta_release.locate_draft_release(repo, tag, sha)

    def test_protected_git_tag_checks_the_exact_annotated_commit(self) -> None:
        repo, sha, annotation = publisher.REPOSITORY, "c" * 40, "e" * 40
        annotated = {"sha": annotation, "object": {"type": "commit", "sha": sha}}
        wrong = {**annotated, "object": {"type": "commit", "sha": "b" * 40}}
        for tag in ("v0.1.0-beta.4", "v1.0.0-rc.1", "v1.0.0"):
            reference = {"ref": f"refs/tags/{tag}", "object": {"type": "tag", "sha": annotation}}
            with (
                self.subTest(tag=tag),
                patch(
                    "beta_release.run",
                    side_effect=[
                        json.dumps(reference),
                        json.dumps(annotated),
                        json.dumps(reference),
                        json.dumps(wrong),
                    ],
                ) as api,
            ):
                beta_release.require_remote_release_tag(repo, tag, sha)
                self.assertTrue(api.call_args_list[0].args[-1].endswith(f"/git/ref/tags/{tag}"))
                self.assertTrue(api.call_args.args[-1].endswith(f"/git/tags/{annotation}"))
                with self.assertRaisesRegex(ValueError, "approved source SHA"):
                    beta_release.require_remote_release_tag(repo, tag, sha)
        with patch("beta_release.run") as api, self.assertRaisesRegex(ValueError, "tag identity"):
            beta_release.require_remote_release_tag(repo, "v0.1.0", sha)
        api.assert_not_called()

    def test_workflow_wires_protected_draft_finalization_and_attestation_assets(
        self,
    ) -> None:
        workflow = (ROOT / ".github/workflows/beta-images.yml").read_text()
        self.assertNotIn("/releases/tags/", workflow)
        self.assertNotIn("make ci", workflow)
        self.assertIn("publish-beta-images.py --finalize", workflow)
        self.assertIn("/beta-release/assets/release-manifest.json", workflow)
        self.assertNotIn("/beta-release/assets/compose.yaml", workflow)
        ci = (ROOT / ".github/workflows/ci.yml").read_text()
        self.assertIn("name: release-migration", ci)
        self.assertIn('verify-migration-cycle.sh "$BASE_SHA" --force-cycle', ci)

    def test_original_beta4_inventory_failure_is_reproduced_before_any_promotion(
        self,
    ) -> None:
        version = inputs(ROOT)["version"]
        sha = beta_release.run("git", "-C", str(ROOT), "rev-parse", "HEAD")
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "assets"
            output.mkdir()
            offending = output / "postgres-reproducibility"
            offending.mkdir()
            (offending / "postgres-oci-evidence.json").write_text("{}")
            with self.assertRaisesRegex(
                ValueError,
                "invalid local release asset inventory.*postgres-reproducibility",
            ):
                beta_release.prepare_release_assets(ROOT, output, version, sha)
            with self.assertRaisesRegex(ValueError, "postgres-reproducibility"):
                beta_release.release_asset_inventory(output)

    def test_asset_inventory_rejects_symlinks_and_hidden_files(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            (output / "valid.json").write_text("{}")
            link = output / "symlink"
            link.symlink_to(output / "valid.json")
            with self.assertRaisesRegex(ValueError, "symlink"):
                beta_release.release_asset_inventory(output)
            link.unlink()
            (output / ".hidden").write_text("{}")
            with self.assertRaisesRegex(ValueError, "hidden"):
                beta_release.release_asset_inventory(output)
            (output / ".hidden").unlink()
            with (output / "oversize.tar.gz").open("wb") as oversized:
                oversized.truncate(2**31)
            with self.assertRaisesRegex(ValueError, "oversize.tar.gz"):
                beta_release.release_asset_inventory(output)

    def test_deployable_compose_has_no_slots_and_withdrawn_bundle_is_absent(self) -> None:
        compose = (ROOT / beta_release.INSTALL_COMPOSE).read_text()
        self.assertNotRegex(compose, r"@[A-Z]+@")
        for repo in ("florabase-postgres", "florabase-backend", "florabase-frontend"):
            self.assertIn(f"ghcr.io/alessandrorossato/{repo}:latest", compose)
        self.assertFalse((ROOT / "deploy").exists())

    def test_partial_or_wrong_release_assets_cannot_be_published(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            (output / "manifest.json").write_bytes(b"fixture")
            asset = {
                "name": "manifest.json",
                "size": 7,
                "digest": "sha256:" + hashlib.sha256(b"fixture").hexdigest(),
            }
            valid = {"draft": True, "assets": [asset]}
            validate_release_assets(valid, output)
            for change in (
                {"draft": False, "assets": [asset]},
                {"draft": True, "assets": []},
                {"draft": True, "assets": [{**asset, "digest": None}]},
                {"draft": True, "assets": [{**asset, "size": 0}]},
            ):
                with self.subTest(change=change), self.assertRaises(ValueError):
                    validate_release_assets(change, output)

    def test_saved_native_descriptor_is_bound_to_configuration(self) -> None:
        config = "sha256:" + "a" * 64
        native = json.dumps({"config": {"digest": config}}).encode()
        native_digest = "sha256:" + hashlib.sha256(native).hexdigest()
        index = json.dumps(
            {
                "manifests": [
                    {"digest": native_digest, "platform": {"os": "linux", "architecture": "amd64"}}
                ]
            }
        ).encode()
        index_digest = "sha256:" + hashlib.sha256(index).hexdigest()
        with tempfile.TemporaryFile() as data:
            with tarfile.open(fileobj=data, mode="w") as saved:
                for name, value in {
                    "index.json": json.dumps({"manifests": [{"digest": index_digest}]}).encode(),
                    "blobs/sha256/" + index_digest[7:]: index,
                    "blobs/sha256/" + native_digest[7:]: native,
                }.items():
                    info = tarfile.TarInfo(name)
                    info.size = len(value)
                    saved.addfile(info, io.BytesIO(value))
            data.seek(0)
            with tarfile.open(fileobj=data) as saved:
                self.assertEqual(saved_descriptors(saved, config)["platform_digest"], native_digest)
                with self.assertRaisesRegex(ValueError, "identity mismatch"):
                    saved_descriptors(saved, "sha256:" + "b" * 64)

    def test_classic_registry_export_binds_native_config_without_oci_store(self) -> None:
        config = "sha256:" + "a" * 64
        native = json.dumps({"config": {"digest": config}}).encode()
        native_digest = "sha256:" + hashlib.sha256(native).hexdigest()
        index = json.dumps(
            {
                "manifests": [
                    {"digest": native_digest, "platform": {"os": "linux", "architecture": "amd64"}}
                ]
            }
        ).encode()
        index_digest = "sha256:" + hashlib.sha256(index).hexdigest()
        reference = "ghcr.io/owner/image@" + index_digest
        with tempfile.TemporaryFile() as data:
            with tarfile.open(fileobj=data, mode="w"):
                pass
            data.seek(0)
            with tarfile.open(fileobj=data) as saved:
                with patch(
                    "beta_release.subprocess.check_output",
                    side_effect=[index + b"\n", native + b"\n"],
                ):
                    self.assertEqual(
                        saved_descriptors(saved, config, reference)["platform_digest"],
                        native_digest,
                    )
                with (
                    patch("beta_release.subprocess.check_output", return_value=b"{}"),
                    self.assertRaisesRegex(ValueError, "digest mismatch"),
                ):
                    saved_descriptors(saved, config, reference)
                with (
                    patch("beta_release.subprocess.check_output", side_effect=[index, native]),
                    self.assertRaisesRegex(ValueError, "config identity mismatch"),
                ):
                    saved_descriptors(saved, "sha256:" + "b" * 64, reference)
                with self.assertRaisesRegex(ValueError, "OCI image store required"):
                    saved_descriptors(saved, config, "local-candidate")

    def test_classic_registry_export_resolves_index_when_raw_view_is_not_an_index(self) -> None:
        config = "sha256:" + "a" * 64
        native = json.dumps({"config": {"digest": config}}).encode()
        native_digest = "sha256:" + hashlib.sha256(native).hexdigest()
        raw_platform_view = json.dumps({"config": {}, "layers": []}).encode()
        index_digest = "sha256:" + hashlib.sha256(raw_platform_view).hexdigest()
        reference = "127.0.0.1:5000/owner/image@" + index_digest
        index = {
            "digest": index_digest,
            "manifests": [
                {
                    "digest": native_digest,
                    "platform": {"os": "linux", "architecture": "amd64"},
                }
            ],
        }
        with tempfile.TemporaryFile() as data:
            with tarfile.open(fileobj=data, mode="w"):
                pass
            data.seek(0)
            with tarfile.open(fileobj=data) as saved:
                with (
                    patch("beta_release.run", return_value=json.dumps(index)),
                    patch(
                        "beta_release.subprocess.check_output",
                        side_effect=[raw_platform_view + b"\n", native + b"\n"],
                    ),
                ):
                    descriptors = saved_descriptors(saved, config, reference)
        self.assertEqual(descriptors["index_digest"], index_digest)
        self.assertEqual(descriptors["platform_digest"], native_digest)
        self.assertEqual(descriptors["configuration_digest"], config)
        self.assertEqual(descriptors["raw_index_document"], json.loads(raw_platform_view))

    def test_oci_export_resolves_platform_root_against_immutable_registry_index(self) -> None:
        config_bytes = json.dumps({"rootfs": {"diff_ids": []}}).encode()
        config = "sha256:" + hashlib.sha256(config_bytes).hexdigest()
        native = {"config": {"digest": config}, "layers": []}
        native_bytes = json.dumps(native).encode()
        native_digest = "sha256:" + hashlib.sha256(native_bytes).hexdigest()
        remote_native = json.dumps({**native, "annotations": {"source": "registry"}}).encode()
        remote_digest = "sha256:" + hashlib.sha256(remote_native).hexdigest()
        index = json.dumps(
            {
                "manifests": [
                    {"digest": remote_digest, "platform": {"os": "linux", "architecture": "amd64"}}
                ],
            }
        ).encode()
        index_digest = "sha256:" + hashlib.sha256(index).hexdigest()
        reference = "127.0.0.1:5000/owner/image@" + index_digest
        with tempfile.TemporaryFile() as data:
            with tarfile.open(fileobj=data, mode="w") as saved:
                for name, value in {
                    "index.json": json.dumps({"manifests": [{"digest": native_digest}]}).encode(),
                    "blobs/sha256/" + native_digest[7:]: native_bytes,
                    "blobs/sha256/" + config[7:]: config_bytes,
                }.items():
                    info = tarfile.TarInfo(name)
                    info.size = len(value)
                    saved.addfile(info, io.BytesIO(value))
            data.seek(0)
            with tarfile.open(fileobj=data) as saved:
                with patch(
                    "beta_release.subprocess.check_output", side_effect=[index, remote_native]
                ):
                    descriptors = saved_descriptors(saved, config, reference)
        self.assertEqual(descriptors["index_digest"], index_digest)
        self.assertEqual(descriptors["platform_digest"], remote_digest)
        self.assertEqual(descriptors["configuration_digest"], config)
        self.assertEqual(descriptors["raw_index_document"], native)

    def test_registry_descriptor_requires_distinct_native_identity(self) -> None:
        digest = "sha256:" + "a" * 64
        native = {
            "digest": "sha256:" + "b" * 64,
            "platform": {"os": "linux", "architecture": "amd64"},
        }
        valid = {"digest": digest, "manifests": [native]}
        reference = "ghcr.io/owner/image@" + digest
        with patch("beta_release.run", return_value=json.dumps(valid)):
            self.assertEqual(
                registry_record(reference, "linux/amd64")["platform_digest"], native["digest"]
            )
        for manifests in (
            [],
            [native, native],
            [{**native, "digest": digest}],
            [native, {**native, "platform": {"os": "linux", "architecture": "arm64"}}],
        ):
            with (
                self.subTest(manifests=manifests),
                patch(
                    "beta_release.run", return_value=json.dumps({**valid, "manifests": manifests})
                ),
                self.assertRaises(ValueError),
            ):
                registry_record(reference, "linux/amd64")

    def test_disposable_registry_manifest_uses_the_same_release_schema(self) -> None:
        value = candidate()
        host = "127.0.0.1:5055"
        for image in value["images"].values():
            image["reference"] = image["reference"].replace("ghcr.io", host)
        beta_release.validate_manifest(value, registry_host=host)
        with patch(
            "beta_release.run",
            return_value=json.dumps(
                {
                    "digest": value["images"]["backend"]["index_digest"],
                    "manifests": [
                        {
                            "digest": value["images"]["backend"]["platform_digest"],
                            "platform": {"os": "linux", "architecture": "amd64"},
                        }
                    ],
                }
            ),
        ):
            self.assertEqual(
                registry_record(
                    value["images"]["backend"]["reference"],
                    "linux/amd64",
                    registry_host=host,
                )["index_digest"],
                value["images"]["backend"]["index_digest"],
            )

    def test_release_rehearsal_is_hosted_read_only_and_reuses_pipeline(self) -> None:
        workflow = (ROOT / ".github/workflows/beta-release-rehearsal.yml").read_text()
        self.assertIn("runs-on: ubuntu-24.04", workflow)
        self.assertIn("version: v0.38.1", workflow)
        self.assertIn("packages: read", workflow)
        self.assertIn('| tee "$log"', workflow)
        self.assertIn("if: always()", workflow)
        self.assertNotIn("packages: write", workflow)
        self.assertNotIn("actions/attest-build-provenance@", workflow)
        self.assertIn("--hosted", workflow)
        self.assertIn("push:", workflow)
        source = (ROOT / "scripts/rehearse-beta-release.py").read_text()
        self.assertIn("_publisher.run_pipeline(root, output)", source)
        self.assertNotIn('"docker", "login", "ghcr.io"', source)

    def test_interrupted_artifact_parent_allows_child_cleanup(self) -> None:
        with tempfile.TemporaryDirectory(prefix="beta-child-cleanup-test-") as temporary:
            artifact = Path(temporary)
            (artifact / "smoke-beta-images.py").write_text(
                textwrap.dedent("""\
                import signal, time
                from pathlib import Path
                def cleanup(number, frame):
                    Path('cleaned').write_text('owned child cleanup completed')
                    raise SystemExit(128 + number)
                signal.signal(signal.SIGTERM, cleanup)
                Path('started').touch()
                while True:
                    time.sleep(0.1)
                """)
            )
            controller = (
                textwrap.dedent("""\
                import os, signal, sys, threading, time
                from pathlib import Path
                sys.path.insert(0, SCRIPTS)
                from beta_release import run_artifact_smoke
                artifact = Path(ARTIFACT)
                def interrupt(number, frame):
                    raise SystemExit(128 + number)
                signal.signal(signal.SIGTERM, interrupt)
                def send_signal():
                    deadline = time.monotonic() + 5
                    while not (artifact / 'started').exists():
                        if time.monotonic() >= deadline:
                            os.kill(os.getpid(), signal.SIGTERM)
                            return
                        time.sleep(0.01)
                    os.kill(os.getpid(), signal.SIGTERM)
                threading.Thread(target=send_signal, daemon=True).start()
                run_artifact_smoke(artifact, local=True, postgres_image="sha256:" + "0" * 64)
                """)
                .replace("SCRIPTS", repr(str(ROOT / "scripts")))
                .replace("ARTIFACT", repr(str(artifact)))
            )
            result = subprocess.run([sys.executable, "-c", controller], check=False, timeout=10)
            self.assertEqual(result.returncode, 143)
            self.assertTrue((artifact / "cleaned").is_file())

    def test_distinct_digests_and_trusted_build_inputs(self) -> None:
        for field in ("index_digest", "platform_digest"):
            value = candidate()
            value["images"]["frontend"][field] = value["images"]["backend"][field]
            if field == "index_digest":
                value["images"]["frontend"]["reference"] = (
                    "ghcr.io/alessandrorossato/florabase-frontend@"
                    + value["images"]["backend"][field]
                )
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_manifest(value)
        value = candidate()
        value["build_inputs"]["base_images"]["python"] = "python:3.14@sha256:" + "f" * 64
        with self.assertRaises(ValueError):
            validate_manifest(value)

    def test_published_schema_is_enforced(self) -> None:
        base = candidate()
        mutations = []
        for field in base:
            v = copy.deepcopy(base)
            del v[field]
            mutations.append(v)
        for field in ("run_id", "run_attempt"):
            v = copy.deepcopy(base)
            v["workflow"][field] = None
            mutations.append(v)
        for owner in ("foreign", "alessandrorossato"):
            v = copy.deepcopy(base)
            v["images"]["frontend"]["reference"] = v["images"]["backend"]["reference"].replace(
                "alessandrorossato", owner
            )
            mutations.append(v)
        for field in ("scanner", "buildkit", "sbom_generator", "dockerfile_frontend"):
            v = copy.deepcopy(base)
            v["build_inputs"][field] = "example:latest"
            mutations.append(v)
        v = copy.deepcopy(base)
        v["build_inputs"]["base_images"]["python"] = "python:latest"
        mutations.append(v)
        for i, value in enumerate(mutations):
            with self.subTest(case=i), self.assertRaises(ValueError):
                validate_manifest(value)

    def test_attestation_policy_cannot_be_repo_only(self) -> None:
        policy = (ROOT / "docs/archive/BETA-IMAGE-001/beta-image-001.md").read_text()
        for flag in (
            "--signer-workflow",
            "--source-ref",
            "--deny-self-hosted-runners",
            "--source-digest",
        ):
            self.assertIn(flag, policy)

    def test_no_automatic_release_trigger_and_least_privilege(self) -> None:
        workflow = (ROOT / ".github/workflows/beta-images.yml").read_text()
        self.assertIn("workflow_dispatch:", workflow)
        self.assertNotIn("pull_request", workflow)
        self.assertNotIn("  push:", workflow)
        self.assertIn("environment: beta-release", workflow)
        self.assertIn("secrets.RELEASE_APPROVED_SHA", workflow)
        self.assertEqual(workflow.count("packages: write"), 1)
        self.assertIn("needs: verify", workflow)
        self.assertIn("--verify-tag", (ROOT / "scripts/publish-beta-images.py").read_text())

    def test_trusted_ci_workflow_pins_actions_to_full_commit_shas(self) -> None:
        workflow = (ROOT / ".github/workflows/ci.yml").read_text()
        uses = re.findall(r"^\s*(?:-\s+)?uses:\s*([^\s#]+)", workflow, re.M)
        self.assertEqual(len(uses), 8)
        for reference in uses:
            with self.subTest(reference=reference):
                self.assertRegex(
                    reference,
                    r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_./-]+@[0-9a-f]{40}$",
                )
        self.assertEqual(
            uses.count("actions/checkout@d23441a48e516b6c34aea4fa41551a30e30af803"),
            4,
        )
        self.assertEqual(
            uses.count("actions/upload-artifact@cf430e030ddbb5b0abf93d22962f4752f3646cd9"),
            4,
        )
        for job_name in ("quality", "integration", "build", "release-migration"):
            self.assertIn(f"name: {job_name}", workflow)


INDEX_TYPE = "application/vnd.oci.image.index.v1+json"


class FakeResponse:
    def __init__(self, body: bytes, headers: dict[str, str]) -> None:
        self.body = body
        self.headers = headers

    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def read(self) -> bytes:
        return self.body


def token_response() -> FakeResponse:
    return FakeResponse(b'{"token": "registry-fixture"}', {})


def manifest_response(body: bytes = b'{"schemaVersion": 2, "manifests": []}') -> FakeResponse:
    digest = "sha256:" + hashlib.sha256(body).hexdigest()
    return FakeResponse(body, {"Docker-Content-Digest": digest, "Content-Type": INDEX_TYPE})


def http_error(code: int, body: bytes = b"") -> urllib.error.HTTPError:
    return urllib.error.HTTPError(
        "https://ghcr.io/fixture",
        code,
        "fixture",
        email.message.Message(),
        io.BytesIO(body),
    )


def registry(*answers: object) -> Any:
    """Answer the token request, then the manifest request, in order."""
    queue = list(answers)

    def urlopen(request: Any, timeout: float) -> Any:
        answer = queue.pop(0)
        if isinstance(answer, BaseException):
            raise answer
        return answer

    return patch.object(publisher.urllib.request, "urlopen", side_effect=urlopen)


class RegistryPreflightTests(unittest.TestCase):
    """GHCR existence checks: only a definite registry "unknown" counts as absent."""

    def lookup(self, *answers: object, actions: str = "pull,push") -> str | None:
        with registry(*answers) as opener:
            result: str | None = publisher.published_digest(
                "alessandrorossato/florabase-backend",
                "0.1.0-beta.3",
                "actor",
                "secret",
                actions=actions,
            )
        token, manifest = (call.args[0] for call in opener.call_args_list)
        self.assertIn(
            "scope=repository%3Aalessandrorossato%2Fflorabase-backend%3A"
            + urllib.parse.quote(actions, safe=""),
            token.full_url,
        )
        self.assertTrue(token.get_header("Authorization").startswith("Basic "))
        self.assertEqual(manifest.get_header("Authorization"), "Bearer registry-fixture")
        self.assertIn(INDEX_TYPE, manifest.get_header("Accept"))
        self.assertTrue(
            manifest.full_url.endswith(
                "/v2/alessandrorossato/florabase-backend/manifests/0.1.0-beta.3"
            )
        )
        return result

    def test_existing_application_version_returns_its_digest(self) -> None:
        response = manifest_response()
        self.assertEqual(
            self.lookup(token_response(), response), response.headers["Docker-Content-Digest"]
        )

    def test_definitely_absent_image(self) -> None:
        for code in ("MANIFEST_UNKNOWN", "NAME_UNKNOWN"):
            body = json.dumps({"errors": [{"code": code, "message": "unknown"}]}).encode()
            with self.subTest(code=code):
                self.assertIsNone(self.lookup(token_response(), http_error(404, body)))

    def test_rehearsal_candidate_policy_follows_the_base_version(self) -> None:
        rehearsal = load_tool("rehearse-beta-release")
        with tempfile.TemporaryDirectory(prefix="rehearsal-base-") as temporary:
            root = Path(temporary)

            def git(*args: str) -> str:
                return subprocess.run(
                    ["git", "-C", temporary, "-c", "user.name=t", "-c", "user.email=t@t", *args],
                    check=True,
                    capture_output=True,
                    text=True,
                ).stdout.strip()

            git("init", "-q")
            git("commit", "-q", "--allow-empty", "-m", "no inputs")
            empty = git("rev-parse", "HEAD")
            (root / "release").mkdir()
            (root / "release/inputs.json").write_text('{"version": "0.1.0-beta.5"}')
            git("add", ".")
            git("commit", "-q", "-m", "beta.5")
            base = git("rev-parse", "HEAD")
            candidate = rehearsal.release_candidate
            self.assertFalse(candidate(root, base, "0.1.0-beta.5"))  # Ordinary development PR.
            self.assertTrue(candidate(root, base, "0.1.0-beta.6"))  # Version bump: candidate.
            for strict in ("", "0" * 40, "f" * 40, empty, "HEAD", base[:12]):
                with self.subTest(base=strict):
                    self.assertTrue(candidate(root, strict, "0.1.0-beta.5"))

    def test_rehearsal_refuses_reuse_only_for_release_candidates(self) -> None:
        rehearsal = load_tool("rehearse-beta-release")
        pinned = "sha256:" + "a" * 64
        locked = {
            "version": "0.1.0-beta.5",
            "postgresql": {"version": "18.6", "index_digest": pinned},
        }
        published = "sha256:" + "b" * 64

        def lookups(app: str | None, postgres: str | None) -> Any:
            def lookup(repository: str, tag: str, *_: object, **__: object) -> str | None:
                return postgres if repository.endswith("postgres") else app

            return patch.object(rehearsal, "published_digest", side_effect=lookup)

        environment = {"GITHUB_TOKEN": "t", "GITHUB_ACTOR": "a"}
        with patch.dict(os.environ, environment):
            with lookups(published, pinned), self.assertRaisesRegex(ValueError, "refuses reuse"):
                rehearsal.verify_ghcr_read_only(locked, True)
            with lookups(published, pinned):
                observed = rehearsal.verify_ghcr_read_only(locked, False)
            self.assertFalse(observed["release_candidate"])
            self.assertEqual(observed["tags"]["backend"]["status"], "published_base_version")
            with lookups(None, None):
                observed = rehearsal.verify_ghcr_read_only(locked, True)
            self.assertEqual(observed["tags"]["frontend"]["status"], "absent")
            # The PostgreSQL identity gate applies to every rehearsal.
            for candidate in (True, False):
                with (
                    self.subTest(candidate=candidate),
                    lookups(None if candidate else published, published),
                    self.assertRaisesRegex(ValueError, "PostgreSQL"),
                ):
                    rehearsal.verify_ghcr_read_only(locked, candidate)
        workflow = (ROOT / ".github/workflows/beta-release-rehearsal.yml").read_text()
        self.assertIn("github.event.pull_request.base.sha || github.event.before", workflow)
        self.assertIn('--base "$BASE_SHA"', workflow)
        # Protected publication keeps its own unconditional reuse refusal.
        self.assertNotIn("release_candidate", (ROOT / "scripts/publish-beta-images.py").read_text())

    def test_rehearsal_ghcr_probe_requests_pull_only(self) -> None:
        body = json.dumps({"errors": [{"code": "MANIFEST_UNKNOWN", "message": "unknown"}]}).encode()
        self.assertIsNone(self.lookup(token_response(), http_error(404, body), actions="pull"))

    def test_unauthorized_registry_refuses(self) -> None:
        denied = b'{"errors": [{"code": "DENIED", "message": "denied"}]}'
        for answers in (
            (http_error(401),),
            (http_error(403, denied),),
            (token_response(), http_error(401, denied)),
            (token_response(), http_error(403, denied)),
            # A 404 that is really an authorization refusal is not an absence.
            (token_response(), http_error(404, denied)),
        ):
            with self.subTest(answers=answers), registry(*answers), self.assertRaises(ValueError):
                publisher.published_digest("owner/image", "1", "actor", "secret")

    def test_unavailable_registry_refuses(self) -> None:
        for answers in (
            (urllib.error.URLError("unreachable"),),
            (TimeoutError(),),
            (token_response(), http_error(500)),
            (token_response(), http_error(503)),
            (token_response(), http_error(429)),
            (token_response(), urllib.error.URLError("reset")),
        ):
            with self.subTest(answers=answers), registry(*answers), self.assertRaises(ValueError):
                publisher.published_digest("owner/image", "1", "actor", "secret")

    def test_malformed_response_refuses(self) -> None:
        good = manifest_response()
        for answers in (
            (FakeResponse(b"not json", {}),),
            (FakeResponse(b'{"token": ""}', {}),),
            (FakeResponse(b"[]", {}),),
            (token_response(), http_error(404, b"not json")),
            (token_response(), http_error(404, b'{"errors": []}')),
            (
                token_response(),
                http_error(404, b'{"errors": [{"code": "MANIFEST_UNKNOWN"}, "bad"]}'),
            ),
            (token_response(), http_error(404, b'{"errors": [{"message": "x"}]}')),
            (token_response(), FakeResponse(b"not json", good.headers)),
            (
                token_response(),
                FakeResponse(good.body, {**good.headers, "Docker-Content-Digest": ""}),
            ),
            (
                token_response(),
                FakeResponse(b'{"schemaVersion": 2, "x": 1}', good.headers),
            ),
            (
                token_response(),
                FakeResponse(good.body, {**good.headers, "Content-Type": "text/html"}),
            ),
            (
                token_response(),
                FakeResponse(
                    b'{"schemaVersion": 1}',
                    {**manifest_response(b'{"schemaVersion": 1}').headers},
                ),
            ),
        ):
            with (
                self.subTest(answers=answers),
                registry(*answers),
                self.assertRaises(ValueError),
            ):
                publisher.published_digest("owner/image", "1", "actor", "secret")

    def test_release_scripts_parse_on_the_runner_python(self) -> None:
        # The protected workflow runs these with ubuntu-24.04's Python 3.12, while the repository
        # formatter targets 3.14 (it rewrites `except (A, B):` into 3.14-only syntax).
        for name in (
            "publish-beta-images.py",
            "rehearse-beta-release.py",
            "beta_release.py",
            "beta-release-checks.py",
            "release-tools.py",
            "smoke-beta-images.py",
            "disposable_workflow.py",
            "compose_stacks.py",
            "workflow_resources.py",
        ):
            with self.subTest(name=name):
                source = (ROOT / "scripts" / name).read_text()
                ast.parse(source, name, feature_version=(3, 12))

    def test_invalid_reference_is_refused_before_any_request(self) -> None:
        for repository, tag in (("Owner/Image", "1"), ("owner/image", "1/../x"), ("o", "")):
            with self.subTest(repository=repository), registry() as opener:
                with self.assertRaises(ValueError):
                    publisher.published_digest(repository, tag, "actor", "secret")
                opener.assert_not_called()

    def publish(self, lookups: dict[str, str | Exception | None]) -> tuple[Any, Any, Path]:
        sha = "c" * 40
        environment = {
            "GITHUB_ACTIONS": "true",
            "GITHUB_REF": "refs/heads/main",
            "GITHUB_SHA": sha,
            "GITHUB_EVENT_NAME": "workflow_dispatch",
            "GITHUB_REPOSITORY": "alessandrorossato/florabase",
            "GITHUB_WORKFLOW_REF": "alessandrorossato/florabase/.github/workflows/beta-images.yml@refs/heads/main",
            "RUNNER_ENVIRONMENT": "github-hosted",
            "APPROVED_SHA": sha,
            "GITHUB_RUN_ID": "1",
            "GITHUB_RUN_ATTEMPT": "1",
            "GITHUB_ACTOR": "fixture",
            "REGISTRY_TOKEN": "fixture-only",
        }
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        target = Path(temporary.name) / "output"

        def output(*args: str) -> str:
            return {"rev-parse": sha, "status": ""}.get(args[1], "0") if args[0] == "git" else "0"

        def lookup(repository: str, tag: str, actor: str, secret: str) -> str | None:
            self.assertEqual((actor, secret), ("fixture", "fixture-only"))
            answer = lookups[repository]
            if isinstance(answer, Exception):
                raise answer
            return answer

        def execute(command: list[str], **_: Any) -> subprocess.CompletedProcess[str]:
            if command[:3] == ["docker", "buildx", "build"]:
                raise ValueError("stop at build")
            return subprocess.CompletedProcess(command, 0)

        with (
            patch.dict(os.environ, environment, clear=True),
            patch.object(sys, "argv", ["publish", "--output", str(target)]),
            patch.object(publisher, "check_toolchain"),
            patch.object(
                publisher,
                "disposable_registry",
                return_value=nullcontext(("127.0.0.1:5055", 5055)),
            ),
            patch.object(publisher, "run", side_effect=output),
            patch.object(publisher, "published_digest", side_effect=lookup),
            patch.object(
                publisher,
                "local_postgres_identity",
                side_effect=ValueError("stop after preflight"),
            ) as rebuild,
            patch.object(
                publisher.subprocess,
                "run",
                side_effect=execute,
            ) as commands,
            self.assertRaises(ValueError) as raised,
        ):
            publisher.main()
        self.raised = str(raised.exception)
        return commands, rebuild, target

    @staticmethod
    def ran(commands: Any, prefix: list[str]) -> bool:
        return any(call.args[0][: len(prefix)] == prefix for call in commands.call_args_list)

    def lookups(self, **changes: str | Exception | None) -> dict[str, str | Exception | None]:
        value: dict[str, str | Exception | None] = {
            "alessandrorossato/florabase-backend": None,
            "alessandrorossato/florabase-frontend": None,
            "alessandrorossato/florabase-postgres": None,
        }
        value.update({"alessandrorossato/florabase-" + key: item for key, item in changes.items()})
        return value

    def test_existing_application_version_blocks_and_cleans_up(self) -> None:
        for service in ("backend", "frontend"):
            with self.subTest(service=service):
                commands, rebuild, target = self.publish(
                    self.lookups(**{service: "sha256:" + "e" * 64})
                )
                self.assertIn("already exists", self.raised)
                rebuild.assert_not_called()
                self.assertEqual(
                    json.loads((target / "diagnostics/publication-state.json").read_text())[
                        "stages"
                    ]["VALIDATE"]["status"],
                    "failed",
                )
                # Cleanup after an early error: no builder existed, so none is removed; the
                # registry login is always revoked.
                self.assertFalse(self.ran(commands, ["docker", "buildx", "create"]))
                self.assertFalse(self.ran(commands, ["docker", "buildx", "rm"]))
                self.assertTrue(self.ran(commands, ["docker", "logout", "ghcr.io"]))

    def test_registry_failure_blocks_publication_and_cleans_up(self) -> None:
        failure = ValueError("cannot determine whether fixture exists (HTTP 401)")
        for service in ("backend", "frontend", "postgres"):
            with self.subTest(service=service):
                commands, rebuild, _ = self.publish(self.lookups(**{service: failure}))
                self.assertIn("cannot determine", self.raised)
                rebuild.assert_not_called()
                self.assertFalse(self.ran(commands, ["docker", "buildx", "create"]))
                self.assertFalse(self.ran(commands, ["docker", "buildx", "rm"]))
                self.assertTrue(self.ran(commands, ["docker", "logout", "ghcr.io"]))

    def test_existing_postgres_tag_with_pinned_digest_is_reused(self) -> None:
        pinned = inputs(ROOT)["postgresql"]["index_digest"]
        commands, rebuild, _ = self.publish(self.lookups(postgres=pinned))
        self.assertEqual(self.raised, "stop at build")
        # The published identity is reused: no rebuild into the registry.
        rebuild.assert_not_called()
        self.assertTrue(self.ran(commands, ["docker", "buildx", "create"]))
        # The builder was created, so cleanup removes it.
        self.assertTrue(self.ran(commands, ["docker", "buildx", "rm"]))
        self.assertTrue(self.ran(commands, ["docker", "logout", "ghcr.io"]))

    def test_existing_postgres_tag_with_other_digest_blocks(self) -> None:
        commands, rebuild, _ = self.publish(self.lookups(postgres="sha256:" + "f" * 64))
        self.assertIn("differs from the pinned identity", self.raised)
        rebuild.assert_not_called()
        self.assertFalse(self.ran(commands, ["docker", "buildx", "create"]))
        self.assertTrue(self.ran(commands, ["docker", "logout", "ghcr.io"]))

    def test_absent_postgres_tag_builds_the_pinned_identity(self) -> None:
        commands, rebuild, _ = self.publish(self.lookups())
        self.assertEqual(self.raised, "stop after preflight")
        rebuild.assert_called_once()
        self.assertTrue(self.ran(commands, ["docker", "buildx", "rm"]))


class SharedPublicationTests(unittest.TestCase):
    def test_shared_pipeline_validates_complete_output_before_any_version_write(
        self,
    ) -> None:
        for fault in (None, "inventory", "extra", "smoke", "portable", "tag appeared", "promotion"):
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as temporary:
                self.exercise_pipeline(Path(temporary) / "output", fault)

    def exercise_pipeline(self, output: Path, fault: str | None) -> None:
        host = "127.0.0.1:5055"
        value = candidate()
        sha = subprocess.check_output(
            ["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True
        ).strip()
        value["source"]["revision"] = sha
        for image in value["images"].values():
            image["reference"] = image["reference"].replace("ghcr.io", host)
        images = value["images"]
        tagged: dict[tuple[str, str], str] = {}

        def postgres(*args: Any, evidence_dir: Path, **kwargs: Any) -> None:
            evidence_dir.mkdir()
            (evidence_dir / "postgres-oci-evidence.json").write_text("{}")
            if fault == "inventory":
                (output / "assets/postgres-reproducibility").mkdir()
            if fault == "extra":
                (output / "assets/extra.json").write_text("{}")

        def smoke(*args: Any, **kwargs: Any) -> None:
            if fault == "smoke":
                raise ValueError("injected smoke failure")
            if fault == "tag appeared":
                tagged[("alessandrorossato/florabase-frontend", value["version"])] = "unexpected"

        def portable_smoke(
            _root: Path, compose: Path, refs: dict[str, str], head: str, _log_path: Path
        ) -> None:
            self.assertEqual(head, value["alembic_head"])
            self.assertEqual(set(refs), {"backend", "frontend", "postgresql"})
            self.assertEqual(compose, ROOT / beta_release.INSTALL_COMPOSE)
            if fault == "portable":
                raise ValueError("injected portable smoke failure")

        def promote(reference: str, tag: str, registry: str) -> str:
            self.assertEqual(registry, host)
            repository, digest = reference.split("@")
            if fault == "promotion" and repository.endswith("-frontend"):
                raise ValueError("injected partial promotion")
            self.assertTrue((output / "assets/RELEASE.md").is_file())
            tagged[(repository.split("/", 1)[1], tag)] = digest
            return digest

        def cli(*args: str) -> str:
            return {"rev-parse": sha, "status": "", "show": "1762387200"}[args[1]]

        real_run = subprocess.run
        with (
            patch.object(publisher, "run", side_effect=cli),
            patch.object(publisher, "check_toolchain"),
            patch.object(publisher, "disposable_registry", return_value=nullcontext((host, 5055))),
            patch.object(publisher, "pinned_builder", return_value=nullcontext("fixture")),
            patch.object(
                publisher,
                "lookup_manifest",
                side_effect=lambda origin, repo, tag: tagged.get((repo, tag)),
            ),
            patch.object(publisher, "local_postgres_identity", side_effect=postgres),
            patch.object(
                publisher,
                "build_application_image",
                side_effect=lambda root, builder, service, *args: images[service]["reference"],
            ),
            patch.object(publisher, "manifest", return_value=value),
            patch.object(publisher.subprocess, "run", wraps=subprocess.run) as commands,
            patch.object(publisher, "scan_images"),
            patch.object(
                publisher,
                "software_bill_of_materials",
                side_effect=lambda ref, path, scanner: path.write_text("{}"),
            ),
            patch.object(publisher, "run_artifact_smoke", side_effect=smoke),
            patch.object(publisher, "run_portable_smoke", side_effect=portable_smoke),
            patch.object(publisher, "promote_image", side_effect=promote) as promotion,
        ):

            def docker_only(command: list[str], **kwargs: Any) -> Any:
                if command[0] == "docker":
                    self.assertEqual(command[1], "pull")
                    return None
                if fault is not None and "archive" in command:
                    return real_run([*command, "docs/decisions"], **kwargs)
                return real_run(command, **kwargs)

            commands.side_effect = docker_only
            if fault is None:
                publisher.run_pipeline(ROOT, output)
                self.assertEqual(promotion.call_count, 6)
            else:
                with self.assertRaises(ValueError):
                    publisher.run_pipeline(ROOT, output)
                self.assertEqual(promotion.call_count, 2 if fault == "promotion" else 0)

        state = read(output / "diagnostics/publication-state.json")
        self.assertTrue(
            (output / "diagnostics/postgres-reproducibility/postgres-oci-evidence.json").is_file()
        )
        stages = state["stages"]
        if fault is None:
            self.assertTrue(all(stage["status"] == "passed" for stage in stages.values()))
            assets = state["release"]["assets"]
            # RELEASE.md, manifest, PostgreSQL SBOM and source archive.
            self.assertEqual(len(assets), 4)
            self.assertEqual(
                {name: (item["size"], item["sha256"]) for name, item in assets.items()},
                beta_release.release_asset_inventory(output / "assets"),
            )
            self.assertEqual(set(state["promoted_latest"]), {"backend", "frontend", "postgresql"})
            for service in ("backend", "frontend"):
                self.assertEqual(
                    tagged[(f"alessandrorossato/florabase-{service}", "latest")],
                    images[service]["index_digest"],
                )
            self.assertEqual(
                tagged[("alessandrorossato/florabase-postgres", "latest")],
                value["postgresql"]["index_digest"],
            )
        else:
            failed = {"smoke": "SCAN/SMOKE", "portable": "SCAN/SMOKE", "promotion": "PROMOTE"}.get(
                fault, "VALIDATE ASSETS"
            )
            self.assertEqual(stages[failed]["status"], "failed")
            if fault == "promotion":
                self.assertEqual(set(state["promoted"]), {"backend"})
                self.assertEqual(state["promotion_in_progress"], "frontend")
            else:
                self.assertNotIn("PROMOTE", stages)

    def test_actual_finalizer_refuses_draft_digest_mismatch_and_refuses_resume(
        self,
    ) -> None:
        value = candidate()
        sha = value["source"]["revision"]
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "output"
            publication = publisher.Publication(output)
            assets = output / "assets"
            assets.mkdir()
            for name in (
                "RELEASE.md",
                beta_release.POSTGRES_SBOM,
                f"florabase-{value['version']}-source.tar.gz",
            ):
                (assets / name).write_text("fixture")
            (assets / "release-manifest.json").write_text(json.dumps(value))
            inventory = beta_release.release_asset_inventory(assets)
            request = release_finalization_inputs(value, sha, inventory)
            publication.state.update(
                source_sha=sha,
                mode="protected",
                release=request,
                run_id="1",
                run_attempt="1",
                stages={
                    "PROMOTE": {"status": "passed"},
                    "ATTEST": {"status": "passed"},
                },
            )
            publication.save()
            valid_draft: dict[str, Any] = {
                "id": 42,
                "draft": True,
                "prerelease": request["prerelease"],
                "assets": [
                    {"name": name, "size": size, "digest": digest}
                    for name, (size, digest) in inventory.items()
                ],
            }
            for valid in (False, True):
                with self.subTest(valid=valid):
                    publication.save()
                    draft = copy.deepcopy(valid_draft)
                    if not valid:
                        draft["assets"][0]["digest"] = "wrong"
                    with (
                        patch.dict(
                            os.environ,
                            {"GITHUB_RUN_ID": "1", "GITHUB_RUN_ATTEMPT": "1"},
                        ),
                        patch.object(publisher, "run", return_value=sha),
                        patch.object(publisher, "require_publication_identity"),
                        patch.object(publisher, "require_remote_release_tag"),
                        patch.object(publisher, "locate_draft_release", return_value=draft),
                        patch.object(publisher.subprocess, "run") as mutation,
                    ):
                        if valid:
                            publisher.finalize_release(output)
                            self.assertEqual(mutation.call_count, 2)
                            self.assertEqual(
                                mutation.call_args.args[0][:4],
                                ["gh", "api", "--method", "PATCH"],
                            )
                            self.assertIn(
                                "prerelease=" + json.dumps(request["prerelease"]),
                                mutation.call_args.args[0],
                            )
                        else:
                            with self.assertRaisesRegex(ValueError, "digest/size"):
                                publisher.finalize_release(output)
                            self.assertEqual(mutation.call_count, 1)
                        with self.assertRaisesRegex(ValueError, "refuse to finalize"):
                            publisher.finalize_release(output)

    def test_postgres_latest_promotion_refuses_major_version_jump(self) -> None:
        with (
            tempfile.TemporaryDirectory() as temporary,
            patch.object(publisher, "POSTGRES_LATEST_MAJOR", "17"),
        ):
            output = Path(temporary) / "output"
            with self.assertRaisesRegex(
                ValueError, "refuse to move florabase-postgres:latest across PostgreSQL major"
            ):
                self.exercise_pipeline(output, None)
            state = read(output / "diagnostics/publication-state.json")
            self.assertEqual(state["stages"]["PREPARE"]["status"], "failed")
            self.assertNotIn("PROMOTE", state["stages"])
            self.assertEqual(state["promoted"], {})
            self.assertEqual(state["promoted_latest"], {})

    def test_runtime_dev_tool_check_survives_python_optimize(self) -> None:
        smoke_path = Path(__file__).with_name("smoke-beta-images.py")
        tree = ast.parse(smoke_path.read_text(encoding="utf-8"))
        snippet: str | None = None
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Assign)
                and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and node.targets[0].id == "runtime_check"
                and isinstance(node.value, ast.Constant)
                and isinstance(node.value.value, str)
            ):
                snippet = node.value.value
                break
        self.assertIsNotNone(snippet)
        assert snippet is not None
        parsed = ast.parse(snippet)
        self.assertFalse(any(isinstance(node, ast.Assert) for node in ast.walk(parsed)))
        with tempfile.TemporaryDirectory() as temporary:
            fake_site = Path(temporary)
            (fake_site / "florabase.py").write_text("__version__ = '0.1.0-beta.8'\n")
            (fake_site / "pytest.py").write_text("# forbidden dev tool\n")
            result = subprocess.run(
                [sys.executable, "-O", "-c", snippet],
                env={**os.environ, "PYTHONPATH": str(fake_site), "PYTHONOPTIMIZE": "1"},
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("dev tools in runtime image: pytest", result.stderr)


if __name__ == "__main__":
    unittest.main()
