from pathlib import Path

from core.result_normalization import display_text, normalize_module_result, normalize_parties


ROOT = Path(__file__).resolve().parents[1]


def test_analysis_parties_accept_object_arrays_and_role_mappings():
    assert normalize_parties([
        {"role": "原告", "name": "王某", "identity": "某大学学生"},
        {"role": "被告", "name": "李某"},
    ]) == ["原告：王某（某大学学生）", "被告：李某"]
    assert normalize_parties({"plaintiff": "王某", "defendant": {"name": "某公司"}}) == [
        "原告：王某",
        "被告：某公司",
    ]


def test_analysis_omits_empty_or_object_marker_parties():
    assert normalize_parties(None) == []
    assert normalize_parties([]) == []
    assert normalize_parties([{}, "[object Object]", None]) == []


def test_module_results_normalize_other_object_lists_to_readable_text():
    result = normalize_module_result({
        "document_type": "民事起诉状",
        "parties": [{"role": "原告", "name": "王某"}],
        "key_clauses": [{"clause": "诉讼请求", "summary": "请求返还押金", "risk_level": "中"}],
        "risk_points": [{"point": "主体信息不完整", "level": "中", "suggestion": "补充身份信息"}],
        "legal_basis": [{"law_name": "中华人民共和国民法典", "article": "第五百七十七条", "content": "违约责任"}],
        "revision_suggestions": [{"suggestion": "补充证据目录"}],
        "overall_assessment": "需要补充材料",
    }, "analyze")

    assert result["parties"] == ["原告：王某"]
    assert result["legal_basis"] == ["《中华人民共和国民法典》第五百七十七条：违约责任"]
    assert result["revision_suggestions"] == ["建议：补充证据目录"]
    assert "object" not in str(result).lower()


def test_all_professional_modules_normalize_declared_string_lists():
    strategy = normalize_module_result({
        "applicable_laws": [{"law_name": "中华人民共和国民法典", "article": "第一百八十八条"}],
        "key_evidence": [{"title": "转账记录"}],
        "next_steps": {"suggestion": "先书面催告"},
        "legal_strategy": "先协商，必要时起诉",
    }, "strategy")
    assert strategy["applicable_laws"] == ["《中华人民共和国民法典》第一百八十八条"]
    assert strategy["key_evidence"] == ["名称：转账记录"]
    assert strategy["next_steps"] == ["建议：先书面催告"]
    assert strategy["legal_strategy"]["primary"] == "先协商，必要时起诉"

    student = normalize_module_result({
        "evidence_checklist": [{"title": "聊天记录"}],
        "authority_channels": None,
        "risk_points": "不要公开未经核实的指控",
    }, "student_legal")
    assert student["evidence_checklist"] == ["名称：聊天记录"]
    assert student["authority_channels"] == []
    assert student["risk_points"][0]["point"] == "不要公开未经核实的指控"


def test_frontend_has_display_guards_for_legacy_records():
    javascript = (ROOT / "static" / "js" / "main.js").read_text(encoding="utf-8")
    assert "function readableResultValue" in javascript
    assert "function normalizePartyEntries" in javascript
    assert "const parties = normalizePartyEntries(result.parties);" in javascript
    assert "result.parties.map(escapeHtml)" not in javascript


def test_display_text_never_returns_language_object_tokens():
    assert display_text({}) == ""
    assert display_text("[object Object]") == ""
    assert display_text({"unknown_key": {"value": "可读内容"}}) == "内容：可读内容"
