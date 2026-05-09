"""End-to-end import of wayback-dumped articles into Umbraco 17.

Pipeline:
  1. Parse each .md (parse_markdown.parse_all)
  2. Resolve image references against the uploaded image map (upload_images)
  3. Build a BlockGrid `value` per article (typed contentData + settingsData + layout)
  4. PUT existing nodes (1108 First article, 1110 Result pattern), POST third article
  5. Publish via /document/{id}/publish

Run with --dry to dump the assembled payloads to disk without hitting the API.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import uuid
from typing import Any

from parse_markdown import Article, Block, parse_all
from umbraco_client import UmbracoClient

# Block content-type keys (from existing first-article API response)
RICH_TEXT_TYPE = "3678bf30-0761-4fa0-8ea7-8e369180b43a"
CODE_BLOCK_TYPE = "24ccda54-e3a7-416b-b503-6f2f534777f1"
IMAGE_BLOCK_TYPE = "88017cec-da1b-4467-bd8e-77267e9eccbe"

# Settings type keys (from v15 source)
RICH_TEXT_SETTINGS = "3a551aef-0004-46cb-9026-c43cfa453337"
CODE_BLOCK_SETTINGS = "ac645e60-86f5-4a89-8d68-4a1c87f599fe"
IMAGE_BLOCK_SETTINGS = "4115a917-6c5c-46f3-aef0-b76109c84ef9"

# articlesItem doctype + article template
ARTICLES_ITEM_TYPE = "dd9090da-7352-4d7b-bfbb-4cfff566c358"
ARTICLE_TEMPLATE = "72da0212-ad9c-48fc-8a84-645acd587c42"

# Articles parent + C# category from probe
ARTICLES_PARENT = "bd3d7e50-e131-43c3-9a9b-2b5fa0ee096a"
CATEGORY_CSHARP = "bb9d1afe-7c12-4711-bf8a-907caa37ba95"

# Slug -> existing doc id (None = create new)
ARTICLE_SLUG_TO_DOC = {
    "crafting-a-result-pattern-in-c-a-comprehensive-guide": "721cda9a-eecf-4980-8895-ce4284c958a3",  # First article (1108)
    "discriminated-unions-result-pattern-part-1": None,  # Result pattern (1110) — find via tree
    "developing-a-cross-platform-pdf-to-svgpng-wrapper-for-net": None,  # Create new
}

# Filename of the inline `result-open-api-spec.png` -> we'll look it up in image map
INLINE_IMAGE_TITLES = {
    "result-open-api-spec.png": "Proper generated body for all possible return types",
}

DUMP_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "forevka_dump"))
IMAGES_MAP_FILE = os.path.join(os.path.dirname(__file__), "images_map.json")


def _new_uuid() -> str:
    return str(uuid.uuid4())


def _load_image_map() -> dict[str, str]:
    if not os.path.exists(IMAGES_MAP_FILE):
        return {}
    with open(IMAGES_MAP_FILE, encoding="utf-8") as f:
        return json.load(f)


def _media_picker_value(media_id: str) -> list[dict[str, Any]]:
    return [
        {
            "key": _new_uuid(),
            "mediaKey": media_id,
            "mediaTypeAlias": "Image",
            "crops": [],
            "focalPoint": None,
        }
    ]


def _settings_block(type_key: str, *, toc_text: str = "", enabled: bool = False, language: str | None = None) -> dict[str, Any]:
    values: list[dict[str, Any]] = [
        {"editorAlias": "Umbraco.TextBox", "culture": None, "segment": None, "alias": "tocText", "value": toc_text or "1"},
        {"editorAlias": "Umbraco.TextBox", "culture": None, "segment": None, "alias": "tocAnchor", "value": toc_text or "1"},
        {"editorAlias": "Umbraco.TextBox", "culture": None, "segment": None, "alias": "tocLevel", "value": "1"},
        {"editorAlias": "Umbraco.TrueFalse", "culture": None, "segment": None, "alias": "isEnabled", "value": 1 if enabled else 0},
    ]
    if type_key == CODE_BLOCK_SETTINGS:
        values.append({"editorAlias": "Umbraco.TextBox", "culture": None, "segment": None, "alias": "languageName", "value": language or "csharp"})
        values.append({"editorAlias": "Umbraco.CheckBoxList", "culture": None, "segment": None, "alias": "languageTheme", "value": ["github-dark"]})
    return {
        "contentTypeKey": type_key,
        "key": _new_uuid(),
        "values": values,
    }


def _content_block(block: Block, image_map: dict[str, str]) -> dict[str, Any]:
    if block.kind == "text":
        return {
            "contentTypeKey": RICH_TEXT_TYPE,
            "key": _new_uuid(),
            "values": [
                {
                    "editorAlias": "Umbraco.RichText",
                    "culture": None,
                    "segment": None,
                    "alias": "text",
                    "value": {
                        "markup": block.html,
                        "blocks": {"layout": {}, "contentData": [], "settingsData": [], "expose": []},
                    },
                }
            ],
        }
    if block.kind == "code":
        return {
            "contentTypeKey": CODE_BLOCK_TYPE,
            "key": _new_uuid(),
            "values": [
                {
                    "editorAlias": "Umbraco.TextArea",
                    "culture": None,
                    "segment": None,
                    "alias": "content",
                    "value": block.text,
                }
            ],
        }
    if block.kind == "image":
        media_id = image_map.get(block.filename.lower())
        if not media_id:
            raise RuntimeError(f"no media id for {block.filename}")
        title = INLINE_IMAGE_TITLES.get(block.filename, block.alt or "")
        return {
            "contentTypeKey": IMAGE_BLOCK_TYPE,
            "key": _new_uuid(),
            "values": [
                {"editorAlias": "Umbraco.MediaPicker3", "culture": None, "segment": None, "alias": "image", "value": _media_picker_value(media_id)},
                {"editorAlias": "Umbraco.TextBox", "culture": None, "segment": None, "alias": "title", "value": title},
            ],
        }
    raise ValueError(block.kind)


def build_blockgrid(article: Article, image_map: dict[str, str]) -> dict[str, Any]:
    content_data: list[dict[str, Any]] = []
    settings_data: list[dict[str, Any]] = []
    layout: list[dict[str, Any]] = []

    section_index = 0
    for block in article.blocks:
        if block.kind == "text":
            section_index += 1
            content = _content_block(block, image_map)
            settings = _settings_block(RICH_TEXT_SETTINGS, toc_text=str(section_index), enabled=True)
        elif block.kind == "code":
            content = _content_block(block, image_map)
            settings = _settings_block(CODE_BLOCK_SETTINGS, toc_text=str(section_index), enabled=False, language=block.language)
        elif block.kind == "image":
            content = _content_block(block, image_map)
            settings = _settings_block(IMAGE_BLOCK_SETTINGS, toc_text=str(section_index), enabled=False)
        else:
            continue
        content_data.append(content)
        settings_data.append(settings)
        layout.append(
            {
                "$type": "BlockGridLayoutItem",
                "columnSpan": 3,
                "rowSpan": 1,
                "areas": [],
                "contentUdi": None,
                "settingsUdi": None,
                "contentKey": content["key"],
                "settingsKey": settings["key"],
            }
        )

    return {
        "layout": {"Umbraco.BlockGrid": layout},
        "contentData": content_data,
        "settingsData": settings_data,
    }


def _values_for_article(article: Article, image_map: dict[str, str], hero_id: str, card_id: str) -> list[dict[str, Any]]:
    intro = article.intro
    return [
        {"editorAlias": "Umbraco.TextArea", "culture": None, "segment": None, "alias": "title", "value": intro["title"]},
        {"editorAlias": "Umbraco.TextArea", "culture": None, "segment": None, "alias": "description", "value": intro["description"]},
        {"editorAlias": "Umbraco.Integer", "culture": None, "segment": None, "alias": "readTime", "value": intro["read_time"]},
        {"editorAlias": "Umbraco.MediaPicker3", "culture": None, "segment": None, "alias": "heroImage", "value": _media_picker_value(hero_id)},
        {"editorAlias": "Umbraco.MultiNodeTreePicker", "culture": None, "segment": None, "alias": "category", "value": [{"type": "document", "unique": CATEGORY_CSHARP}]},
        {"editorAlias": "Umbraco.TextBox", "culture": None, "segment": None, "alias": "bodyTitle", "value": intro["body_title"][:255]},
        {"editorAlias": "Umbraco.TextBox", "culture": None, "segment": None, "alias": "bodyDescription", "value": intro["body_description"][:255]},
        {"editorAlias": "Umbraco.MediaPicker3", "culture": None, "segment": None, "alias": "cardImage", "value": _media_picker_value(card_id)},
        {"editorAlias": "Umbraco.BlockGrid", "culture": None, "segment": None, "alias": "content", "value": build_blockgrid(article, image_map)},
    ]


def _doc_payload_update(doc_id: str, name: str, values: list[dict[str, Any]]) -> dict[str, Any]:
    """Body for PUT /document/{id}."""
    return {
        "values": values,
        "variants": [{"culture": None, "segment": None, "name": name}],
        "template": {"id": ARTICLE_TEMPLATE},
    }


def _doc_payload_create(name: str, values: list[dict[str, Any]]) -> dict[str, Any]:
    """Body for POST /document."""
    return {
        "id": _new_uuid(),
        "parent": {"id": ARTICLES_PARENT},
        "documentType": {"id": ARTICLES_ITEM_TYPE},
        "template": {"id": ARTICLE_TEMPLATE},
        "values": values,
        "variants": [{"culture": None, "segment": None, "name": name}],
    }


def _find_doc_by_name(client: UmbracoClient, parent_id: str, name: str) -> str | None:
    children = client.get("tree/document/children", parentId=parent_id, take=50)
    for item in children.get("items", []):
        for v in item.get("variants", []):
            if v.get("name") == name:
                return item["id"]
    return None


def _publish(client: UmbracoClient, doc_id: str) -> None:
    r = client.put(f"document/{doc_id}/publish", {"publishSchedules": [{"culture": None, "segment": None}]})
    if r.status_code not in (200, 201, 202, 204):
        raise RuntimeError(f"publish {doc_id} failed: {r.status_code} {r.text[:300]}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true", help="dump payloads to ./tools/payloads/, don't call API")
    ap.add_argument("--slug", help="only process one slug")
    ap.add_argument("--no-publish", action="store_true", help="update content but don't publish")
    args = ap.parse_args()

    image_map = _load_image_map()
    if not image_map and not args.dry:
        print("ERROR: images_map.json missing — run upload_images.py first.", file=sys.stderr)
        return 1

    payloads_dir = os.path.join(os.path.dirname(__file__), "payloads")
    os.makedirs(payloads_dir, exist_ok=True)

    client: UmbracoClient | None = None
    if not args.dry:
        client = UmbracoClient()
        client.login()

    # Per-article hero/card image ids — same source as upload_images.IMAGE_MANIFEST
    from upload_images import IMAGE_MANIFEST  # noqa: PLC0415

    for art in parse_all():
        if args.slug and art.slug != args.slug:
            continue
        manifest = IMAGE_MANIFEST.get(art.slug)
        if not manifest:
            print(f"skip {art.slug} (no manifest)", file=sys.stderr)
            continue
        hero_id = image_map[manifest["hero"].lower()]
        card_id = image_map[manifest["card"].lower()]

        values = _values_for_article(art, image_map, hero_id, card_id)
        payload_path = os.path.join(payloads_dir, f"{art.slug}.json")
        with open(payload_path, "w", encoding="utf-8") as f:
            json.dump({"slug": art.slug, "values": values}, f, indent=2, ensure_ascii=False)
        print(f"[{art.slug}] payload written to {payload_path} (blocks={len(art.blocks)})")

        if args.dry or client is None:
            continue

        existing_id = ARTICLE_SLUG_TO_DOC.get(art.slug)
        if existing_id is None and art.slug == "discriminated-unions-result-pattern-part-1":
            existing_id = _find_doc_by_name(client, ARTICLES_PARENT, "Result pattern")
        if existing_id:
            body = _doc_payload_update(existing_id, art.title, values)
            r = client.put(f"document/{existing_id}", body)
            if r.status_code not in (200, 201, 204):
                raise RuntimeError(f"PUT {existing_id} failed: {r.status_code} {r.text[:600]}")
            print(f"  updated {existing_id}")
            doc_id = existing_id
        else:
            body = _doc_payload_create(art.title, values)
            r = client.post("document", body)
            if r.status_code not in (200, 201):
                raise RuntimeError(f"POST create failed: {r.status_code} {r.text[:600]}")
            doc_id = body["id"]
            print(f"  created {doc_id}")

        if not args.no_publish:
            _publish(client, doc_id)
            print(f"  published {doc_id}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
