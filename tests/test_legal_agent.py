"""Tests for the unified MingJian legal-agent surface."""

from __future__ import annotations

import io
import json
import os
import unittest
from unittest import mock

from flask_login import UserMixin


with mock.patch.dict(
    os.environ,
    {
        "DATABASE_URL": "sqlite:///:memory:",
        "SECRET_KEY": "legal-agent-test-secret",
        "LLM_API_KEY": "sk-placeholder-test",
    },
):
    import app as app_module

from core.doc_parser import ParsedDocument
from core.legal_agent import (
    INTENT_DRAFT,
    INTENT_EVIDENCE,
    INTENT_GENERAL,
    INTENT_REVIEW,
    INTENT_RISK,
    INTENT_STRATEGY,
    build_general_prompt,
    compose_chat_answer,
    detect_intent,
)
from core.legal_guidance import legal_anchors_for_question, requires_legal_basis
from core.models import Conversation, ConversationMessage


class _ApprovedUser(UserMixin):
    id = 9102
    username = "legal-agent-test-user"
    is_admin = False
    is_approved = True
    llm_api_key = None
    llm_base_url = None
    llm_model = None
    free_api_used = 0


class LegalAgentRoutingTests(unittest.TestCase):
    def test_routes_general_legal_capabilities(self):
        self.assertEqual(detect_intent("请给我一份证据清单"), INTENT_EVIDENCE)
        self.assertEqual(detect_intent("请分析一下最坏结果和风险点"), INTENT_RISK)
        self.assertEqual(detect_intent("这个案件怎么打官司，有什么诉讼策略"), INTENT_STRATEGY)
        self.assertEqual(detect_intent("我要起草起诉状"), INTENT_DRAFT)

    def test_uploaded_contract_is_automatically_routed_to_review(self):
        contract = (
            "甲方委托乙方提供服务。本合同约定服务费用和履行期限，"
            "乙方逾期应承担违约责任，争议由甲方所在地法院处理。"
        )
        self.assertEqual(
            detect_intent("请看附件", attachment_text=contract, filename="服务协议.docx"),
            INTENT_REVIEW,
        )

    def test_general_prompt_uses_direct_api_answer_without_local_retrieval(self):
        prompt = build_general_prompt(
            "我在校外租房被骗了怎么办？",
            "用户：我通过聊天软件联系了转租人并转账。",
        )

        self.assertIn("先回答“怎么办”", prompt)
        self.assertIn("不要输出 [L1]", prompt)
        self.assertNotIn("本地法律证据（JSON", prompt)
        self.assertNotIn("BM25", prompt)

    def test_legal_characterisation_questions_receive_verified_articles(self):
        self.assertFalse(requires_legal_basis("我被打了怎么办"))
        self.assertTrue(requires_legal_basis("我能打回去吗"))
        self.assertTrue(requires_legal_basis("抢劫可以定啥罪"))
        defense = legal_anchors_for_question("我能打回去吗")
        robbery = legal_anchors_for_question("抢劫可以定啥罪")
        self.assertEqual(defense[0]["article"], "第二十条")
        self.assertEqual(robbery[0]["article"], "第二百六十三条")

        prompt = build_general_prompt(
            "我能打回去吗",
            "用户刚才说自己被打。",
            verified_legal_anchors=defense,
            legal_basis_required=True,
        )
        self.assertIn("legal_basis 必须列出", prompt)
        self.assertIn("第二十条", prompt)

        answer = compose_chat_answer(
            INTENT_GENERAL,
            {"answer": "正在受到攻击时可以采取必要制止行为，但不能事后报复。"},
            legal_basis_fallback=defense,
            required_legal_basis=True,
        )
        self.assertIn("法律依据", answer)
        self.assertIn("第二十条", answer)


class LegalAgentEndpointTests(unittest.TestCase):
    def setUp(self):
        app_module.app.config.update(TESTING=True)
        self.user = _ApprovedUser()
        self.loader_patch = mock.patch.object(
            app_module.login_manager,
            "_user_callback",
            side_effect=lambda _user_id: self.user,
        )
        self.loader_patch.start()
        self.client = app_module.app.test_client()
        with app_module.app.app_context():
            ConversationMessage.query.delete()
            Conversation.query.filter_by(user_id=self.user.id).delete()
            app_module.db.session.commit()
        with self.client.session_transaction() as session:
            session["_user_id"] = str(self.user.id)
            session["_fresh"] = True

    def tearDown(self):
        with app_module.app.app_context():
            app_module.db.session.rollback()
            ConversationMessage.query.delete()
            Conversation.query.filter_by(user_id=self.user.id).delete()
            app_module.db.session.commit()
        self.loader_patch.stop()

    def test_general_question_returns_direct_model_answer_without_internal_metadata(self):
        model_result = {
            "answer": "先保存合同、转账记录、聊天记录和房源页面，再立即联系平台止付并报警；如果属于一般合同纠纷，可同步要求对方退款并准备民事追偿。",
            "summary": "租房被骗处理建议",
            "evidence_checklist": ["租赁合同", "转账记录", "聊天记录", "房源页面"],
            "risk_points": [],
            "next_steps": ["联系支付平台申请止付", "携带证据报警"],
            "questions_to_clarify": ["对方是否为房东或有转租授权？"],
        }
        with mock.patch.object(app_module, "_is_current_demo_mode", return_value=False), mock.patch.object(
            app_module, "_call_llm", return_value=model_result), mock.patch.object(
            app_module, "save_record"
        ):
            response = self.client.post(
                "/api/legal-agent",
                json={"message": "我在校外租房被骗了怎么办？"},
            )

        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(body["status"], "completed")
        self.assertIn("保存合同", body["answer"])
        self.assertNotIn("local_references", body)
        self.assertNotIn("citation_audit", body)
        self.assertNotIn("pipeline_trace", body)
        self.assertNotIn("本地法律", json.dumps(body, ensure_ascii=False))
        self.assertTrue(body["conversation_id"])

    def test_general_answer_strips_stale_local_citation_labels(self):
        answer = compose_chat_answer(
            INTENT_GENERAL,
            {"answer": "先保存转账记录。[L1] 再联系平台投诉。[L23]"},
        )

        self.assertEqual(answer, "先保存转账记录。 再联系平台投诉。")

    def test_general_answer_does_not_repeat_clarifying_questions(self):
        answer = compose_chat_answer(
            INTENT_GENERAL,
            {
                "answer": "需要进一步核实被骗金额和对方身份。",
                "questions_to_clarify": ["被骗金额是多少？", "对方是谁？"],
            },
        )

        self.assertEqual(answer, "需要进一步核实被骗金额和对方身份。")

    def test_insufficient_information_is_stated_without_fabricated_law(self):
        uncertain = {
            "answer": "现有信息不足以判断属于诈骗还是一般租赁合同纠纷，需要先核实对方身份、房屋权属和转账去向。",
            "questions_to_clarify": ["争议发生时间是什么时候"],
        }
        with mock.patch.object(app_module, "_is_current_demo_mode", return_value=False), mock.patch.object(
            app_module, "_call_llm", return_value=uncertain), mock.patch.object(
            app_module, "save_record"
        ):
            response = self.client.post(
                "/api/legal-agent",
                json={"message": "这种少见的争议能直接获得十倍赔偿吗？"},
            )

        body = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertIn("信息不足", body["answer"])
        self.assertNotIn("并不存在的法", body["answer"])

    def test_contract_upload_is_previewed_and_auto_reviewed(self):
        contract = (
            "服务合同。甲方张三委托乙方公司提供服务，联系电话13800138000。"
            "本合同约定服务费用一万元，乙方应在三十日内履行。"
            "任何违约均不承担违约责任，争议由甲方所在地法院处理。"
        )
        parsed = ParsedDocument(
            text=contract,
            method="docx_text",
            page_count=2,
            ocr_confidence=None,
            warnings=(),
        )
        with mock.patch.object(
            app_module, "parse_upload_detailed", return_value=("服务合同.docx", parsed)
        ), mock.patch.object(app_module, "_is_current_demo_mode", return_value=True), mock.patch.object(
            app_module, "save_record"
        ):
            response = self.client.post(
                "/api/legal-agent",
                data={
                    "message": "请分析附件",
                    "file": (io.BytesIO(b"fake-docx"), "服务合同.docx"),
                },
                content_type="multipart/form-data",
            )

        body = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["intent"], INTENT_REVIEW)
        self.assertEqual(body["attachment"]["filename"], "服务合同.docx")
        self.assertEqual(body["attachment"]["method"], "docx_text")
        self.assertNotIn("13800138000", body["attachment"]["preview"])
        self.assertIn("[手机号_1]", body["attachment"]["preview"])

    def test_multi_turn_complaint_generation_collects_then_exports(self):
        with mock.patch.object(app_module, "save_record"):
            first = self.client.post(
                "/api/legal-agent",
                json={"message": "我要起草起诉状"},
            )
            first_body = first.get_json()
            second = self.client.post(
                "/api/legal-agent",
                json={
                    "conversation_id": first_body["conversation_id"],
                    "message": (
                        "原告：张三；被告：某科技公司；"
                        "诉讼请求：支付拖欠工资三万元；"
                        "事实和理由：自2026年1月起连续拖欠工资；"
                        "法院：北京市朝阳区人民法院"
                    ),
                    "client_messages": [
                        {"role": "user", "content": "我要起草起诉状"},
                    ],
                },
            )

        self.assertEqual(first.status_code, 200)
        self.assertEqual(first_body["status"], "needs_information")
        self.assertEqual(second.status_code, 200)
        second_body = second.get_json()
        self.assertEqual(second_body["status"], "completed")
        self.assertTrue(second_body["can_export"])
        self.assertEqual(second_body["document"]["document_type"], "起诉状")
        self.assertIn("支付拖欠工资三万元", second_body["document"]["body"])
        self.assertNotIn("【说明】", second_body["document"]["body"])

    def test_stream_emits_progress_chunks_and_final_envelope(self):
        model_result = {
            "answer": "先固定劳动关系、工资标准和欠薪事实，再向单位书面催付并根据情况申请劳动仲裁。",
            "evidence_checklist": [],
            "risk_points": [],
            "next_steps": [],
            "questions_to_clarify": [],
        }
        with mock.patch.object(app_module, "_is_current_demo_mode", return_value=False), mock.patch.object(
            app_module, "_call_llm", return_value=model_result), mock.patch.object(
            app_module, "save_record"
        ):
            response = self.client.post(
                "/api/legal-agent-stream",
                json={"message": "拖欠工资有什么法律依据？"},
            )
            payload = response.get_data(as_text=True)

        events = [
            json.loads(block.removeprefix("data: "))
            for block in payload.strip().split("\n\n")
            if block.startswith("data: ")
        ]
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("X-Accel-Buffering"), "no")
        self.assertTrue(any(event.get("stage") == "understand" for event in events))
        self.assertFalse(any(event.get("stage") == "retrieve" for event in events))
        self.assertTrue(any(event.get("chunk") for event in events))
        self.assertTrue(events[-1]["done"])
        self.assertNotIn("local_references", events[-1]["result"])
        self.assertNotIn("citation_audit", events[-1]["result"])


if __name__ == "__main__":
    unittest.main()
