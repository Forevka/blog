"""Upload article images to Umbraco via the Management API.

Workflow per image:
  1. POST /umbraco/management/api/v1/temporary-file as multipart/form-data
     - returns a temporary file id (UUID)
  2. POST /umbraco/management/api/v1/media with body that references the
     temporary file id, plus a name + media type id ("Image" → cc07b313-...)
     - returns the new media's id (UUID)

We persist the resulting filename → media-id map to images_map.json so reruns
are idempotent. Image type id 'cc07b313-0843-4aa8-bbda-871c8da728c8' was seen
in the existing media tree from probe_api.py.

Image manifest below maps each article slug to its hero / card / inline images.
The actual binaries live under <article-name>_files/ in forevka_dump/.
"""

from __future__ import annotations

import json
import mimetypes
import os
import sys
import uuid
from typing import Any

import requests

from umbraco_client import UmbracoClient

DUMP_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "forevka_dump"))
MAP_FILE = os.path.join(os.path.dirname(__file__), "images_map.json")
IMAGE_MEDIA_TYPE_ID = "cc07b313-0843-4aa8-bbda-871c8da728c8"

IMAGE_MANIFEST: dict[str, dict[str, Any]] = {
    "crafting-a-result-pattern-in-c-a-comprehensive-guide": {
        "files_dir": "Crafting a Result Pattern in C#_ A Comprehensive Guide - Forevka_files",
        "hero": "crafting-result-pattern-hero.png",
        "card": "photo-1602475063211-3d98d60e3b1f.jpeg",
        "inline": {
            "result-open-api-spec.png": "result-open-api-spec.png",
        },
    },
    "developing-a-cross-platform-pdf-to-svgpng-wrapper-for-net": {
        "files_dir": "Developing a Cross-Platform PDF-to-SVG_PNG Wrapper for .NET - Forevka_files",
        "hero": "reflection-to-generators-card.png",
        "card": "photo-1602475063211-3d98d60e3b1f.jpeg",
        "inline": {},
    },
    "discriminated-unions-result-pattern-part-1": {
        "files_dir": "Discriminated Unions & Result Pattern - Forevka_files",
        "hero": "crafting-result-pattern-card.png",
        "card": "photo-1602475063211-3d98d60e3b1f.jpeg",
        "inline": {},
    },
}


def _load_map() -> dict[str, str]:
    if os.path.exists(MAP_FILE):
        with open(MAP_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_map(m: dict[str, str]) -> None:
    with open(MAP_FILE, "w", encoding="utf-8") as f:
        json.dump(m, f, indent=2)


def _find_local(files_dir: str, filename: str) -> str:
    """Find file in _files dir, accepting case-insensitive matches.
    Wayback often lower-cases filenames during save."""
    full_dir = os.path.join(DUMP_DIR, files_dir)
    if not os.path.isdir(full_dir):
        raise FileNotFoundError(f"_files dir missing: {full_dir}")
    target = filename.lower()
    for entry in os.listdir(full_dir):
        if entry.lower() == target:
            return os.path.join(full_dir, entry)
    raise FileNotFoundError(f"image not found: {filename} in {files_dir}")


def upload_temp(client: UmbracoClient, path: str) -> str:
    """POST /temporary-file with binary, returns the temporary id (UUID)."""
    temp_id = str(uuid.uuid4())
    name = os.path.basename(path)
    mime = mimetypes.guess_type(name)[0] or "application/octet-stream"
    with open(path, "rb") as f:
        files = {"File": (name, f, mime)}
        data = {"Id": temp_id}
        url = client._api("temporary-file")
        r = client.session.post(url, files=files, data=data, timeout=60)
    if r.status_code not in (200, 201):
        raise RuntimeError(f"temp upload failed for {name}: {r.status_code} {r.text[:300]}")
    return temp_id


def create_media(client: UmbracoClient, name: str, temp_id: str, parent_id: str | None = None) -> str:
    """POST /media to create the media entry. Returns the new media id (UUID)."""
    media_id = str(uuid.uuid4())
    body = {
        "id": media_id,
        "parent": {"id": parent_id} if parent_id else None,
        "mediaType": {"id": IMAGE_MEDIA_TYPE_ID},
        "values": [
            {
                "alias": "umbracoFile",
                "culture": None,
                "segment": None,
                "value": {"temporaryFileId": temp_id},
            }
        ],
        "variants": [
            {
                "culture": None,
                "segment": None,
                "name": name,
            }
        ],
    }
    r = client.post("media", body)
    if r.status_code not in (200, 201):
        raise RuntimeError(f"media create failed for {name}: {r.status_code} {r.text[:500]}")
    location = r.headers.get("Umb-Generated-Resource") or r.headers.get("Location") or media_id
    if "/" in location:
        location = location.rsplit("/", 1)[-1]
    return location


def upload_one(client: UmbracoClient, files_dir: str, filename: str, name_map: dict[str, str]) -> str:
    """Upload an image (idempotent via name_map). Returns media UUID."""
    key = filename.lower()
    if key in name_map:
        return name_map[key]
    path = _find_local(files_dir, filename)
    print(f"  uploading {filename} ({os.path.getsize(path)} bytes)...", flush=True)
    temp_id = upload_temp(client, path)
    media_id = create_media(client, os.path.splitext(filename)[0], temp_id)
    name_map[key] = media_id
    _save_map(name_map)
    return media_id


def main() -> int:
    client = UmbracoClient()
    client.login()
    name_map = _load_map()

    for slug, manifest in IMAGE_MANIFEST.items():
        files_dir = manifest["files_dir"]
        print(f"\n[{slug}]")
        for slot in ("hero", "card"):
            fn = manifest[slot]
            mid = upload_one(client, files_dir, fn, name_map)
            print(f"  {slot}: {fn} -> {mid}")
        for src_url, fn in manifest["inline"].items():
            mid = upload_one(client, files_dir, fn, name_map)
            print(f"  inline {src_url} -> {mid}")

    print(f"\nSaved {len(name_map)} entries to {MAP_FILE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
