import base64
from typing import cast
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette.requests import Request

from florabase.auth.dependencies import AuthenticatedActor
from florabase.auth.model import AuthSession
from florabase.import_export import api
from florabase.import_export.service import MAX_BYTES, CsvFormatError, DecisionOption, PreviewRow


class _Database:
    def __init__(self) -> None:
        self.committed = False
        self.rolled_back = False

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.rolled_back = True

    def scalars(self, _statement: object) -> list[object]:
        return []


def _session(database: _Database) -> Session:
    return cast(Session, database)


def _actor(*, owner: bool = True, token_digest: bytes = b"t" * 32) -> AuthenticatedActor:
    return AuthenticatedActor(
        user_id=uuid4(),
        login_name="owner",
        display_name="Owner",
        owner=owner,
        session=AuthSession(id=uuid4(), token_digest=token_digest),
    )


def _request(
    body: bytes,
    *,
    content_type: str = "text/csv",
    extra_headers: tuple[tuple[bytes, bytes], ...] = (),
) -> Request:
    headers = [(b"content-type", content_type.encode()), *extra_headers]
    messages = iter([{"type": "http.request", "body": body, "more_body": False}])

    async def receive() -> dict[str, object]:
        return next(messages, {"type": "http.request", "body": b"", "more_body": False})

    return Request(
        {"type": "http", "method": "POST", "path": "/imports/suppliers", "headers": headers},
        receive,
    )


def test_signed_confirmation_and_option_tokens_bind_session_bytes_and_row(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    actor = _actor()
    other = _actor()
    monkeypatch.setattr("florabase.import_export.api.time.time", lambda: 1_800_000_000)
    token = api._token(actor, "suppliers", b"name,kind\nABC,nursery\n")
    assert api._verify_token(actor, "suppliers", b"name,kind\nABC,nursery\n", token)
    assert not api._verify_token(other, "suppliers", b"name,kind\nABC,nursery\n", token)
    assert not api._verify_token(actor, "suppliers", b"changed", token)
    assert not api._verify_token(actor, "locations", b"name,kind\nABC,nursery\n", token)
    old = "1799999099." + api._signature(
        actor, "suppliers", b"name,kind\nABC,nursery\n", 1_799_999_099
    )
    assert not api._verify_token(actor, "suppliers", b"name,kind\nABC,nursery\n", old)
    assert not api._verify_token(actor, "suppliers", b"data", "malformed")

    option = DecisionOption("record", "use_existing", str(uuid4()), "ABC", "details", "snapshot")
    option_token = api._option_token(actor, "suppliers", b"data", 1_800_000_000, 2, option)
    row = PreviewRow(2, "ABC", options=[option])
    public = api._public_rows([row], actor, "suppliers", b"data", 1_800_000_000)
    assert public[0].options[0].token == option_token


def test_request_size_kind_and_csv_response_guards() -> None:
    api._kind("suppliers")
    with pytest.raises(HTTPException) as unsupported:
        api._kind("arbitrary")
    assert unsupported.value.status_code == 404

    async def read() -> None:
        request = _request(b"abc")
        assert await api._read_csv(request, limit=3) == b"abc"
        with pytest.raises(HTTPException) as too_large:
            await api._read_csv(_request(b"abcd"), limit=3)
        assert too_large.value.status_code == 413

    import asyncio

    asyncio.run(read())
    response = api._csv_response("name\r\nABC\r\n", "suppliers.csv")
    assert bytes(response.body).startswith(b"\xef\xbb\xbf")
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"


def test_preview_endpoint_maps_parser_errors_and_counts_outcomes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    actor = _actor()
    database = _Database()
    rows = [
        PreviewRow(2, "Ready", outcome="ready"),
        PreviewRow(3, "Existing", outcome="already_exists"),
        PreviewRow(4, "Choice", outcome="needs_choice"),
    ]
    monkeypatch.setattr(api, "preview", lambda *_args: rows)

    async def invoke() -> None:
        response = await api.preview_import(
            "suppliers",
            _request(b"csv"),
            actor,
            database,  # type: ignore[arg-type]
        )
        assert response.ready == 1
        assert response.already_exists == 1
        assert response.needs_attention == 1
        assert len(response.confirmation_token.split(".")) == 2

        monkeypatch.setattr(
            api, "preview", lambda *_args: (_ for _ in ()).throw(CsvFormatError("bad CSV"))
        )
        with pytest.raises(HTTPException) as invalid:
            await api.preview_import("suppliers", _request(b"bad"), actor, database)  # type: ignore[arg-type]
        assert invalid.value.status_code == 422
        assert invalid.value.detail == "bad CSV"

    import asyncio

    asyncio.run(invoke())


def test_apply_endpoint_commits_exact_json_payload_and_handles_raw_csv(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    actor = _actor()
    data = b"name,kind\nABC,nursery\n"
    token = api._token(actor, "suppliers", data)
    database = _Database()
    seen: list[tuple[str, bytes, dict[tuple[int, str], DecisionOption]]] = []
    option = DecisionOption("record", "use_existing", str(uuid4()), "ABC", "details", "snapshot")
    monkeypatch.setattr(api, "preview", lambda *_args: [PreviewRow(2, "ABC", options=[option])])

    def fake_apply(
        _database: object,
        kind: str,
        body: bytes,
        selected: dict[tuple[int, str], DecisionOption],
    ) -> tuple[int, int, int]:
        seen.append((kind, body, selected))
        return (1, 0, 0)

    monkeypatch.setattr(api, "apply", fake_apply)

    async def invoke() -> None:
        issued = int(token.split(".")[0])
        choice_token = api._option_token(actor, "suppliers", data, issued, 2, option)
        envelope = api.ImportApplyEnvelope(
            csv_base64=base64.b64encode(data).decode(),
            decisions={"2": {"record": choice_token}},
        )
        response = await api.apply_import(
            "suppliers",
            _request(envelope.model_dump_json().encode(), content_type="application/json"),
            actor,
            database,  # type: ignore[arg-type]
            confirmation_token=token,
        )
        assert response.created == 1
        assert database.committed
        assert seen[-1][0:2] == ("suppliers", data)
        assert seen[-1][2] == {(2, "record"): option}

        raw_database = _Database()
        monkeypatch.setattr(api, "preview", lambda *_args: [PreviewRow(2, "ABC")])
        monkeypatch.setattr(api, "apply", lambda *_args: (1, 0, 0))
        raw = await api.apply_import(
            "suppliers",
            _request(data),
            actor,
            _session(raw_database),
            confirmation_token=token,
        )
        assert raw.created == 1
        assert raw_database.committed

    import asyncio

    asyncio.run(invoke())


def test_apply_endpoint_rejects_bad_tokens_choices_and_stale_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    actor = _actor()
    data = b"csv"
    token = api._token(actor, "suppliers", data)
    database = _Database()
    monkeypatch.setattr(api, "preview", lambda *_args: [PreviewRow(2, "ABC")])

    async def invoke() -> None:
        with pytest.raises(HTTPException) as missing:
            await api.apply_import("suppliers", _request(data), actor, _session(database), None)
        assert missing.value.status_code == 409
        with pytest.raises(HTTPException) as non_owner:
            await api.apply_import(
                "suppliers", _request(data), _actor(owner=False), _session(database), token
            )
        assert non_owner.value.status_code == 403

        invalid_json = _request(b"not-json", content_type="application/json")
        with pytest.raises(HTTPException) as malformed:
            await api.apply_import("suppliers", invalid_json, actor, database, token)  # type: ignore[arg-type]
        assert malformed.value.status_code == 422

        encoded = base64.b64encode(data).decode()
        unknown_row = api.ImportApplyEnvelope(
            csv_base64=encoded, decisions={"nope": {"record": "choice"}}
        )
        with pytest.raises(HTTPException) as bad_row:
            await api.apply_import(
                "suppliers",
                _request(unknown_row.model_dump_json().encode(), content_type="application/json"),
                actor,
                database,  # type: ignore[arg-type]
                token,
            )
        assert bad_row.value.status_code == 409
        assert database.rolled_back

        bad_text = api.ImportApplyEnvelope(csv_base64=encoded, decisions={"nope": {}})
        with pytest.raises(HTTPException) as invalid_row_text:
            await api.apply_import(
                "suppliers",
                _request(bad_text.model_dump_json().encode(), content_type="application/json"),
                actor,
                _Database(),  # type: ignore[arg-type]
                token,
            )
        assert invalid_row_text.value.status_code == 409

        monkeypatch.setattr(api, "preview", lambda *_args: [PreviewRow(2, "ABC")])
        missing_option = api.ImportApplyEnvelope(
            csv_base64=encoded, decisions={"2": {"record": "forged"}}
        )
        with pytest.raises(HTTPException) as stale_option:
            await api.apply_import(
                "suppliers",
                _request(
                    missing_option.model_dump_json().encode(), content_type="application/json"
                ),
                actor,
                _Database(),  # type: ignore[arg-type]
                token,
            )
        assert stale_option.value.status_code == 409

        too_large = b"x" * (MAX_BYTES + 1)
        encoded_large = api.ImportApplyEnvelope(
            csv_base64=base64.b64encode(too_large).decode(), decisions={}
        )
        with pytest.raises(HTTPException) as json_size:
            await api.apply_import(
                "suppliers",
                _request(encoded_large.model_dump_json().encode(), content_type="application/json"),
                actor,
                _Database(),  # type: ignore[arg-type]
                token,
            )
        assert json_size.value.status_code == 413
        with pytest.raises(HTTPException) as raw_size:
            await api.apply_import(
                "suppliers",
                _request(too_large),
                actor,
                _session(_Database()),
                token,
            )
        assert raw_size.value.status_code == 413

    import asyncio

    asyncio.run(invoke())


def test_apply_endpoint_rolls_back_preview_and_domain_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    actor = _actor()
    data = b"csv"
    token = api._token(actor, "suppliers", data)

    async def run_csv_failure() -> int:
        database = _Database()
        monkeypatch.setattr(api, "preview", lambda *_args: [PreviewRow(2, "ABC")])
        monkeypatch.setattr(
            api, "apply", lambda *_args: (_ for _ in ()).throw(CsvFormatError("needs attention"))
        )
        with pytest.raises(HTTPException) as rejected:
            await api.apply_import("suppliers", _request(data), actor, database, token)  # type: ignore[arg-type]
        assert database.rolled_back
        return rejected.value.status_code

    async def run_unexpected_failure() -> None:
        database = _Database()
        monkeypatch.setattr(api, "preview", lambda *_args: [PreviewRow(2, "ABC")])
        monkeypatch.setattr(
            api, "apply", lambda *_args: (_ for _ in ()).throw(ValueError("unexpected"))
        )
        with pytest.raises(ValueError, match="unexpected"):
            await api.apply_import("suppliers", _request(data), actor, database, token)  # type: ignore[arg-type]
        assert database.rolled_back

    import asyncio

    async def invoke() -> None:
        assert await run_csv_failure() == 409
        await run_unexpected_failure()

        database = _Database()
        monkeypatch.setattr(
            api,
            "apply",
            lambda *_args: (_ for _ in ()).throw(
                IntegrityError("write", {}, RuntimeError("duplicate"))
            ),
        )
        with pytest.raises(HTTPException) as conflict:
            await api.apply_import("suppliers", _request(data), actor, database, token)  # type: ignore[arg-type]
        assert conflict.value.status_code == 409
        assert database.rolled_back

    asyncio.run(invoke())


def test_format_template_example_and_export_routes_are_exposed() -> None:
    actor = _actor(owner=False)
    database = _Database()
    assert api.get_import_format("suppliers", actor).fields[0].field == "name"
    template = api.download_template("suppliers", actor)
    example = api.download_example("suppliers", actor)
    assert b"name,kind" in template.body
    assert b"Cercatoridisem" in example.body
    exported = api.export_records("suppliers", actor, database)  # type: ignore[arg-type]
    assert exported.headers["content-disposition"].endswith('"florabase-suppliers.csv"')
