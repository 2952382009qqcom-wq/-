import unittest

from core.citations import (
    audit_citations,
    extract_citation_ids,
    extract_named_legal_citations,
)


class CitationAuditTests(unittest.TestCase):
    def setUp(self):
        self.sources = [
            {
                "citation_id": "L1",
                "law_name": "中华人民共和国民法典",
                "article": "第509条",
                "content": "当事人应当按照约定全面履行自己的义务。",
            },
            {
                "citation_id": "L2",
                "law_name": "中华人民共和国劳动合同法",
                "article": "第三十条",
                "content": "用人单位应当按照劳动合同约定支付劳动报酬。",
            },
        ]

    def test_extract_ids_deduplicates_and_normalises_case(self):
        payload = {
            "answer": "先看 [L2]，再结合 [l1]，结论仍见 [ L2 ]。",
            "local_references": [{"citation_id": "L99", "content": "[L99]"}],
        }

        self.assertEqual(extract_citation_ids(payload), ["L2", "L1"])

    def test_attached_sources_do_not_inflate_coverage(self):
        result = {
            "legal_analysis": "合同履行规则见 [L1]。",
            "local_references": self.sources,
            "references": ["[L2]"],
        }

        audit = audit_citations(result)

        self.assertEqual(audit["source_count"], 2)
        self.assertEqual(audit["cited_ids"], ["L1"])
        self.assertEqual(audit["uncited_ids"], ["L2"])
        self.assertEqual(audit["coverage_percent"], 50.0)
        self.assertEqual(audit["status"], "warning")

    def test_unknown_l99_fails_audit(self):
        audit = audit_citations({"answer": "该结论来自 [L1] 与 [L99]。"}, self.sources)

        self.assertEqual(audit["known_cited_ids"], ["L1"])
        self.assertEqual(audit["unknown_ids"], ["L99"])
        self.assertEqual(audit["status"], "fail")
        self.assertIn("L99", audit["message"])

    def test_obviously_unrelated_claim_fails_lexical_alignment(self):
        audit = audit_citations(
            {"answer": "故意杀人构成犯罪，应当依刑法追究刑事责任 [L1]。"},
            self.sources[:1],
        )

        self.assertEqual(audit["coverage_percent"], 100.0)
        self.assertEqual(audit["status"], "fail")
        self.assertEqual(audit["alignment"]["failed_ids"], ["L1"])
        self.assertEqual(audit["alignment"]["items"][0]["verdict"], "fail")
        self.assertIn("不能证明语义正确", audit["alignment"]["disclaimer"])

    def test_reasonable_labour_pay_paraphrase_passes_alignment(self):
        audit = audit_citations(
            {"answer": "公司必须按劳动合同约定足额发放工资 [L2]。"},
            self.sources[1:],
        )

        self.assertEqual(audit["coverage_percent"], 100.0)
        self.assertEqual(audit["status"], "pass")
        self.assertEqual(audit["alignment"]["failed_ids"], [])
        self.assertEqual(audit["alignment"]["warning_ids"], [])
        self.assertEqual(audit["alignment"]["items"][0]["verdict"], "pass")

    def test_source_identity_label_does_not_require_body_text_overlap(self):
        audit = audit_citations(
            {"applicable_laws": ["[L1] 《中华人民共和国民法典》第509条"]},
            self.sources[:1],
        )

        self.assertEqual(audit["status"], "pass")
        self.assertEqual(audit["alignment"]["items"][0]["verdict"], "pass")

    def test_no_citation_keeps_uncited_warning_and_empty_alignment(self):
        audit = audit_citations({"answer": "这里只给出一般说明。"}, self.sources[:1])

        self.assertEqual(audit["status"], "warning")
        self.assertEqual(audit["uncited_ids"], ["L1"])
        self.assertEqual(audit["alignment"]["items"], [])

    def test_no_local_sources_is_never_reported_as_pass(self):
        audit = audit_citations({"answer": "当事人应当承担违约责任。"}, [])

        self.assertEqual(audit["status"], "insufficient")
        self.assertTrue(audit["has_auditable_text"])
        self.assertIn("没有可审计的本地来源", audit["message"])

    def test_empty_answer_and_no_sources_is_insufficient(self):
        audit = audit_citations({}, [])

        self.assertEqual(audit["status"], "insufficient")
        self.assertFalse(audit["has_auditable_text"])
        self.assertIn("回答正文为空", audit["message"])

    def test_named_law_and_chinese_article_match_allowed_source(self):
        result = {
            "answer": "依据《民法典》第五百零九条，应当全面履行合同 [L1]；"
            "工资支付规则见《中华人民共和国劳动合同法》第三十条 [L2]。"
        }

        audit = audit_citations(result, self.sources)

        self.assertEqual(audit["unsupported_named_citations"], [])
        self.assertEqual(audit["coverage_percent"], 100.0)
        self.assertEqual(audit["status"], "pass")
        self.assertEqual(
            [item["source_ids"] for item in audit["matched_named_citations"]],
            [["L1"], ["L2"]],
        )

    def test_unsupported_named_citation_is_reported(self):
        audit = audit_citations(
            {"answer": "另据《中华人民共和国民法典》第五百一十条处理 [L1]。"},
            self.sources[:1],
        )

        self.assertEqual(
            audit["unsupported_named_citations"],
            ["《中华人民共和国民法典》第五百一十条"],
        )
        self.assertEqual(audit["status"], "fail")

    def test_named_citation_extractor_supports_subarticles(self):
        citations = extract_named_legal_citations("规则见《示例法》第十条之一，亦见重复的《示例法》第十条之一。")

        self.assertEqual(len(citations), 1)
        self.assertEqual(citations[0]["article_number"], 10)
        self.assertEqual(citations[0]["subarticle_number"], 1)
        self.assertEqual(citations[0]["display"], "《示例法》第十条之一")


if __name__ == "__main__":
    unittest.main()
