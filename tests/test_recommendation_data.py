from __future__ import annotations

import json
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INDEX_PATH = PROJECT_ROOT / "skills" / "cook-with-what-you-have" / "references" / "recipe-index.jsonl"


class RecommendationDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.records = [json.loads(line) for line in INDEX_PATH.read_text(encoding="utf-8").splitlines()]

    def test_tofu_anchor_has_three_equipment_safe_candidates(self) -> None:
        candidates = [
            record
            for record in self.records
            if "豆腐" in record["match_terms"]
            and record["recommendation_eligible"]
            and not record["special_equipment"]
        ]
        self.assertGreaterEqual(len({record["title"] for record in candidates}), 3)

    def test_specific_tofu_types_are_preserved(self) -> None:
        mapo_tofu = next(record for record in self.records if record["title"] == "麻婆豆腐")
        self.assertIn("内脂豆腐", mapo_tofu["required_ingredients"])
        self.assertIn("豆腐", mapo_tofu["match_terms"])

    def test_special_equipment_is_tagged_for_filtering(self) -> None:
        air_fryer = [record for record in self.records if "空气炸锅" in record["special_equipment"]]
        microwave = [record for record in self.records if "微波炉" in record["special_equipment"]]
        oven = [record for record in self.records if "烤箱" in record["special_equipment"]]
        self.assertTrue(air_fryer)
        self.assertTrue(microwave)
        self.assertTrue(oven)

    def test_peanut_allergy_can_filter_real_recipes(self) -> None:
        peanut_recipes = [
            record
            for record in self.records
            if any("花生" in ingredient for ingredient in record["required_ingredients"] + record["optional_ingredients"])
        ]
        self.assertTrue(peanut_recipes)
        self.assertIn("宫保鸡丁", {record["title"] for record in peanut_recipes})

    def test_readme_high_match_example_matches_index(self) -> None:
        cold_tofu = next(record for record in self.records if record["title"] == "凉拌豆腐")
        available = {"豆腐", "小葱", "大蒜", "生抽", "香油", "食用油", "盐", "清水"}
        self.assertTrue(set(cold_tofu["required_ingredients"]).issubset(available))


if __name__ == "__main__":
    unittest.main()
