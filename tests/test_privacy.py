import json
import unittest

from core.privacy import (
    RedactionSession,
    is_valid_bank_card,
    is_valid_id_card,
    is_valid_uscc,
    public_redaction_summary,
    redact_nested_json,
    redact_text,
)


class PrivacyRedactionTests(unittest.TestCase):
    def test_repeated_value_uses_stable_placeholder_across_calls(self):
        session = RedactionSession()

        first = redact_text("联系电话：13800138000，再次确认 13800138000", session)
        second = redact_text("国际格式：+86 13800138000", session)

        self.assertEqual(first.count("[手机号_1]"), 2)
        self.assertIn("[手机号_1]", second)
        self.assertNotIn("13800138000", first + second)
        self.assertEqual(session.counts["phone"], 3)
        self.assertEqual(len(session.entities), 1)
        self.assertTrue(session.has_pii)

    def test_checksum_validation_rejects_near_misses(self):
        self.assertTrue(is_valid_id_card("11010519491231002X"))
        self.assertFalse(is_valid_id_card("110105194912310021"))
        self.assertFalse(is_valid_id_card("110105199902300020"))  # impossible date

        self.assertTrue(is_valid_bank_card("4532 0151 1283 0366"))
        self.assertFalse(is_valid_bank_card("4532 0151 1283 0367"))

        self.assertTrue(is_valid_uscc("91350100M000100Y43"))
        self.assertFalse(is_valid_uscc("91350100M000100Y44"))

    def test_supported_pii_categories_are_redacted(self):
        text = (
            "姓名：张三，地址：北京市海淀区中关村大街1号；"
            "邮箱zhang.san@example.com，身份证11010519491231002X，"
            "银行卡4532015112830366，护照E12345678，"
            "备用护照号：K12345678，统一社会信用代码91350100M000100Y43。"
        )

        redacted = redact_text(text)

        for original in (
            "张三",
            "北京市海淀区中关村大街1号",
            "zhang.san@example.com",
            "11010519491231002X",
            "4532015112830366",
            "E12345678",
            "K12345678",
            "91350100M000100Y43",
        ):
            self.assertNotIn(original, redacted)
        for category in ("姓名", "地址", "邮箱", "身份证", "银行卡", "护照", "统一社会信用代码"):
            self.assertIn(f"[{category}_1]", redacted)

    def test_nested_json_is_copied_and_labeled_fields_are_protected(self):
        payload = {
            "姓名": "李雷",
            "profile": {
                "地址": "天津市南开区卫津路94号",
                "contact": "13800138000",
            },
            "phones": ["13800138000", {"backup": "13800138000"}],
            "owner@example.com": {"note": "联系 owner@example.com"},
        }
        session = RedactionSession()

        redacted = redact_nested_json(payload, session)
        rendered = json.dumps(redacted, ensure_ascii=False)

        self.assertEqual(payload["姓名"], "李雷")  # input was not mutated
        for original in ("李雷", "天津市南开区卫津路94号", "13800138000", "owner@example.com"):
            self.assertNotIn(original, rendered)
        self.assertEqual(rendered.count("[手机号_1]"), 3)
        self.assertIn("[姓名_1]", rendered)
        self.assertIn("[地址_1]", rendered)
        self.assertIn("[邮箱_1]", rendered)

    def test_project_english_header_aliases_are_redacted(self):
        payload = {
            "header": {
                "plaintiff": "张三",
                "plaintiff_address": "天津市南开区卫津路94号",
                "defendant": "天津示例科技有限公司",
                "appellant": "李四",
                "appellee": "王五",
                "respondent": "赵六",
                "applicant": "孙七",
                "obligor": "周八",
                "principal": "吴九",
                "agent": "郑十",
                "suer": "冯一",
                "defendant_info": (
                    "钱十一，男，2001年5月6日出生，住北京市朝阳区建国路88号，"
                    "联系电话：010-12345678"
                ),
                "representative_contact": "（022）87654321-123",
                # Explicit structured keys must protect plausible values even
                # when a user mistyped their checksum.
                "id_card": "110105194912310021",
                "passport": "K12345670",
                "bank_card": "4532015112830367",
            }
        }

        redacted = redact_nested_json(payload)
        rendered = json.dumps(redacted, ensure_ascii=False)

        for original in (
            "张三",
            "天津市南开区卫津路94号",
            "李四",
            "王五",
            "赵六",
            "孙七",
            "周八",
            "吴九",
            "郑十",
            "冯一",
            "钱十一",
            "北京市朝阳区建国路88号",
            "010-12345678",
            "（022）87654321-123",
            "110105194912310021",
            "K12345670",
            "4532015112830367",
        ):
            self.assertNotIn(original, rendered)

        # A party role may legitimately contain an organisation; role-key
        # handling must not blindly hide every value.
        self.assertIn("天津示例科技有限公司", rendered)
        for category in ("姓名", "地址", "手机号", "身份证", "护照", "银行卡"):
            self.assertIn(f"[{category}_1]", rendered)

    def test_explicit_labels_mask_near_misses_but_unlabeled_values_stay_strict(self):
        invalid_id = "110105194912310021"
        invalid_bank_card = "4532015112830367"
        labeled = f"身份证号：{invalid_id}；银行卡号：{invalid_bank_card}。"
        unlabeled = f"校验样本 {invalid_id} 与 {invalid_bank_card}。"

        redacted = redact_text(labeled)

        self.assertNotIn(invalid_id, redacted)
        self.assertNotIn(invalid_bank_card, redacted)
        self.assertIn("[身份证_1]", redacted)
        self.assertIn("[银行卡_1]", redacted)
        self.assertEqual(redact_text(unlabeled), unlabeled)

    def test_labeled_landlines_are_redacted(self):
        text = (
            "联系电话：010-12345678；座机：（022）87654321-123。"
            "未标注的编号010-12345678保持不变。"
        )

        redacted = redact_text(text)

        self.assertEqual(redacted.count("[手机号_"), 2)
        self.assertNotIn("（022）87654321-123", redacted)
        self.assertIn("未标注的编号010-12345678保持不变", redacted)

    def test_public_summary_never_contains_original_values(self):
        session = RedactionSession()
        redact_text("13800138000 与 test@example.com，再次 13800138000", session)

        summary = public_redaction_summary(session)
        rendered = json.dumps(summary, ensure_ascii=False)

        self.assertEqual(summary["masked_count"], 3)
        self.assertEqual(summary["unique_masked_count"], 2)
        self.assertEqual(summary["counts"], {"phone": 2, "email": 1})
        self.assertEqual(summary["categories"], ["phone", "email"])
        self.assertNotIn("13800138000", rendered)
        self.assertNotIn("test@example.com", rendered)

    def test_amount_date_and_article_number_are_not_misidentified(self):
        text = (
            "金额：13800138000元；价款4532015112830366.00元；"
            "日期：2026-09-25；日期：E20260925；"
            "《示例法》第13800138000条。"
        )

        self.assertEqual(redact_text(text), text)

        structured = {
            "amount": "4532015112830366",
            "hearing_date": "2026-09-25",
            "article_number": "13800138000",
            "金额": "13800138000",
        }
        self.assertEqual(redact_nested_json(structured), structured)


if __name__ == "__main__":
    unittest.main()
