"""Read existing First-article node so we know exactly the payload shape."""

import json
import sys

from umbraco_client import UmbracoClient


def main() -> int:
    c = UmbracoClient()
    c.login()

    # First article from earlier first-article.config: Key 721cda9a-eecf-4980-8895-ce4284c958a3
    article_id = "721cda9a-eecf-4980-8895-ce4284c958a3"
    print(f"=== document/{article_id} ===")
    doc = c.get(f"document/{article_id}")
    print(json.dumps(doc, indent=2)[:8000])

    # also fetch articles parent + categories to grab their ids
    print("\n=== media tree (first 30) ===")
    media = c.get("tree/media/root", take=30)
    print(json.dumps(media, indent=2)[:3000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
