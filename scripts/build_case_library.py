"""Build MingJian's bundled 500-case library from public court cases.

The source corpus is CC0 and mirrors the full text published by the Supreme
People's Court.  The generated JSON keeps the official court URL on every
record so the UI can always take a reader back to the primary source.

Usage::

    python scripts/build_case_library.py \
      --source ../_source_chinese_law_corpus/guiding-cases \
      --gazette-source ../_source_chinese_law_corpus/gazette-cases \
      --output data/legal_cases_500.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.taxonomy import DOMAIN_LABELS, classify_case_content


CORE_CASE_NUMBERS = {23, 38, 39, 170, 180, 185, 195}
SELECTED_CASE_NUMBERS = set(range(1, 280)) - CORE_CASE_NUMBERS
GAZETTE_TARGET = 222

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
    case_type = infer_case_type(keywords, title)
    cause = infer_cause(title, keywords)
    category_slug, legal_domain = classify_case_content(
        title=title, cause=cause, keywords=keywords, dispute_focus=gist,
        case_type=case_type,
    )
    category_label = DOMAIN_LABELS[legal_domain]
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
    tags = list(dict.fromkeys(tags))[:8]
    categories = [category_slug]
    result_text = compact(raw.get("result", []))
    return {
        "slug": f"guiding-case-{number}",
        "title": title,
        "case_number": extract_case_number(result_text),
        "guiding_case_number": f"指导性案例{number}号",
        "court_name": extract_court(result_text),
        "case_type": case_type,
        "cause": cause,
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


def court_excerpt(value: str, limit: int) -> str:
    """Keep only short, minimally redacted excerpts from public judgments."""
    value = compact(value)
    value = re.sub(r"(?<!\d)1[3-9]\d{9}(?!\d)", "[手机号已隐去]", value)
    value = re.sub(r"(?<!\d)\d{17}[\dXx](?!\d)", "[身份证号已隐去]", value)
    value = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "[邮箱已隐去]", value)
    return clipped(value, limit)


FACT_MARKERS = (
    "经审理查明", "本院查明", "本院再审查明", "查明事实", "认定事实", "原审查明",
    "一审查明", "二审查明", "法院查明", "中院查明", "高院查明", "本院对一、二审法院查明",
)
REASON_MARKERS = ("本院认为", "本院再审认为", "本院二审认为", "本院经审查认为", "本院经审理认为", "法院认为")
RESULT_MARKERS = ("判决如下", "裁定如下", "裁判如下", "决定如下")
FOCUS_MARKERS = ("争议焦点", "争议的焦点", "审查的焦点", "争议问题", "焦点问题", "问题在于", "本案焦点", "本案争点", "核心争议")


def marker_positions(body: list[str], markers: tuple[str, ...], before: int | None = None) -> list[int]:
    return [
        index for index, paragraph in enumerate(body[:before])
        if any(marker in paragraph for marker in markers)
    ]


def court_laws(body: list[str]) -> list[dict[str, str]]:
    """Only link instruments explicitly named in the court's own reasoning."""
    laws_by_name: dict[str, dict[str, str]] = {}
    for paragraph in body:
        for match in re.finditer(r"《([^》]{3,100})》([^《。；\n]{0,50})", paragraph):
            name, suffix = match.groups()
            if not any(word in name for word in ("法", "条例", "规定", "解释", "办法", "规则", "实施细则")):
                continue
            if "通知" in name or "会议纪要" in name:
                continue
            if any(word in name for word in ("合同", "协议", "章程", "通知书")) and "劳动合同法" not in name and "合同法" not in name:
                continue
            article_match = re.match(r"\s*(第[一二三四五六七八九十百千万零〇两\d]+条(?:第[一二三四五六七八九十百千万零〇两\d]+款)?)", suffix)
            article = article_match.group(1) if article_match else ""
            if name not in laws_by_name:
                laws_by_name[name] = {
                    "law_name": name,
                    "article": article,
                    "note": "原裁判文书法院说理中提及；可能适用历史版本，请核对现行法律",
                }
            elif article and not laws_by_name[name]["article"]:
                laws_by_name[name]["article"] = article
    laws = list(laws_by_name.values())
    laws.sort(key=lambda item: any(word in item["law_name"] for word in ("民事诉讼法", "刑事诉讼法", "行政诉讼法")))
    return laws[:3]


def build_gazette_record(raw: dict) -> dict | None:
    body = [compact(paragraph) for paragraph in raw.get("body", []) if compact(paragraph)]
    result_positions = marker_positions(body, RESULT_MARKERS)
    if not result_positions:
        return None
    result_index = result_positions[-1]
    reasoning_positions = [
        index for index in marker_positions(body, REASON_MARKERS, result_index)
        if min((body[index].find(marker) for marker in REASON_MARKERS if marker in body[index]), default=999) < 40
    ]
    if not reasoning_positions:
        return None
    reasoning_index = reasoning_positions[-1]
    fact_positions = marker_positions(body, FACT_MARKERS, reasoning_index)
    fact_candidates = []
    for index in fact_positions:
        paragraph = body[index]
        starts = [paragraph.find(marker) for marker in FACT_MARKERS if marker in paragraph]
        if not starts or min(starts) > 45:
            continue
        marker = next(marker for marker in FACT_MARKERS if marker in paragraph)
        fact = paragraph.split(marker, 1)[1].lstrip("：:，,。 ")
        if len(fact) < 80 and index + 1 < reasoning_index:
            fact = body[index + 1]
        if len(fact) >= 80 and not any(fact.startswith(prefix) for prefix in ("本院认为", "法院认为", "请求驳回", "请求撤销")):
            fact_candidates.append((index, fact))
    reason_paragraphs = body[reasoning_index:result_index + 1]
    laws = court_laws(reason_paragraphs)
    if not laws:
        return None

    title = compact(raw["title"])
    if fact_candidates:
        summary = court_excerpt(fact_candidates[-1][1], 850)
    else:
        factual_reason = next(
            (paragraph for paragraph in reason_paragraphs
             if len(paragraph) >= 100 and any(word in paragraph for word in ("本案中", "案涉", "涉案", "本案事实"))
             and not paragraph.startswith(("根据《", "依照《"))
             and not any(word in paragraph[:100] for word in ("争议焦点", "焦点问题", "本案焦点"))),
            "",
        )
        if not factual_reason:
            factual_reason = next(
                (paragraph for paragraph in reason_paragraphs
                 if len(paragraph) >= 100 and "案涉" in paragraph),
                "",
            )
        if not factual_reason:
            return None
        summary = court_excerpt("法院说理中记载的案情要点：" + factual_reason, 850)
    focus_positions = marker_positions(body, FOCUS_MARKERS, result_index)
    if focus_positions:
        focus = body[focus_positions[-1]]
        start = min((focus.find(marker) for marker in FOCUS_MARKERS if marker in focus), default=0)
        focus = focus[start:]
        focus = court_excerpt(focus, 460)
    else:
        focus = f"本案涉及{title.removesuffix('案')}；具体争点请结合官方裁判文书的法院说理核对。"
    reasoning = court_excerpt(" ".join(body[reasoning_index:min(reasoning_index + 3, result_index)]), 850)
    result_tail = body[result_index].split(next(marker for marker in RESULT_MARKERS if marker in body[result_index]), 1)[1]
    operative = [result_tail.lstrip("：: ")] if result_tail.strip("：: ") else []
    for paragraph in body[result_index + 1:result_index + 7]:
        if any(stop in paragraph for stop in ("案件受理费", "审判长", "本判决为终审", "本裁定为终审")):
            break
        operative.append(paragraph)
        if len(operative) >= 3:
            break
    result = re.split(r"审\s*判\s*长|代理审判员|书\s*记\s*员", court_excerpt(" ".join(operative), 700))[0].strip()
    if len(summary) < 80 or len(reasoning) < 80 or not all((focus, result)):
        return None

    case_number = compact(raw.get("caseNumber"))
    case_type = "刑事" if "刑" in case_number else "行政" if "行" in case_number else "民事"
    cause = clipped(title.removesuffix("案").split("等")[-1], 160)
    category_slug, domain = classify_case_content(
        title=title, cause=cause, dispute_focus=focus, case_type=case_type,
    )
    category_label = DOMAIN_LABELS[domain]
    year = int(raw["issueYear"])
    issue = int(raw["issueNo"])
    tip = EVIDENCE_TIPS[domain]
    plain = (
        f"这是《最高人民法院公报》{year}年第{issue}期刊载的{case_type}裁判，"
        f"主题为{title.removesuffix('案')}。遇到类似问题，建议{tip}；"
        "请先看本案实际裁判理由和结果，再核对目前有效的法律与司法解释。"
    )
    tags = ["公报裁判", f"{year}年公报", category_label]
    categories = [category_slug]
    source_url = compact(raw.get("sourceUrl")).replace("http://gongbao.court.gov.cn/", "https://gongbao.court.gov.cn/", 1)
    digest = hashlib.sha256("|".join((title, summary, reasoning, result, source_url)).encode("utf-8")).hexdigest()
    return {
        "slug": compact(raw["id"]),
        "title": title,
        "case_number": case_number,
        "guiding_case_number": "",
        "court_name": clipped(raw.get("court"), 160),
        "case_type": case_type,
        "cause": cause,
        "legal_domain": domain,
        "decision_date": "",
        "published_at": "",  # An issue number is not an exact publication date.
        "summary": summary,
        "dispute_focus": focus,
        "judgment_result": result,
        "judgment_reasoning": reasoning,
        "ai_plain_language": plain,
        "keywords": ",".join(tags),
        "source_publisher": "中华人民共和国最高人民法院公报",
        "source_type": "official_court_gazette",
        "source_external_id": compact(raw["id"]),
        "source_url": source_url,
        "source_hash": digest,
        "image_url": "",
        "image_alt": "",
        "image_source_url": "",
        "categories": categories,
        "tags": tags,
        "laws": laws,
    }


def build(source: Path, gazette_source: Path) -> dict:
    manifest = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
    records = []
    for item in manifest["cases"]:
        number = int(item["number"])
        if number not in SELECTED_CASE_NUMBERS:
            continue
        raw = json.loads((source / item["file"]).read_text(encoding="utf-8"))
        records.append(build_record(raw))
    records.sort(key=lambda item: int(item["source_external_id"].split("-")[-1]))
    if len(records) != 271:
        raise RuntimeError(f"expected 271 supplemental guiding cases, got {len(records)}")
    existing_numbers = {re.sub(r"[()（）\s]", "", record["case_number"]) for record in records}
    gazette_candidates = []
    for path in gazette_source.glob("*.json"):
        raw = json.loads(path.read_text(encoding="utf-8"))
        number = re.sub(r"[()（）\s]", "", compact(raw.get("caseNumber")))
        if number and number in existing_numbers:
            continue
        record = build_gazette_record(raw)
        if record:
            year = int(raw["issueYear"])
            focus_bonus = 20 if "具体争点请" not in record["dispute_focus"] else 0
            gazette_candidates.append((year, 6 * (year - 2000) + focus_bonus, record))
    # Exhaust recent usable judgments before using older, topical classics.
    gazette_candidates.sort(key=lambda pair: (-(pair[0] >= 2020), -(pair[0] >= 2015), -pair[1], pair[2]["source_external_id"]))
    gazette_records = []
    selected_numbers = set(existing_numbers)
    for _, _, record in gazette_candidates:
        number = re.sub(r"[()（）\s]", "", record["case_number"])
        if number and number in selected_numbers:
            continue
        gazette_records.append(record)
        if number:
            selected_numbers.add(number)
        if len(gazette_records) == GAZETTE_TARGET:
            break
    if len(gazette_records) != GAZETTE_TARGET:
        raise RuntimeError(f"expected {GAZETTE_TARGET} usable gazette cases, got {len(gazette_records)}")
    records.extend(gazette_records)
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
        "selection_note": "除7件人工精校案例外收录全部指导性案例；公报裁判文书优先选取年份较近、有法院说理、结果及明确提及法律依据的222件。优先摘录法院查明事实；无独立事实段时使用法院说理中的案情要点。公报法律依据可能为历史版本。",
        "cases": records,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--gazette-source", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("data/legal_cases_500.json"))
    args = parser.parse_args()
    payload = build(args.source, args.gazette_source)
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
