"""Authenticated client for Umbraco 17 Management API.

Performs the OAuth2 + PKCE login flow that the backoffice SPA uses, then
exposes simple wrappers for documents, media, and temporary file uploads.
Run as a script to do a quick auth + capability dump.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
import sys
import urllib.parse
from typing import Any

import requests

BASE_URL = os.environ.get("UMB_BASE", "https://forevka.dev")
USERNAME = os.environ.get("UMB_USER", "zebestforevka@gmail.com")
PASSWORD = os.environ.get("UMB_PASS", "werdwerd2012")
CLIENT_ID = "umbraco-back-office"
REDIRECT_URI = f"{BASE_URL}/umbraco/oauth_complete"


def _b64url(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode("ascii")


class UmbracoClient:
    def __init__(self, base_url: str = BASE_URL) -> None:
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.verify = True
        self.access_token: str | None = None

    def _api(self, path: str) -> str:
        return f"{self.base_url}/umbraco/management/api/v1/{path.lstrip('/')}"

    def login(self, username: str = USERNAME, password: str = PASSWORD) -> str:
        login_resp = self.session.post(
            self._api("security/back-office/login"),
            json={"username": username, "password": password},
            headers={"Accept": "application/json"},
            timeout=15,
        )
        login_resp.raise_for_status()

        verifier = _b64url(secrets.token_bytes(48))
        challenge = _b64url(hashlib.sha256(verifier.encode()).digest())
        state = _b64url(secrets.token_bytes(16))

        params = {
            "client_id": CLIENT_ID,
            "redirect_uri": REDIRECT_URI,
            "response_type": "code",
            "scope": "offline_access",
            "state": state,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        }
        authorize_url = self._api("security/back-office/authorize") + "?" + urllib.parse.urlencode(params)
        auth_resp = self.session.get(authorize_url, allow_redirects=False, timeout=15)
        if auth_resp.status_code not in (302, 303):
            raise RuntimeError(
                f"authorize did not redirect: status={auth_resp.status_code} body={auth_resp.text[:300]}"
            )
        location = auth_resp.headers.get("Location", "")
        parsed = urllib.parse.urlparse(location)
        qs = urllib.parse.parse_qs(parsed.query)
        if "code" not in qs:
            raise RuntimeError(f"no code in authorize redirect: {location}")
        code = qs["code"][0]

        token_resp = self.session.post(
            self._api("security/back-office/token"),
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": REDIRECT_URI,
                "client_id": CLIENT_ID,
                "code_verifier": verifier,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=15,
        )
        token_resp.raise_for_status()
        token = token_resp.json()
        self.access_token = token["access_token"]
        self.session.headers["Authorization"] = f"Bearer {self.access_token}"
        return self.access_token

    def get(self, path: str, **params: Any) -> Any:
        r = self.session.get(self._api(path), params=params, timeout=20)
        r.raise_for_status()
        return r.json() if r.content else None

    def post(self, path: str, json_body: Any | None = None, **kwargs: Any) -> requests.Response:
        r = self.session.post(self._api(path), json=json_body, timeout=30, **kwargs)
        return r

    def put(self, path: str, json_body: Any | None = None) -> requests.Response:
        return self.session.put(self._api(path), json=json_body, timeout=30)

    def delete(self, path: str) -> requests.Response:
        return self.session.delete(self._api(path), timeout=15)


def main() -> int:
    client = UmbracoClient()
    print("logging in...", file=sys.stderr)
    token = client.login()
    print(f"got access_token (len={len(token)})", file=sys.stderr)

    print("\n--- /tree/document/root ---")
    print(json.dumps(client.get("tree/document/root", take=10), indent=2)[:2000])

    print("\n--- /document-type ---")
    dt = client.get("document-type", take=50)
    if isinstance(dt, dict) and "items" in dt:
        for item in dt["items"]:
            print(f"  {item.get('alias','?')}\t{item.get('id','?')}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
