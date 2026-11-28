"""Exercise only the owned synthetic Review through its actual HTTP API."""
# ruff: noqa: T201 -- Print only the safe scenario summary, never authentication material.

from __future__ import annotations

import json
from http.cookiejar import CookieJar
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import HTTPCookieProcessor, Request, build_opener

from review import SOURCE, TaxonomyReview


def main() -> None:
    environment = TaxonomyReview()
    environment.validate()
    environment.require_owner()
    credentials = json.loads((SOURCE / ".taxonomy-review/credentials.json").read_text())
    client = build_opener(HTTPCookieProcessor(CookieJar()))
    csrf = ""

    def request(method: str, route: str, body: dict | None = None, status: int = 200):
        headers = {"Origin": environment.url, "Content-Type": "application/json"}
        if csrf:
            headers["X-CSRF-Token"] = csrf
        call = Request(
            environment.url + "/api/v1/" + route,
            data=json.dumps(body).encode() if body is not None else None,
            method=method,
            headers=headers,
        )
        try:
            response = client.open(call, timeout=15)
        except HTTPError as error:
            if error.code != status:
                raise AssertionError((route, error.code, status)) from error
            return None
        with response:
            assert response.status == status, (route, response.status, status)
            data = response.read()
        return json.loads(data) if data else None

    csrf = request(
        "POST",
        "auth/login",
        {
            "login_name": credentials["login"],
            "password": credentials["password"],
        },
    )["csrf_token"]
    tree = request("GET", "explore/taxonomy/tree")
    assert tree["source_available"]
    assert "synthetic" in tree["source"]["version"]
    assert tree["counts"] == {"represented": 8, "living": 5, "current": 7, "historical": 1}
    assert tree["unresolved"] == 2
    assert any(i["synonym_of"] for i in tree["identities"])
    lavender = next(
        i for i in tree["identities"] if i["scientific_name"] == "Lavandula angustifolia"
    )
    prefix = "botanical-identities/" + lavender["id"]
    original = request("GET", prefix)
    taxonomy = request("GET", prefix + "/taxonomy")
    assert taxonomy["link"] is None, "Operator linked Lavender; refusing to replace their work"
    candidates = request("GET", prefix + "/taxonomy/candidates?" + urlencode({"q": "Lavandula"}))
    assert 0 < len(candidates) <= 25
    candidate = next(
        c for c in candidates if c["taxon"]["scientific_name"] == "Lavandula angustifolia"
    )
    assert candidate["classification"]
    request("GET", prefix + "/taxonomy/candidates?" + urlencode({"q": "   "}), status=422)
    names = {key: original[key] for key in ("scientific_name", "cultivar_name", "common_name")}
    request("PUT", prefix, {**names, "common_name": "Lavender · concurrent synthetic edit"})
    payload = {
        "source_taxon_id": candidate["taxon"]["source_taxon_id"],
        "checksum": taxonomy["source"]["checksum"],
        "expected_version": None,
        "identity_updated_at": original["updated_at"],
    }
    request("PUT", prefix + "/taxonomy/link", payload, status=409)
    assert request("GET", prefix + "/taxonomy")["link"] is None
    fresh = request("GET", prefix)
    assert fresh["updated_at"] != original["updated_at"]
    assert "concurrent synthetic edit" in fresh["common_name"]
    renewed = request("GET", prefix + "/taxonomy/candidates?" + urlencode({"q": "Lavandula"}))
    assert renewed == candidates
    confirmed = request(
        "PUT",
        prefix + "/taxonomy/link",
        {
            **payload,
            "identity_updated_at": fresh["updated_at"],
        },
    )
    assert request("GET", prefix)["scientific_name"] == original["scientific_name"]
    request(
        "DELETE",
        prefix + "/taxonomy/link?" + urlencode({"version": confirmed["version"]}),
        status=204,
    )
    request("PUT", prefix, names)
    environment.compose(
        "exec", "-T", "backend", "python", "/review/runtime.py", "source", "unavailable"
    )
    try:
        absent = request("GET", "explore/taxonomy/tree")
        assert not absent["source_available"]
        assert not absent["nodes"]
        assert len(absent["identities"]) == 8
        rosemary = next(
            i for i in absent["identities"] if i["scientific_name"] == "Rosmarinus officinalis"
        )
        saved = request("GET", "botanical-identities/" + rosemary["id"] + "/taxonomy")
        assert saved["link"]["evidence"]["taxon"]["taxonomic_status"] == "synonym"
    finally:
        environment.compose(
            "exec", "-T", "backend", "python", "/review/runtime.py", "source", "available"
        )
    final = request("GET", "explore/taxonomy/tree")
    assert final["counts"] == tree["counts"]
    assert final["unresolved"] == 2
    request("POST", "auth/logout")
    print(
        "Live API scenarios passed: source ready/absent, retained synonym evidence, "
        "blank prefix 422, "
        "stale identity 409, authoritative GET, renewed search, explicit confirmation and unlink. "
        "Eight fixture identities and two unresolved links retained; source restored available."
    )


if __name__ == "__main__":
    main()
