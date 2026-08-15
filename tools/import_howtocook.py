#!/usr/bin/env python3
"""Build the offline HowToCook snapshot used by the distributable skill.

This is a maintainer tool. Skill users do not run it and need no Python runtime.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import tempfile
import urllib.request
import zipfile
from datetime import date
from pathlib import Path
from urllib.parse import quote


UPSTREAM_REPOSITORY = "https://github.com/Anduin2017/HowToCook"
DEFAULT_REFERENCE_ROOT = Path("skills/cook-with-what-you-have/references")

CATEGORY_NAMES = {
    "aquatic": "水产",
    "breakfast": "早餐",
    "condiment": "酱料和其他材料",
    "dessert": "甜品",
    "drink": "饮料",
    "meat_dish": "荤菜",
    "semi-finished": "半成品",
    "soup": "汤与粥",
    "staple": "主食",
    "vegetable_dish": "素菜",
}

EQUIPMENT_TERMS = {
    "水果刀",
    "菜刀",
    "砧板",
    "烤箱",
    "空气炸锅",
    "微波炉",
    "电饭煲",
    "电压力锅",
    "高压锅",
    "压力锅",
    "蒸箱",
    "破壁机",
    "搅拌机",
    "料理机",
    "榨汁机",
    "厨师机",
    "打蛋器",
    "电饼铛",
    "平底锅",
    "不粘锅",
    "炒锅",
    "砂锅",
    "蒸锅",
    "汤锅",
    "锅铲",
    "铁勺",
    "勺子",
    "汤勺",
    "炒勺",
    "漏勺",
    "滤网",
    "密封袋",
    "蘸料碟",
    "烤盘",
    "烤架",
    "锡纸",
    "保鲜膜",
    "碗",
    "盘",
    "筷子",
}

SPECIAL_EQUIPMENT_ALIASES = {
    "烤箱": "烤箱",
    "空气炸锅": "空气炸锅",
    "微波炉": "微波炉",
    "电饭煲": "电饭煲",
    "电压力锅": "压力锅",
    "高压锅": "压力锅",
    "压力锅": "压力锅",
    "蒸箱": "蒸箱",
    "破壁机": "料理机",
    "搅拌机": "料理机",
    "料理机": "料理机",
    "榨汁机": "料理机",
    "厨师机": "料理机",
}

OPTIONAL_MARKERS = ("可选", "备选", "可以不加", "可不加", "非必需")

EXACT_ALIASES = {
    "油": "食用油",
    "植物油": "食用油",
    "食盐": "盐",
    "开水": "清水",
    "凉水": "清水",
    "冷水": "清水",
    "饮用水": "清水",
    "水": "清水",
    "番茄": "西红柿",
    "马铃薯": "土豆",
}


def strip_comments(text: str) -> str:
    return re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)


def strip_markdown(value: str) -> str:
    value = re.sub(r"!\[[^]]*]\([^)]*\)", "", value)
    value = re.sub(r"\[([^]]+)]\([^)]*\)", r"\1", value)
    value = value.replace("**", "").replace("__", "").replace("`", "")
    return re.sub(r"\s+", " ", value).strip()


def extract_section(text: str, heading: str) -> str:
    pattern = rf"^##\s+{re.escape(heading)}\s*$\n(.*?)(?=^##\s+|\Z)"
    match = re.search(pattern, text, flags=re.MULTILINE | re.DOTALL)
    return match.group(1) if match else ""


def extract_title(text: str, fallback: str) -> str:
    match = re.search(r"^#\s+(.+?)\s*$", text, flags=re.MULTILINE)
    title = strip_markdown(match.group(1)) if match else fallback
    return title.removesuffix("的做法").strip()


def extract_description(text: str) -> str:
    title_match = re.search(r"^#\s+.+?$", text, flags=re.MULTILINE)
    if not title_match:
        return ""
    remainder = text[title_match.end() :]
    for paragraph in re.split(r"\n\s*\n", remainder):
        candidate = strip_markdown(paragraph)
        if not candidate or candidate.startswith("预估") or candidate.startswith("#"):
            continue
        if candidate.startswith("!["):
            continue
        return candidate
    return ""


def extract_difficulty(text: str) -> int | None:
    match = re.search(r"预估烹饪难度[：:]\s*([★☆]+)", text)
    return match.group(1).count("★") if match else None


def extract_calories(text: str) -> int | None:
    match = re.search(r"预估卡路里[：:]\s*(\d+)\s*大卡", text)
    return int(match.group(1)) if match else None


def extract_duration_minutes(description: str) -> int | None:
    matches = re.findall(r"(\d+(?:\.\d+)?)\s*(分钟|小时)", description)
    if not matches:
        return None
    value, unit = matches[-1]
    minutes = float(value) * (60 if unit == "小时" else 1)
    return round(minutes)


def is_optional(raw_item: str) -> bool:
    return any(marker in raw_item for marker in OPTIONAL_MARKERS)


def without_parenthetical(value: str) -> str:
    value = re.sub(r"（[^）]*）", "", value)
    value = re.sub(r"\([^)]*\)", "", value)
    return re.sub(r"\s+", " ", value).strip(" ;；，,。")


def looks_like_equipment(item: str) -> bool:
    base = without_parenthetical(item)
    alternatives = re.split(r"[/／、]|(?:或)", base)
    for alternative in alternatives:
        candidate = alternative.strip()
        for term in EQUIPMENT_TERMS:
            if candidate == term or candidate.startswith(term) or candidate.endswith(term):
                return True
    return False


def normalize_food_term(value: str) -> str:
    value = without_parenthetical(value)
    value = re.sub(r"(?:\.\.\.|…)+.*$", "", value)
    value = re.sub(r"^(?:适量|少量|少许)", "", value).strip()
    return EXACT_ALIASES.get(value, value)


def food_terms(item: str) -> list[str]:
    base = without_parenthetical(item)
    parts = re.split(r"[/／、]|(?:或)", base)
    terms: list[str] = []
    for part in parts:
        normalized = normalize_food_term(part)
        if normalized and normalized not in terms:
            terms.append(normalized)
    return terms or ([normalize_food_term(base)] if base else [])


def add_semantic_match_terms(terms: list[str]) -> list[str]:
    expanded: list[str] = []

    def add(value: str) -> None:
        value = value.strip()
        if value and value not in expanded:
            expanded.append(value)

    for term in terms:
        add(term)
        if "豆腐" in term and "日本豆腐" not in term:
            add("豆腐")
        if "西红柿" in term or "番茄" in term:
            add("西红柿")
            add("番茄")
        if "土豆" in term or "马铃薯" in term:
            add("土豆")
            add("马铃薯")
        if any(token in term for token in ("香葱", "小葱", "大葱", "葱花")):
            add("葱")
        if "生姜" in term:
            add("姜")
        if any(token in term for token in ("大蒜", "蒜瓣", "蒜蓉")):
            add("蒜")
        if any(token in term for token in ("肉末", "肉糜", "五花肉", "猪肉")):
            add("猪肉")
        if "牛肉" in term or "牛腩" in term:
            add("牛肉")
        if "鸡腿" in term or "鸡翅" in term or term == "鸡肉":
            add("鸡肉")
    return expanded


def parse_ingredient_items(text: str) -> tuple[list[str], list[str], list[str], list[str]]:
    section = extract_section(text, "必备原料和工具")
    bullet_items = []
    for line in section.splitlines():
        match = re.match(r"^\s*[-*+]\s+(.+?)\s*$", line)
        if match:
            item = strip_markdown(match.group(1))
            if item:
                bullet_items.append(item)

    required: list[str] = []
    optional: list[str] = []
    equipment: list[str] = []
    special_equipment: list[str] = []

    for item in bullet_items:
        if looks_like_equipment(item):
            equipment.append(without_parenthetical(item))
            for source, canonical in SPECIAL_EQUIPMENT_ALIASES.items():
                if source in item and canonical not in special_equipment:
                    special_equipment.append(canonical)
            continue
        target = optional if is_optional(item) else required
        for term in food_terms(item):
            if term and term not in target:
                target.append(term)

    return required, optional, equipment, special_equipment


def parse_recipe(markdown_path: Path, dishes_root: Path, commit: str) -> dict[str, object]:
    original_text = markdown_path.read_text(encoding="utf-8")
    text = strip_comments(original_text)
    relative_to_dishes = markdown_path.relative_to(dishes_root)
    category_key = relative_to_dishes.parts[0]
    source_relative = Path("howtocook/dishes") / relative_to_dishes
    title = extract_title(text, markdown_path.stem)
    description = extract_description(text)
    required, optional, equipment, special_equipment = parse_ingredient_items(text)
    match_terms = add_semantic_match_terms(required + optional)
    recipe_id = hashlib.sha256(relative_to_dishes.as_posix().encode("utf-8")).hexdigest()[:12]
    source_url_path = quote(f"dishes/{relative_to_dishes.as_posix()}")

    eligible = bool(required) and bool(extract_section(text, "操作")) and category_key != "template"
    validation_notes: list[str] = []
    if not required:
        validation_notes.append("未识别到必需食材")
    if not extract_section(text, "操作"):
        validation_notes.append("未识别到操作步骤")

    return {
        "id": recipe_id,
        "title": title,
        "category": CATEGORY_NAMES.get(category_key, category_key),
        "category_key": category_key,
        "description": description,
        "difficulty": extract_difficulty(text),
        "duration_minutes": extract_duration_minutes(description),
        "calories_kcal": extract_calories(text),
        "required_ingredients": required,
        "optional_ingredients": optional,
        "match_terms": match_terms,
        "equipment": equipment,
        "special_equipment": special_equipment,
        "recommendation_eligible": eligible,
        "validation_notes": validation_notes,
        "source_path": source_relative.as_posix(),
        "source_url": f"{UPSTREAM_REPOSITORY}/blob/{commit}/{source_url_path}",
    }


def download_snapshot(commit: str, destination: Path) -> Path:
    archive_url = f"https://codeload.github.com/Anduin2017/HowToCook/zip/{commit}"
    archive_path = destination / "howtocook.zip"
    request = urllib.request.Request(archive_url, headers={"User-Agent": "cook-with-what-you-have-importer"})
    with urllib.request.urlopen(request) as response, archive_path.open("wb") as output:
        shutil.copyfileobj(response, output)
    with zipfile.ZipFile(archive_path) as archive:
        archive.extractall(destination)
    candidates = [path for path in destination.iterdir() if path.is_dir() and (path / "dishes").is_dir()]
    if len(candidates) != 1:
        raise RuntimeError("Downloaded archive did not contain exactly one HowToCook source root")
    return candidates[0]


def copy_markdown_snapshot(source_root: Path, target_root: Path) -> list[Path]:
    dishes_source = source_root / "dishes"
    dishes_target = target_root / "dishes"
    if target_root.exists():
        shutil.rmtree(target_root)
    dishes_target.mkdir(parents=True)

    copied: list[Path] = []
    for source_file in sorted(dishes_source.rglob("*.md")):
        relative = source_file.relative_to(dishes_source)
        if relative.parts[0] == "template":
            continue
        target_file = dishes_target / relative
        target_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_file, target_file)
        copied.append(target_file)

    license_source = source_root / "LICENSE"
    if license_source.exists():
        shutil.copy2(license_source, target_root / "LICENSE")
    return copied


def combined_content_hash(files: list[Path], root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(files):
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_snapshot(source_root: Path, reference_root: Path, commit: str, snapshot_date: str) -> dict[str, object]:
    snapshot_root = reference_root / "howtocook"
    copied_files = copy_markdown_snapshot(source_root, snapshot_root)
    dishes_root = snapshot_root / "dishes"
    records = [parse_recipe(path, dishes_root, commit) for path in sorted(copied_files)]
    records.sort(key=lambda record: (str(record["category_key"]), str(record["title"]), str(record["source_path"])))

    index_path = reference_root / "recipe-index.jsonl"
    index_path.parent.mkdir(parents=True, exist_ok=True)
    with index_path.open("w", encoding="utf-8", newline="\n") as output:
        for record in records:
            output.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")

    categories: dict[str, int] = {}
    for record in records:
        category = str(record["category"])
        categories[category] = categories.get(category, 0) + 1

    catalog = {
        "schema_version": 1,
        "source_repository": UPSTREAM_REPOSITORY,
        "source_commit": commit,
        "snapshot_date": snapshot_date,
        "recipe_count": len(records),
        "recommendation_eligible_count": sum(bool(record["recommendation_eligible"]) for record in records),
        "categories": dict(sorted(categories.items())),
        "markdown_bytes": sum(path.stat().st_size for path in copied_files),
        "snapshot_sha256": combined_content_hash(copied_files, snapshot_root),
        "index_sha256": hashlib.sha256(index_path.read_bytes()).hexdigest(),
        "images_included": False,
    }
    write_json(reference_root / "recipe-catalog.json", catalog)
    return catalog


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--commit", required=True, help="Exact HowToCook commit SHA")
    parser.add_argument("--output", type=Path, default=DEFAULT_REFERENCE_ROOT, help="Skill references directory")
    parser.add_argument("--source-dir", type=Path, help="Use an existing HowToCook checkout instead of downloading")
    parser.add_argument("--snapshot-date", default=date.today().isoformat(), help="Date recorded in the catalog")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not re.fullmatch(r"[0-9a-fA-F]{40}", args.commit):
        raise SystemExit("--commit must be a full 40-character Git SHA")

    if args.source_dir:
        source_root = args.source_dir.resolve()
        if not (source_root / "dishes").is_dir():
            raise SystemExit(f"HowToCook dishes directory not found under {source_root}")
        catalog = build_snapshot(source_root, args.output.resolve(), args.commit.lower(), args.snapshot_date)
    else:
        with tempfile.TemporaryDirectory(prefix="howtocook-import-") as temporary:
            source_root = download_snapshot(args.commit.lower(), Path(temporary))
            catalog = build_snapshot(source_root, args.output.resolve(), args.commit.lower(), args.snapshot_date)

    print(json.dumps(catalog, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
