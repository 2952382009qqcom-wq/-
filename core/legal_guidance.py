"""Small verified legal anchors for high-frequency legal characterisation questions.

These anchors are deliberately narrow.  They do not replace model analysis;
they prevent a direct question such as "能打回去吗" or "定什么罪" from
losing the governing provision when the model concentrates on practical steps.
"""

from __future__ import annotations

import re


LEGAL_ANCHORS = {
    "self_defense": (
        {
            "law_name": "《中华人民共和国刑法》",
            "article": "第二十条",
            "summary": "为制止正在进行的不法侵害而实施、并对不法侵害人造成损害的，符合条件时属于正当防卫；明显超过必要限度并造成重大损害的，可能构成防卫过当。",
        },
        {
            "law_name": "《中华人民共和国刑法》",
            "article": "第二百三十四条",
            "summary": "主动报复、相互斗殴或不符合正当防卫条件而故意伤害他人，达到相应程度时可能构成故意伤害罪。",
        },
    ),
    "robbery": (
        {
            "law_name": "《中华人民共和国刑法》",
            "article": "第二百六十三条",
            "summary": "以暴力、胁迫或者其他方法抢劫公私财物的，通常按抢劫罪评价；具体责任和量刑取决于手段、后果、数额及是否存在法定加重情形。",
        },
        {
            "law_name": "《中华人民共和国刑法》",
            "article": "第二百六十七条",
            "summary": "若主要是乘人不备公然夺取财物而非以暴力、胁迫压制反抗，可能涉及抢夺罪；携带凶器抢夺依法按抢劫罪处理。",
        },
    ),
    "assault": (
        {
            "law_name": "《中华人民共和国刑法》",
            "article": "第二百三十四条",
            "summary": "故意伤害他人身体，达到刑事追诉所需的事实和伤情条件时，可能构成故意伤害罪。",
        },
    ),
}


_LEGAL_CHARACTERISATION_RE = re.compile(
    r"(能不能|能.{0,6}吗|可不可以|可以.{0,4}吗|合法吗|违法吗|什么罪|啥罪|定.{0,3}罪|"
    r"构成.{0,4}罪|判几年|怎么判|什么责任|法律依据|法条|处罚)"
)


def legal_topics_for_question(question: str) -> list[str]:
    value = re.sub(r"\s+", "", str(question or ""))
    topics: list[str] = []
    if any(term in value for term in ("抢劫", "抢夺")):
        topics.append("robbery")
    if any(term in value for term in ("打回去", "还手", "反击", "正当防卫")):
        topics.append("self_defense")
    elif any(term in value for term in ("被打", "打人", "殴打", "故意伤害")):
        topics.append("assault")
    return topics


def requires_legal_basis(question: str) -> bool:
    """Whether this turn asks for legal characterisation rather than first aid."""
    value = re.sub(r"\s+", "", str(question or ""))
    return bool(legal_topics_for_question(value) and _LEGAL_CHARACTERISATION_RE.search(value))


def legal_anchors_for_question(question: str) -> list[dict[str, str]]:
    anchors: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for topic in legal_topics_for_question(question):
        for anchor in LEGAL_ANCHORS[topic]:
            key = (anchor["law_name"], anchor["article"])
            if key not in seen:
                anchors.append(dict(anchor))
                seen.add(key)
    return anchors


def format_legal_basis(anchors: list[dict[str, str]]) -> list[str]:
    return [
        f"{item['law_name']}{item['article']}：{item['summary']}"
        for item in anchors
        if item.get("law_name") and item.get("article") and item.get("summary")
    ]
