from __future__ import annotations

import json
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def load_json(relative_path: str) -> dict:
    with (PROJECT_ROOT / relative_path).open("r", encoding="utf-8") as stream:
        return json.load(stream)


class SchemaTests(unittest.TestCase):
    def test_run_fixture_contains_all_top_level_required_fields(self) -> None:
        schema = load_json("schemas/run_result.schema.json")
        fixture = load_json("tests/fixtures/run_result_valid.json")
        self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
        self.assertTrue(set(schema["required"]).issubset(fixture))
        self.assertEqual(fixture["schema_version"], schema["properties"]["schema_version"]["const"])
        self.assertIn(fixture["status"], schema["properties"]["status"]["enum"])

    def test_knowledge_fixture_contains_all_top_level_required_fields(self) -> None:
        schema = load_json("schemas/knowledge_record.schema.json")
        fixture = load_json("tests/fixtures/knowledge_record_valid.json")
        self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
        self.assertTrue(set(schema["required"]).issubset(fixture))
        self.assertEqual(fixture["schema_version"], schema["properties"]["schema_version"]["const"])
        self.assertIn(fixture["status"], schema["properties"]["status"]["enum"])

    def test_human_interpretation_is_optional_evidence_not_a_gate(self) -> None:
        run_schema = load_json("schemas/run_result.schema.json")
        knowledge_schema = load_json("schemas/knowledge_record.schema.json")
        self.assertNotIn("human_interpretation", run_schema["properties"])
        self.assertIn("null", knowledge_schema["properties"]["human_interpretation"]["type"])


if __name__ == "__main__":
    unittest.main()

