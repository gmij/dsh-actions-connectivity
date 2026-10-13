import json
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).parent))
from staged_design import stage_prompt

class StagedContextRegression(unittest.TestCase):
    def test_long_generated_channels_does_not_block_prototype(self):
        completed = {
            "schema_version": 2, "level": "overview",
            "modules": [{"id": "MOD-01", "name": "ACP Runtime"}],
            "task_records": [{"id": "TASK-01", "module_id": "MOD-01"}],
            "channels": [{"id": "IPC-01", "module_id": "MOD-01",
                          "transport": "acp", "command": "session/prompt",
                          "request": {"description": "x"*112000}}],
        }
        prompt = stage_prompt("Original Issue #11", "prototype", ("prototype_html",), completed, "overview")
        self.assertLess(len(prompt), 85000)
        self.assertIn("IPC-01", prompt)
        self.assertIn("TASK-01", prompt)
        self.assertIn("MOD-01", prompt)
        self.assertEqual(len(completed["channels"][0]["request"]["description"]), 112000)

    def test_short_references_remain_unchanged(self):
        completed = {"modules": [{"id": "MOD-01"}], "channels": [{"id": "IPC-01"}]}
        prompt = stage_prompt("Original", "prototype", ("prototype_html",), completed, "overview")
        self.assertIn(json.dumps(completed,ensure_ascii=False),prompt)

if __name__=="__main__":
    unittest.main()
