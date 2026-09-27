"""Build MingJian's bundled 200-case library from public guiding cases.

The source corpus is CC0 and mirrors the full text published by the Supreme
People's Court.  The generated JSON keeps the official court URL on every
record so the UI can always take a reader back to the primary source.

Usage::

    python scripts/build_case_library.py \
      --source ../_source_chinese_law_corpus/guiding-cases \
      --output data/legal_cases_200.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import date
from pathlib import Path


CORE_CASE_NUMBERS = {23, 38, 39, 170, 180, 185, 195}
SELECTED_CASE_NUMBERS = (set(range(86, 279)) - CORE_CASE_NUMBERS) | {1, 17, 18, 64}

CATEGORY_DEFINITIONS = {
    "campus-rights": ("campus", "校园权益", ("学生", "高校", "学校", "教育", "学位", "学籍", "考试", "校园", "教师")),
    "labor": ("labor", "实习就业", ("劳动", "就业", "工资", "工伤", "竞业", "社保", "用人单位", "招聘", "职业")),
    "housing": ("housing", "租房居住", ("房屋租赁", "租房", "物业", "居住", "商品房", "房产", "拆迁", "居间合同")),
    "consumer": ("consumer", "消费维权", ("消费", "买卖合同", "食品", "服务合同", "网络购物", "产品责任", "旅游", "退货", "电信服务")),
    "cyber": ("cyber", "网络安全", ("网络", "个人信息", "隐私", "数据", "互联网", "电信诈骗", "账号", "信息网络", "计算机")),
    "family": ("family", "婚姻家庭", ("婚姻", "家庭", "继承", "抚养", "探望", "监护", "离婚", "赡养")),
    "finance": ("finance", "金融借贷", ("金融", "借贷", "银行", "信用卡", "证券", "保险", "担保", "贷款", "融资")),
    "transport": ("transport", "交通出行", ("交通事故", "机动车", "航空旅客", "铁路", "船舶", "海事", "运输合同")),
    "medical": ("medical", "生命健康", ("医疗", "药品", "健康", "人身损害", "生命权", "身体权", "医院")),
    "intellectual-property": ("ip", "知识产权", ("知识产权", "专利", "著作权", "商标", "植物新品种", "商业秘密", "不正当竞争")),
    "environment": ("environment", "环境生态", ("环境", "污染", "生态", "林业", "野生动物", "公益诉讼", "自然保护")),
    "public-governance": ("public", "行政法治", ("行政", "国家赔偿", "政府", "税务", "信息公开", "征收", "公安局")),
    "criminal": ("criminal", "刑事风险", ("刑事", "诈骗罪", "盗窃罪", "故意伤害", "危险驾驶", "贪污", "受贿", "非法经营", "开设赌场")),
    "civil-business": ("civil", "民商事", ("公司", "股权", "合同纠纷", "破产", "执行", "仲裁", "买卖")),
}

EVIDENCE_TIPS = {
    "campus": "保留校规、处分决定、送达凭证和申辩记录",
    "labor": "保留合同、工资流水、考勤和工作指令",
    "housing": "保留租赁合同、交接照片、转账凭证和维修记录",
    "consumer": "保留订单、商品页、支付凭证和客服沟通记录",
    "cyber": "及时截图、录屏并保存账号、时间和链接信息",
    "family": "保留身份关系、财产流转和实际抚养状况证据",
    "finance": "保留合同、风险提示、资金流水和催收记录",
    "transport": "保留事故认定、现场影像、医疗票据和保险材料",
    "medical": "完整保留病历、检查报告、费用凭证和知情同意材料",
    "ip": "保留首次发表、权属、使用许可和侵权比对证据",
    "environment": "保留监测数据、现场影像、时间线和损害评估材料",
    "public": "保留行政文书、送达日期、申请回执和程序记录",
    "criminal": "保留原始电子数据和资金流向，不要擅自修改或删除证据",
    "civil": "保留合同、履行凭证、沟通记录和损失证明",
}


def compact(value: object) -> str:
    if isinstance(value, list):
        value = "\n".join(str(item) for item in value if item)
    return re.sub(r"[ \t\r\f\v]+", " ", str(value or "")).strip()


def clipped(value: object, limit: int) -> str:
    text = compact(value)
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def classify(text: str, keywords: list[str]) -> tuple[str, str, str]:
    haystack = text + " " + " ".join(keywords)
    scores = {
        slug: sum(1 for term in terms if term in haystack)
        for slug, (_, _, terms) in CATEGORY_DEFINITIONS.items()
    }
    slug = max(scores, key=scores.get)
    if scores[slug] == 0:
        slug = "criminal" if "刑事" in haystack else "civil-business"
    domain, label, _ = CATEGORY_DEFINITIONS[slug]
    return slug, domain, label


def extract_case_number(text: str) -> str:
    values = re.findall(r"[（(]\d{4}[）)][^，。；\n]{2,70}?号", text)
    return clipped(values[-1], 120) if values else ""


def extract_court(text: str) -> str:
    pattern = re.compile(
        r"((?:中华人民共和国)?最高人民法院|"
        r"[一-鿿]{2,40}?(?:高级人民法院|中级人民法院|知识产权法院|互联网法院|海事法院|人民法院))"
    )
    courts = []
    for segment in re.split(r"[。；\n]", text):
        for candidate in pattern.findall(segment):
            candidate = re.sub(
                r"^.*(?:移送至|经请示|起诉至|上诉至|诉至|提请|申请|移交|发回|向|由|撤销|维持|指令|及|就)",
                "",
                candidate,
            )
            candidate = candidate.strip("，、 ")
            if candidate not in {"人民法院", "最高人民法院关于人民法院"}:
                courts.append(candidate)
    return clipped(courts[-1], 160) if courts else "生效裁判法院（详见官方原文）"


def extract_decision_date(text: str) -> str:
    values = re.findall(r"(20\d{2})年(\d{1,2})月(\d{1,2})日", text)
    if not values:
        return ""
    year, month, day = values[-1]
    try:
        return date(int(year), int(month), int(day)).isoformat()
    except ValueError:
        return ""


def infer_case_type(keywords: list[str], title: str) -> str:
    text = " ".join(keywords) + title
    for label in ("刑事附带民事公益诉讼", "国家赔偿", "行政", "刑事", "执行", "民事"):
        if label in text:
            return label
    return "民事"


def infer_cause(title: str, keywords: list[str]) -> str:
    useful = [item for item in keywords if item not in {"民事", "刑事", "行政", "执行", "国家赔偿"}]
    if useful:
        return clipped(useful[0], 160)
    tail = re.split(r"诉|申请", title)[-1]
    return clipped(tail.removesuffix("案"), 160) or "典型案例"


def parse_laws(values: list[str], case_type: str) -> list[dict[str, str]]:
    laws: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for value in values:
        matches = re.findall(r"《([^》]+)》([^《]*)", value)
        for law_name, suffix in matches:
            article = clipped(suffix.strip(" ，、；;"), 80)
            key = (law_name, article)
            if key in seen:
                continue
            seen.add(key)
            laws.append({
                "law_name": law_name,
                "article": article,
                "note": "最高人民法院指导性案例列明的关联法条",
            })
    if laws:
        return laws
    fallback = {
        "刑事": "中华人民共和国刑法",
        "行政": "中华人民共和国行政诉讼法",
        "国家赔偿": "中华人民共和国国家赔偿法",
        "执行": "中华人民共和国民事诉讼法",
    }.get(case_type, "中华人民共和国民法典")
    return [{
        "law_name": fallback,
        "article": "",
        "note": "官方案例未单列具体条号，阅读时应以现行法条和官方原文为准",
    }]


def build_record(raw: dict) -> dict:
    number = int(raw["number"])
    title = compact(raw["title"])
    keywords = [compact(item) for item in raw.get("keywords", []) if compact(item)]
    facts = clipped(raw.get("facts", []), 1800)
    gist = clipped(raw.get("gist", []), 1400)
    result = clipped(raw.get("result", []), 1600)
    reasoning = clipped(raw.get("reasoning", []), 2600)
    searchable = " ".join((title, facts, gist, reasoning, " ".join(keywords)))
    category_slug, legal_domain, category_label = classify(searchable, keywords)
    case_type = infer_case_type(keywords, title)
    law_refs = parse_laws(raw.get("relatedLaws", []), case_type)
    law_names = "、".join(item["law_name"] for item in law_refs[:3])
    tip = EVIDENCE_TIPS[legal_domain]
    plain = clipped(
        f"本案明确：{gist} 遇到类似问题时，建议{tip}，"
        f"并结合《{law_names.replace('、', '》、《')}》和最新司法解释核验具体权利。",
        700,
    )
    published = compact(raw.get("publishedAt"))
    source_url = compact(raw.get("sourceUrl"))
    digest = hashlib.sha256(
        "|".join((title, gist, result, source_url)).encode("utf-8")
    ).hexdigest()
    tags = [item for item in keywords if item not in {"民事", "刑事", "行政", "执行"}]
    if legal_domain in {"campus", "labor", "housing", "consumer", "cyber"}:
        tags.append("大学生高频")
    if published >= "2021-01-01":
        tags.append("社会热点")
    if legal_domain in {"family", "housing", "consumer", "transport", "cyber", "labor"}:
        tags.append("日常生活")
    tags = list(dict.fromkeys(tags))[:8]
    categories = [category_slug]
    if "大学生高频" in tags:
        categories.append("student-daily")
    if "社会热点" in tags:
        categories.append("social-hotspots")
    if "日常生活" in tags:
        categories.append("daily-life")
    result_text = compact(raw.get("result", []))
    return {
        "slug": f"guiding-case-{number}",
        "title": title,
        "case_number": extract_case_number(result_text),
        "guiding_case_number": f"指导性案例{number}号",
        "court_name": extract_court(result_text),
        "case_type": case_type,
        "cause": infer_cause(title, keywords),
        "legal_domain": legal_domain,
        "decision_date": extract_decision_date(result_text),
        "published_at": f"{published}T00:00:00" if published else "",
        "summary": facts,
        "dispute_focus": gist,
        "judgment_result": result,
        "judgment_reasoning": reasoning,
        "ai_plain_language": plain,
        "keywords": ",".join(list(dict.fromkeys(keywords + tags))),
        "source_publisher": "中华人民共和国最高人民法院",
        "source_type": "official_court_guiding",
        "source_external_id": f"guiding-{number}",
        "source_url": source_url,
        "source_hash": digest,
        "image_url": "",
        "image_alt": "",
        "image_source_url": "",
        "categories": categories,
        "tags": tags or [category_label],
        "laws": law_refs,
    }


def build(source: Path) -> dict:
    manifest = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
    records = []
    for item in manifest["cases"]:
        number = int(item["number"])
        if number not in SELECTED_CASE_NUMBERS:
            continue
        raw = json.loads((source / item["file"]).read_text(encoding="utf-8"))
        records.append(build_record(raw))
    records.sort(key=lambda item: int(item["source_external_id"].split("-")[-1]))
    if len(records) != 193:
        raise RuntimeError(f"expected 193 supplemental cases, got {len(records)}")
    if len({item["slug"] for item in records}) != len(records):
        raise RuntimeError("duplicate case slug generated")
    return {
        "schema_version": 1,
        "generated_at": date.today().isoformat(),
        "case_count": len(records),
        "total_with_core_cases": len(records) + len(CORE_CASE_NUMBERS),
        "source_repository": "https://github.com/lttxzmj/chinese-law-corpus",
        "source_license": "CC0-1.0",
        "official_index_url": "https://www.court.gov.cn/fabu/gengduo/151.html",
        "selection_note": "优先收录指导性案例86—278号，并补充居间、汽车消费、劳动合同和电信服务等日常生活早期案例。",
        "cases": records,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("data/legal_cases_200.json"))
    args = parser.parse_args()
    payload = build(args.source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"wrote {payload['case_count']} supplemental cases "
        f"({payload['total_with_core_cases']} total) to {args.output}"
    )


if __name__ == "__main__":
    main()
