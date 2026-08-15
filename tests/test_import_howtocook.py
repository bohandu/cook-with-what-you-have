from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
IMPORTER_PATH = PROJECT_ROOT / "tools" / "import_howtocook.py"
SPEC = importlib.util.spec_from_file_location("import_howtocook", IMPORTER_PATH)
assert SPEC and SPEC.loader
IMPORTER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(IMPORTER)


SAMPLE_RECIPE = """# 西红柿炒鸡蛋的做法

一道简单家常菜，全程约需 15 分钟。

预估烹饪难度：★★

预估卡路里：252 大卡

## 必备原料和工具

- 西红柿
- 鸡蛋
- 食用油
- 盐
- 糖（可选）
- 葱花（可选）
- 平底锅

## 计算

每人一份。

## 操作

1. 炒熟。
"""


class ParserTests(unittest.TestCase):
    def test_parse_recipe_separates_optional_food_and_equipment(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            dishes_root = Path(temporary) / "dishes"
            recipe_path = dishes_root / "vegetable_dish" / "西红柿炒鸡蛋.md"
            recipe_path.parent.mkdir(parents=True)
            recipe_path.write_text(SAMPLE_RECIPE, encoding="utf-8")

            record = IMPORTER.parse_recipe(recipe_path, dishes_root, "a" * 40)

        self.assertEqual(record["title"], "西红柿炒鸡蛋")
        self.assertEqual(record["difficulty"], 2)
        self.assertEqual(record["duration_minutes"], 15)
        self.assertEqual(record["calories_kcal"], 252)
        self.assertEqual(record["required_ingredients"], ["西红柿", "鸡蛋", "食用油", "盐"])
        self.assertEqual(record["optional_ingredients"], ["糖", "葱花"])
        self.assertEqual(record["equipment"], ["平底锅"])
        self.assertIn("番茄", record["match_terms"])
        self.assertTrue(record["recommendation_eligible"])

    def test_aliases_keep_japanese_tofu_distinct(self) -> None:
        self.assertEqual(IMPORTER.normalize_food_term("内脂豆腐"), "内脂豆腐")
        self.assertIn("豆腐", IMPORTER.add_semantic_match_terms(["内脂豆腐"]))
        self.assertEqual(IMPORTER.normalize_food_term("日本豆腐"), "日本豆腐")
        self.assertNotIn("豆腐", IMPORTER.add_semantic_match_terms(["日本豆腐"]))


class GeneratedSnapshotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.reference_root = PROJECT_ROOT / "skills" / "cook-with-what-you-have" / "references"
        cls.catalog_path = cls.reference_root / "recipe-catalog.json"
        cls.index_path = cls.reference_root / "recipe-index.jsonl"

    def test_generated_snapshot_is_consistent(self) -> None:
        if not self.catalog_path.exists() or not self.index_path.exists():
            self.skipTest("Generated snapshot has not been imported yet")
        catalog = json.loads(self.catalog_path.read_text(encoding="utf-8"))
        records = [json.loads(line) for line in self.index_path.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(catalog["recipe_count"], len(records))
        self.assertGreater(len(records), 300)
        self.assertTrue(all(record["category_key"] != "template" for record in records))
        self.assertTrue(all((self.reference_root / record["source_path"]).is_file() for record in records))

    def test_known_recipe_has_expected_index_data(self) -> None:
        if not self.index_path.exists():
            self.skipTest("Generated snapshot has not been imported yet")
        records = [json.loads(line) for line in self.index_path.read_text(encoding="utf-8").splitlines()]
        tomato_eggs = next(record for record in records if record["title"] == "西红柿炒鸡蛋")
        self.assertIn("西红柿", tomato_eggs["required_ingredients"])
        self.assertIn("鸡蛋", tomato_eggs["required_ingredients"])
        self.assertIn("糖", tomato_eggs["optional_ingredients"])
        self.assertEqual(tomato_eggs["difficulty"], 2)
        self.assertTrue(tomato_eggs["recommendation_eligible"])


if __name__ == "__main__":
    unittest.main()
