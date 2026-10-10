"""违禁词扫描与分级决策。

高危 → 直接拒绝发布；中危 → 转人工审核；低危 → 提示用户但仍可发布。
一条内容命中多个词时，处理方式取其中最高等级。
"""

from .models import BannedWord

SEVERITY_ACTIONS = {"high": "reject", "medium": "review", "low": "warn"}
SEVERITY_LABELS = {"high": "高危", "medium": "中危", "low": "低危"}
SEVERITY_RANK = {"high": 3, "medium": 2, "low": 1}
SEVERITY_CHOICES = ("high", "medium", "low")


def scan_text(text):
    """返回命中的违禁词列表（大小写不敏感的子串匹配）。"""
    if not text:
        return []
    haystack = str(text).lower()
    hits = []
    for row in BannedWord.query.filter_by(is_active=True).all():
        needle = (row.word or "").strip().lower()
        if needle and needle in haystack:
            hits.append({
                "word": row.word,
                "severity": row.severity,
                "action": SEVERITY_ACTIONS.get(row.severity, "warn"),
                "category": row.category,
            })
    return hits


def decide(hits):
    """按最高等级给出处理动作。返回 (action, hits)。"""
    if not hits:
        return "ok", []
    top = max(hits, key=lambda hit: SEVERITY_RANK.get(hit["severity"], 0))
    return SEVERITY_ACTIONS.get(top["severity"], "warn"), hits


def top_severity(hits):
    if not hits:
        return ""
    return max(hits, key=lambda hit: SEVERITY_RANK.get(hit["severity"], 0))["severity"]


def describe_hits(hits):
    """生成可读的命中说明，例如「命中高危词：赌博、诈骗」。"""
    if not hits:
        return ""
    top = max(hits, key=lambda hit: SEVERITY_RANK.get(hit["severity"], 0))
    words = "、".join(dict.fromkeys(hit["word"] for hit in hits))
    return f"命中{SEVERITY_LABELS.get(top['severity'], top['severity'])}词：{words}"
