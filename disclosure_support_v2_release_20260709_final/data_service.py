from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any


DATA_DIR = Path(__file__).resolve().parent / "data"


def normalize_text(value: str) -> str:
    return re.sub(r"[\s\u3000、。，．・（）()「」『』【】〔〕［］\[\]]+", "", value or "")


@lru_cache(maxsize=1)
def load_records() -> list[dict[str, Any]]:
    reference = json.loads((DATA_DIR / "pdf_reference.json").read_text(encoding="utf-8"))
    mapping = json.loads((DATA_DIR / "item_mapping.json").read_text(encoding="utf-8"))
    mapping_by_source = {
        (item["pdf_category"], str(item["pdf_item_number"])): item
        for item in mapping["records"]
    }

    records: list[dict[str, Any]] = []
    for position, source in enumerate(reference["records"], start=1):
        normalized_key = source["normalized_item_key"]
        mapped = mapping_by_source.get(
            (source["disclosure_category"], str(source["item_number"])),
            {},
        )
        records.append(
            {
                **source,
                "display_order": position,
                "mapping_id": mapped.get("mapping_id", f"UNMAPPED-{position:03d}"),
                "manual_review_flag": bool(mapped.get("manual_review_flag")),
                "manual_review_reason": mapped.get("manual_review_reason") or "",
                "base_items": mapped.get("base_items") or [],
                "base_category": mapped.get("base_category") or "",
                "search_text": normalize_text(
                    " ".join(
                        [
                            source.get("disclosure_category", ""),
                            source.get("disclosure_item", ""),
                            source.get("timely_disclosure_article_and_criteria", ""),
                            source.get("insider_trading_article_and_criteria", ""),
                            source.get("extraordinary_report_requirements", ""),
                        ]
                    )
                ),
            }
        )
    return records


def get_categories(records: list[dict[str, Any]]) -> list[str]:
    return list(dict.fromkeys(item["disclosure_category"] for item in records))


def filter_records(
    records: list[dict[str, Any]],
    category: str = "すべて",
    query: str = "",
    manual_only: bool = False,
) -> list[dict[str, Any]]:
    normalized_query = normalize_text(query)
    return [
        item
        for item in records
        if (category == "すべて" or item["disclosure_category"] == category)
        and (not manual_only or item["manual_review_flag"])
        and (not normalized_query or normalized_query in item["search_text"])
    ]


def regime_text(record: dict[str, Any], regime: str) -> str:
    fields = {
        "timely": "timely_disclosure_article_and_criteria",
        "insider": "insider_trading_article_and_criteria",
        "extraordinary": "extraordinary_report_requirements",
    }
    value = record.get(fields[regime], "")
    return value.strip() if value and value.strip() else "該当記載なし（非該当を意味しません）"


def compact_record(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "No.": record["display_order"],
        "区分": record["disclosure_category"],
        "項目番号": record["item_number"],
        "mapping_id": record["mapping_id"],
        "開示項目": record["disclosure_item"],
        "手動レビュー": "要" if record["manual_review_flag"] else "不要",
        "PDF頁": ", ".join(map(str, record.get("pdf_pages", []))),
    }
