from __future__ import annotations

import hashlib
import json
import re
import shutil
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = PROJECT_ROOT / "skills" / "cook-with-what-you-have"
REFERENCE_ROOT = SKILL_ROOT / "references"


class SkillContractTests(unittest.TestCase):
    def test_skill_has_valid_minimal_frontmatter(self) -> None:
        text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertTrue(text.startswith("---\n"))
        frontmatter = text.split("---", 2)[1].strip().splitlines()
        keys = [line.split(":", 1)[0].strip() for line in frontmatter if ":" in line]
        self.assertEqual(keys, ["name", "description"])
        self.assertIn("name: cook-with-what-you-have", frontmatter)
        name = next(line.split(":", 1)[1].strip() for line in frontmatter if line.startswith("name:"))
        description = next(
            line.split(":", 1)[1].strip().strip('"')
            for line in frontmatter
            if line.startswith("description:")
        )
        self.assertRegex(name, r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
        self.assertLessEqual(len(name), 64)
        self.assertLessEqual(len(description), 1024)
        self.assertIsNone(re.search(r"[<>]", description))
        self.assertLess(len(text.splitlines()), 500)

    def test_skill_is_runtime_dependency_free(self) -> None:
        self.assertFalse((SKILL_ROOT / "scripts").exists())
        openai_yaml = (SKILL_ROOT / "agents" / "openai.yaml").read_text(encoding="utf-8")
        self.assertNotIn("dependencies:", openai_yaml)
        self.assertIn("$cook-with-what-you-have", openai_yaml)

    def test_required_references_exist(self) -> None:
        expected = {
            "profile-rules.md",
            "recommendation-rules.md",
            "profile-template.json",
            "history-template.json",
            "recipe-index.jsonl",
            "recipe-catalog.json",
        }
        self.assertTrue(expected.issubset({path.name for path in REFERENCE_ROOT.iterdir()}))

    def test_profile_defaults_match_product_contract(self) -> None:
        profile = json.loads((REFERENCE_ROOT / "profile-template.json").read_text(encoding="utf-8"))
        self.assertEqual(profile["default_diners"], 1)
        self.assertEqual(profile["pantry"], ["食用油", "盐", "清水"])
        self.assertEqual(profile["equipment"]["available"], ["灶台", "锅", "刀", "砧板"])
        self.assertFalse(profile["equipment"]["special_equipment_confirmed"])
        self.assertFalse(profile["dietary_constraints_confirmed"])
        self.assertEqual(profile["allergens"], [])
        self.assertEqual(profile["avoid"], [])

    def test_catalog_hash_matches_index(self) -> None:
        catalog = json.loads((REFERENCE_ROOT / "recipe-catalog.json").read_text(encoding="utf-8"))
        index_bytes = (REFERENCE_ROOT / "recipe-index.jsonl").read_bytes()
        self.assertEqual(hashlib.sha256(index_bytes).hexdigest(), catalog["index_sha256"])
        self.assertEqual(catalog["recipe_count"], 368)
        self.assertEqual(catalog["recommendation_eligible_count"], 368)
        self.assertLess(catalog["markdown_bytes"], 5 * 1024 * 1024)

        snapshot_root = REFERENCE_ROOT / "howtocook"
        markdown_files = sorted((snapshot_root / "dishes").rglob("*.md"))
        digest = hashlib.sha256()
        for path in markdown_files:
            digest.update(path.relative_to(snapshot_root).as_posix().encode("utf-8"))
            digest.update(b"\0")
            digest.update(path.read_bytes())
            digest.update(b"\0")
        self.assertEqual(digest.hexdigest(), catalog["snapshot_sha256"])
        self.assertTrue((snapshot_root / "LICENSE").is_file())
        self.assertFalse(any(path.suffix.lower() in {".jpg", ".jpeg", ".png", ".gif"} for path in snapshot_root.rglob("*")))

    def test_each_index_record_points_to_original_markdown(self) -> None:
        records = [
            json.loads(line)
            for line in (REFERENCE_ROOT / "recipe-index.jsonl").read_text(encoding="utf-8").splitlines()
        ]
        for record in records:
            source = REFERENCE_ROOT / record["source_path"]
            self.assertTrue(source.is_file(), record["source_path"])
            original = source.read_text(encoding="utf-8")
            self.assertIn("## 必备原料和工具", original)
            self.assertIn("## 操作", original)

    def test_copied_skill_is_self_contained(self) -> None:
        """Exercise the documented install flow in a clean, unrelated directory."""
        with tempfile.TemporaryDirectory() as temporary_home:
            installed = Path(temporary_home) / ".agents" / "skills" / SKILL_ROOT.name
            shutil.copytree(SKILL_ROOT, installed)

            skill_text = (installed / "SKILL.md").read_text(encoding="utf-8")
            for relative_reference in {
                "references/profile-rules.md",
                "references/recommendation-rules.md",
                "references/recipe-index.jsonl",
            }:
                self.assertIn(relative_reference, skill_text)
                self.assertTrue((installed / relative_reference).is_file())

            installed_references = installed / "references"
            records = [
                json.loads(line)
                for line in (installed_references / "recipe-index.jsonl")
                .read_text(encoding="utf-8")
                .splitlines()
            ]
            self.assertEqual(len(records), 368)
            for record in records:
                self.assertTrue(
                    (installed_references / record["source_path"]).is_file(),
                    record["source_path"],
                )

    def test_eval_suite_covers_core_flows(self) -> None:
        suite = json.loads((PROJECT_ROOT / "evals" / "cases.json").read_text(encoding="utf-8"))
        ids = {case["id"] for case in suite["cases"]}
        self.assertTrue(
            {
                "first-use-onboarding",
                "three-ranked-candidates",
                "hard-allergy-filter",
                "persistent-profile-update",
                "faithful-source-recipe",
                "meal-combination",
            }.issubset(ids)
        )


if __name__ == "__main__":
    unittest.main()
