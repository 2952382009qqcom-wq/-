"""Shared legal-domain taxonomy used by community, cases and recommendations."""

import re


COMMUNITY_CATEGORIES = (
    ("campus-rights", "校园权益", "学籍、奖助、处分、隐私与校园管理", "校"),
    ("internship-jobs", "实习就业", "实习、兼职、劳动合同与工资报酬", "职"),
    ("renting", "租房", "租赁合同、押金、退租与居住安全", "租"),
    ("consumer-rights", "消费维权", "购物、培训、服务、退款与平台争议", "消"),
    ("cyber-security", "网络安全", "账号、隐私、网暴、诈骗与个人信息", "网"),
)

CASE_CATEGORIES = (
    ("student-daily", "大学生常见", "学籍、实习、租房、消费、防诈与网络权益"),
    ("social-hotspots", "社会热点", "近年发布且具有公共关注度的典型案例"),
    ("daily-life", "日常问题", "家庭、居住、消费、出行、网络与就业问题"),
    ("campus-rights", "校园权益", "教育管理、学籍学位与学生权利"),
    ("labor", "实习就业", "劳动关系、报酬、竞业与招聘"),
    ("housing", "租房居住", "房屋租赁、押金与居住权益"),
    ("consumer", "消费维权", "商品、服务、培训与平台消费"),
    ("cyber", "网络安全", "个人信息、网络侵权与电信网络诈骗"),
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
    "campus": ("学校", "大学", "学院", "学生", "学籍", "学位", "毕业证", "处分", "奖学金", "宿舍", "辅导员"),
    "labor": ("实习", "就业", "兼职", "劳动", "工资", "加班", "社保", "招聘", "竞业", "解除合同"),
    "housing": ("租房", "租赁", "房东", "押金", "退租", "房租", "中介", "合租"),
    "consumer": ("消费", "退款", "退费", "商品", "培训", "商家", "平台", "预付费", "食品", "赔偿"),
    "cyber": ("网络", "账号", "隐私", "个人信息", "网暴", "诈骗", "转账", "偷拍视频", "泄露"),
}

SLUG_TO_DOMAIN = {
    "campus-rights": "campus",
    "internship-jobs": "labor",
    "labor": "labor",
    "renting": "housing",
    "housing": "housing",
    "consumer-rights": "consumer",
    "consumer": "consumer",
    "cyber-security": "cyber",
    "cyber": "cyber",
}


def infer_legal_domain(text: str, fallback: str = "other") -> str:
    value = re.sub(r"\s+", " ", str(text or "")).lower()
    scores = {
        domain: sum(1 for keyword in keywords if keyword.lower() in value)
        for domain, keywords in DOMAIN_KEYWORDS.items()
    }
    best = max(scores, key=scores.get) if scores else fallback
    return best if scores.get(best, 0) else fallback


def domain_for_category(slug: str) -> str:
    return SLUG_TO_DOMAIN.get(str(slug or ""), "other")


def safe_search_terms(value: str) -> list[str]:
    """Keep only non-identifying topic terms for recommendation telemetry."""
    text = str(value or "")
    terms = []
    for domain, keywords in DOMAIN_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            terms.append(domain)
    return terms[:5]
