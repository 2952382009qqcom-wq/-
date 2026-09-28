"""Shared, explainable legal taxonomy for conversations and court cases.

Conversation classification gives concrete scenarios (renting, wages,
refunds) more weight than generic words such as ``学生``.  Court-case
classification is stricter still: only titles, causes, keywords and a short
dispute focus participate, so a stray word in a long judgment cannot turn a
murder or patent case into a student case.
"""

import re


COMMUNITY_CATEGORIES = (
    ("campus-rights", "校园权益", "学籍、奖助、处分、隐私与校园管理", "校"),
    ("internship-jobs", "实习就业", "实习、兼职、劳动合同与工资报酬", "职"),
    ("renting", "租房", "租赁合同、押金、退租与居住安全", "租"),
    ("consumer-rights", "消费维权", "购物、培训、服务、退款与平台争议", "消"),
    ("cyber-security", "网络安全", "账号、隐私、网暴、诈骗与个人信息", "网"),
)

# Broad, overlapping buckets such as "大学生常见" and "日常问题" were
# removed. Every visible filter now represents one concrete legal domain.
CASE_CATEGORIES = (
    ("campus-rights", "校园与教育", "教育管理、学籍学位与学生权利"),
    ("labor", "实习与就业", "劳动关系、实习报酬、招聘与竞业"),
    ("housing", "租房居住", "房屋租赁、押金与居住权益"),
    ("consumer", "消费维权", "商品、服务、培训与平台消费"),
    ("cyber", "网络与隐私", "个人信息、网络侵权与电信网络诈骗"),
    ("family", "婚姻家庭", "婚姻、继承、抚养、监护与家事纠纷"),
    ("finance", "金融借贷", "借贷、保险、银行、证券与担保"),
    ("transport", "交通出行", "道路交通、航空、铁路与运输责任"),
    ("medical", "生命健康", "医疗、药品、健康与人身损害"),
    ("intellectual-property", "知识产权", "著作权、商标、专利与商业秘密"),
    ("environment", "环境生态", "污染防治、生态保护与公益诉讼"),
    ("public-governance", "行政法治", "行政行为、信息公开与国家赔偿"),
    ("criminal", "刑事风险", "诈骗、侵犯人身财产与刑事合规"),
    ("civil-business", "民商事", "合同、公司、破产、执行与商事交易"),
)

DOMAIN_KEYWORDS = {
    "campus": {
        "学籍": 6, "学位": 6, "毕业证": 6, "处分": 5, "奖学金": 5,
        "助学金": 5, "宿舍": 4, "辅导员": 4, "高校": 3, "学院": 2,
        "大学": 2, "学校": 2, "学生": 1,
    },
    "labor": {
        "劳动合同": 6, "劳动关系": 6, "工伤": 6, "工资": 5, "欠薪": 5,
        "实习": 5, "兼职": 5, "就业": 4, "招聘": 4, "社保": 4,
        "加班": 4, "竞业": 4, "用人单位": 3, "解除合同": 3,
    },
    "housing": {
        "租房": 7, "房屋租赁": 7, "退租": 6, "房东": 6, "房租": 5,
        "押金": 5, "承租": 5, "出租": 4, "合租": 4, "租赁": 3,
        "租客": 4, "中介费": 4,
    },
    "consumer": {
        "消费者": 6, "退款": 5, "退费": 5, "预付费": 5, "食品安全": 5,
        "培训机构": 5, "网购": 4, "商品": 3, "商家": 3, "消费": 3,
        "服务": 1, "赔偿": 1,
    },
    "cyber": {
        "个人信息": 7, "隐私": 6, "网暴": 6, "偷拍视频": 6,
        "电信诈骗": 6, "网络诈骗": 6, "账号": 5, "验证码": 5,
        "泄露": 4, "转账": 3, "诈骗": 3, "网络": 1,
    },
    "family": {
        "离婚": 8, "婚姻": 6, "抚养": 7, "赡养": 7, "继承": 7,
        "监护": 6, "彩礼": 6, "夫妻": 4, "家暴": 8,
    },
    "finance": {
        "借贷": 7, "贷款": 6, "网贷": 7, "信用卡": 6, "担保": 6,
        "保险": 6, "证券": 6, "银行": 4, "利息": 4,
    },
    "transport": {
        "交通事故": 9, "车祸": 8, "撞车": 7, "机动车": 6,
        "交通肇事": 8, "航空": 5, "铁路": 5, "运输": 4,
    },
    "medical": {
        "医疗事故": 9, "医疗损害": 9, "误诊": 8, "医院": 5,
        "医生": 4, "药品": 5, "人身损害": 5, "伤残": 4,
    },
    "ip": {
        "著作权": 8, "版权": 7, "商标": 7, "专利": 7,
        "知识产权": 8, "抄袭": 6, "商业秘密": 7,
    },
    "environment": {
        "环境污染": 8, "生态": 6, "污染": 6, "噪声": 5,
        "排污": 6, "野生动物": 5,
    },
    "public": {
        "行政处罚": 8, "行政复议": 8, "行政诉讼": 8,
        "信息公开": 7, "国家赔偿": 7, "征收": 6,
    },
    "criminal": {
        "抢劫": 12, "抢夺": 11, "正当防卫": 12, "打回去": 11,
        "还手": 10, "反击": 8, "被打": 8, "殴打": 8,
        "故意伤害": 11, "盗窃": 10, "杀人": 10, "强奸": 10,
        "寻衅滋事": 10, "聚众斗殴": 10, "刑事": 8, "犯罪": 7,
        "定什么罪": 7, "定啥罪": 7, "判几年": 6,
    },
    "civil": {
        "合同纠纷": 6, "违约": 5, "欠款": 5, "公司": 3,
        "股权": 6, "破产": 6, "执行": 4, "诉讼": 2,
    },
}


# Expand colloquial questions with legal concepts that are likely to appear in
# official case titles and keywords.  Keep the original wording so the UI can
# still explain what the user actually asked.
LEGAL_QUERY_EXPANSIONS = (
    (("抢劫",), "抢劫罪 暴力 胁迫 非法占有 财物"),
    (("抢夺",), "抢夺罪 乘人不备 夺取财物"),
    (("打回去", "还手", "反击", "正当防卫", "被打", "殴打"), "正当防卫 故意伤害 互殴 不法侵害 防卫限度"),
    (("校园欺凌", "学生霸凌", "校园暴力"), "学生霸凌 校园暴力 正当防卫 教育管理责任"),
)

DOMAIN_LABELS = {
    "campus": "校园与教育", "labor": "实习与就业", "housing": "租房居住",
    "consumer": "消费维权", "cyber": "网络与隐私", "family": "婚姻家庭",
    "finance": "金融借贷", "transport": "交通出行", "medical": "生命健康",
    "ip": "知识产权", "environment": "环境生态", "public": "行政法治",
    "criminal": "刑事风险", "civil": "民商事", "other": "综合法律问题",
}

DOMAIN_TO_CASE_CATEGORY = {
    "campus": "campus-rights", "labor": "labor", "housing": "housing",
    "consumer": "consumer", "cyber": "cyber", "family": "family",
    "finance": "finance", "transport": "transport", "medical": "medical",
    "ip": "intellectual-property", "environment": "environment",
    "public": "public-governance", "criminal": "criminal", "civil": "civil-business",
}

# Specific concepts outweigh generic terms such as "网络", "合同" or "学校".
CASE_DOMAIN_RULES = {
    "campus": {"拒发毕业证": 12, "拒绝颁发毕业证": 12, "不授予学位": 12, "拒绝授予学位": 12, "学籍": 10, "学生处分": 9, "开除学籍": 9, "退学处理": 9, "教育行政": 8, "教育机构责任": 9, "校园暴力": 9, "校园体育": 8, "教育惩戒": 9, "学位": 7, "招生": 5, "学生": 5, "学校": 4},
    "labor": {"劳动争议": 10, "劳动合同": 9, "劳动关系": 9, "工伤": 8, "就业歧视": 8, "工资": 6, "竞业": 6, "社会保险": 6, "用人单位": 5, "招聘": 4, "实习": 5},
    "housing": {"房屋租赁": 11, "住房租赁": 11, "承租人": 8, "出租人": 8, "房屋押金": 7, "租金": 7, "物业服务": 5, "居住": 3},
    "consumer": {"消费者权益": 10, "消费者": 8, "食品安全": 8, "产品责任": 8, "网络购物": 7, "预付": 6, "退费": 6, "旅游合同": 5},
    "cyber": {"个人信息": 10, "隐私权": 9, "电信网络诈骗": 9, "网络诈骗": 8, "破坏计算机信息系统": 8, "账号": 5, "数据": 4, "互联网": 2, "网络": 1},
    "family": {"离婚": 10, "继承": 9, "抚养": 9, "赡养": 9, "监护": 8, "婚姻家庭": 8, "夫妻": 6, "探望": 6},
    "finance": {"金融借款": 10, "民间借贷": 9, "融资租赁": 10, "信用卡": 8, "证券": 8, "保险": 8, "银行": 7, "担保": 7, "贷款": 6, "融资": 5},
    "transport": {"交通事故": 10, "机动车": 8, "道路交通": 8, "航空旅客": 8, "铁路": 7, "船舶": 7, "海事": 7, "运输合同": 6},
    "medical": {"医疗损害": 10, "医疗": 8, "医院": 7, "药品": 7, "生命权": 6, "健康权": 6, "人身损害": 5},
    "ip": {"侵害商标权": 11, "侵害专利权": 11, "侵害著作权": 11, "信息网络传播权": 11, "知识产权": 10, "商业秘密": 9, "植物新品种": 9, "不正当竞争": 7, "商标": 7, "专利": 7, "著作权": 7},
    "environment": {"环境污染": 10, "生态环境": 9, "环境公益诉讼": 9, "污染": 7, "生态": 7, "自然保护": 6, "野生动物": 6},
    "public": {"行政处罚": 10, "行政许可": 10, "政府信息公开": 10, "国家赔偿": 9, "行政诉讼": 9, "行政": 6, "征收": 6, "税务": 6, "公安局": 5},
    "criminal": {"故意杀人罪": 12, "抢劫罪": 11, "诈骗罪": 11, "盗窃罪": 11, "故意伤害罪": 11, "刑事": 9, "犯罪": 8, "受贿": 8, "贪污": 8, "非法经营": 8, "开设赌场": 8, "组织、领导": 5, "罪": 4},
    "civil": {"公司纠纷": 8, "股权": 8, "破产": 8, "执行复议": 8, "拍卖": 7, "仲裁": 7, "建设工程": 6, "合同纠纷": 4, "买卖合同": 4},
}

SLUG_TO_DOMAIN = {
    "campus-rights": "campus", "internship-jobs": "labor", "labor": "labor",
    "renting": "housing", "housing": "housing", "consumer-rights": "consumer",
    "consumer": "consumer", "cyber-security": "cyber", "cyber": "cyber",
}


def infer_legal_domains(text: str) -> list[str]:
    value = re.sub(r"\s+", " ", str(text or "")).lower()
    scores = {
        domain: sum(weight for keyword, weight in keywords.items() if keyword.lower() in value)
        for domain, keywords in DOMAIN_KEYWORDS.items()
    }
    return [
        domain for domain, score in sorted(scores.items(), key=lambda pair: pair[1], reverse=True)
        if score > 0
    ]


def infer_legal_domain(text: str, fallback: str = "other") -> str:
    ranked = infer_legal_domains(text)
    return ranked[0] if ranked else fallback


def expand_legal_query(text: str) -> str:
    """Add stable legal vocabulary to a short colloquial search question."""
    value = re.sub(r"\s+", " ", str(text or "")).strip()
    if not value:
        return ""
    for triggers, expansion in LEGAL_QUERY_EXPANSIONS:
        if any(trigger in value for trigger in triggers):
            return f"{value} {expansion}"
    return value


def classify_case_content(
    *, title: str, cause: str = "", keywords: str | list[str] = "",
    dispute_focus: str = "", case_type: str = "", fallback: str = "civil",
) -> tuple[str, str]:
    """Return a precise ``(category_slug, legal_domain)`` for a court case."""
    keyword_text = " ".join(keywords) if isinstance(keywords, (list, tuple)) else str(keywords or "")
    primary = re.sub(r"\s+", " ", " ".join((str(title or ""), str(cause or ""), keyword_text)))
    secondary = re.sub(r"\s+", " ", str(dispute_focus or ""))[:900]
    scores = {}
    primary_scores = {}
    secondary_scores = {}
    for domain, rules in CASE_DOMAIN_RULES.items():
        primary_score = sum(weight for term, weight in rules.items() if term in primary)
        secondary_score = sum(weight for term, weight in rules.items() if term in secondary)
        primary_scores[domain] = primary_score
        secondary_scores[domain] = secondary_score
        scores[domain] = primary_score + secondary_score * 0.35

    type_forced = False
    if "刑" in str(case_type or "") or re.search(r"(?:罪|刑事)(?:案|附带|$)", primary):
        scores["criminal"] += 8
        type_forced = True
    elif "行政" in str(case_type or ""):
        scores["public"] += 7
        type_forced = True

    best = max(scores, key=scores.get) if scores else fallback
    # A single generic word in a judgment's reasoning is not a category.
    if not type_forced and primary_scores.get(best, 0) < 4 and secondary_scores.get(best, 0) < 12:
        best = fallback if fallback in DOMAIN_TO_CASE_CATEGORY else "civil"
    elif scores.get(best, 0) <= 0:
        best = fallback if fallback in DOMAIN_TO_CASE_CATEGORY else "civil"
    return DOMAIN_TO_CASE_CATEGORY[best], best


def domain_for_category(slug: str) -> str:
    return SLUG_TO_DOMAIN.get(str(slug or ""), "other")


def safe_search_terms(value: str) -> list[str]:
    """Keep only non-identifying topic terms for recommendation telemetry."""
    return infer_legal_domains(value)[:5]
