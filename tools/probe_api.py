"""Probe the live Umbraco 17 management API to figure out the endpoints,
schemas, and ids we will need for the dump import."""

from __future__ import annotations

import json
import sys

from umbraco_client import UmbracoClient


def main() -> int:
    c = UmbracoClient()
    c.login()

    print("=== document tree (root) ===")
    print(json.dumps(c.get("tree/document/root"), indent=2)[:1500])

    print("\n=== document-type/{home} via id from tree ===")
    home_id = "ec17e87b-3304-4fc3-bfcc-630c909e740d"
    print(json.dumps(c.get(f"document/{home_id}"), indent=2)[:2500])

    print("\n=== children of home ===")
    children = c.get("tree/document/children", parentId=home_id, take=20)
    print(json.dumps(children, indent=2)[:2000])

    print("\n=== media tree root ===")
    print(json.dumps(c.get("tree/media/root", take=30), indent=2)[:2000])

    print("\n=== document-type list ===")
    for path in ["document-type/root", "document-type/items", "document-type"]:
        try:
            r = c.get(path, take=50)
            print(f"OK {path}")
            print(json.dumps(r, indent=2)[:1500])
            break
        except Exception as e:  # noqa: BLE001
            print(f"FAIL {path}: {e}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
