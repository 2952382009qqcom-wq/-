"""Regression checks for the external-model-only legal answer flow."""

from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class DirectModelPipelineTests(unittest.TestCase):
    def test_local_law_dataset_and_engine_are_removed(self):
        self.assertFalse((ROOT / "data" / "provisions.json").exists())
        self.assertFalse((ROOT / "core" / "legal_kb.py").exists())

    def test_chat_ui_does_not_render_internal_processing_cards(self):
        javascript = (ROOT / "static" / "js" / "main.js").read_text(encoding="utf-8")
        start = javascript.index("function renderAgentResultDetails")
        end = javascript.index("function finishAgentMessage", start)
        renderer = javascript[start:end]

        self.assertNotIn("renderProcessingTrust", renderer)
        self.assertNotIn("renderGroundingTrust", renderer)
        self.assertNotIn("renderGroundedLawCards", renderer)
        self.assertNotIn("citation_audit", renderer)

    def test_home_copy_describes_direct_help_not_local_retrieval(self):
        html = (ROOT / "templates" / "index.html").read_text(encoding="utf-8")
        home_start = html.index('id="module-home"')
        tools_start = html.index('id="module-tools"')
        home = html[home_start:tools_start]

        self.assertNotIn("本地法律检索", home)
        self.assertNotIn("引用审计后展示", home)
        self.assertIn("先直接告诉你可以怎么处理", home)


if __name__ == "__main__":
    unittest.main()
