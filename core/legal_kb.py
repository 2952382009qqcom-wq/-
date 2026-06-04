"""法律知识库 — 基于倒排索引 + BM25 的关键词检索"""
from __future__ import annotations
import json
import os
from collections import defaultdict
from rank_bm25 import BM25Okapi
import jieba

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
MIN_PROVISION_RELEVANCE = 0.70

# 这些词常常描述“不满/程序/时间”，但不能单独证明法条相关。
# 例如“奖学金评选不公平”不应仅因“不公平/公平”命中外商投资、证券、国资等法条。
GENERIC_QUERY_TERMS = {
    "公平", "公正", "公开", "公示", "不公平", "不公正", "不公开", "公平公正", "公开公平公正",
    "期间", "期限", "评定", "评选", "评审", "认定", "依据", "处理", "管理", "规定",
    "取消", "被取消", "怎么办", "怎么", "如何", "问题", "的是", "是否", "可以",
    "国家", "审批", "材料", "侵犯", "未经",
    "投诉", "信息", "泄露", "账号", "平台", "老板", "商家", "房东", "被拒", "要求",
    "导致", "小区", "设施", "不退",
    "理由", "虚假", "宣传", "赔偿", "被", "拒",
    "三倍", "歧视", "男生", "只要",
    "大学生", "后来", "没有", "安排", "工作", "能否", "主张",
}

CUSTOM_LEGAL_TERMS = [
    "三倍赔偿", "虚假宣传", "七天无理由退货", "无理由退货", "就业歧视",
    "个人信息", "敏感个人信息", "劳动仲裁", "拖欠工资", "租房押金",
    "物业服务", "国家助学金", "国家奖学金", "入党政审",
    "宿舍纠纷", "宿舍隐私", "宿舍被盗", "校园处分", "处分申诉",
    "成绩复核", "学籍异动", "困难认定", "奖学金异议", "助学金异议",
    "校外兼职", "兼职押金", "兼职被骗", "实习协议", "三方协议",
    "培训贷", "校园贷", "先学后付", "学生个人信息", "校园欺凌",
    "网络暴力", "偷拍视频", "偷拍", "隐私泄露", "社团收费", "社团赞助", "社团活动事故",
    "培训机构跑路", "考研培训", "考试作弊", "学术不端", "师生矛盾",
    "辅导员", "评优评先", "推优入党",
]

SCENARIO_CONTEXT_TERMS = {
    "校外兼职": ["校外兼职", "兼职"],
    "兼职押金": ["校外兼职", "兼职押金", "兼职", "押金不退"],
    "兼职被骗": ["校外兼职", "兼职被骗", "兼职", "诈骗"],
    "拖欠工资": ["拖欠工资", "工资", "劳动仲裁"],
    "租房押金": ["租房", "租房押金"],
    "培训贷": ["培训贷", "先学后付"],
    "校园贷": ["校园贷", "培训贷"],
    "宿舍纠纷": ["宿舍纠纷", "宿舍"],
    "宿舍被盗": ["宿舍被盗", "宿舍", "财物丢失"],
    "七天无理由退货": ["七天无理由退货", "网购", "退货"],
    "虚假宣传": ["虚假宣传", "欺诈"],
    "就业歧视": ["就业歧视", "歧视"],
}

for term in CUSTOM_LEGAL_TERMS:
    jieba.add_word(term)


class LegalKnowledgeBase:
    def __init__(self):
        self.provisions = []
        self.risk_patterns = []
        self._provision_tokens = []
        self._risk_tokens = []
        self.bm25 = None
        self.risk_bm25 = None
        self._inverted_index = {}       # word -> set[doc_id]
        self._risk_inverted_index = {}  # word -> set[doc_id]
        self._load_data()
        self._build_index()

    def _load_data(self):
        with open(os.path.join(DATA_DIR, "provisions.json"), "r", encoding="utf-8") as f:
            data = json.load(f)
            self.provisions = data.get("provisions", [])
        for p in self.provisions:
            for keyword in p.get("keywords", []):
                if isinstance(keyword, str) and len(keyword.strip()) >= 2:
                    jieba.add_word(keyword.strip())

        with open(os.path.join(DATA_DIR, "contract_risks.json"), "r", encoding="utf-8") as f:
            data = json.load(f)
            self.risk_patterns = data.get("risk_patterns", [])

    def _build_index(self):
        # 分词 + 建倒排索引
        for idx, p in enumerate(self.provisions):
            text = p["law_name"] + " " + p["article"] + " " + p["content"] + " " + " ".join(p.get("keywords", []))
            tokens = list(jieba.cut(text))
            self._provision_tokens.append(tokens)
            for token in set(tokens):
                if token not in self._inverted_index:
                    self._inverted_index[token] = set()
                self._inverted_index[token].add(idx)

        for idx, r in enumerate(self.risk_patterns):
            text = r["risk_type"] + " " + r["keywords"]
            tokens = list(jieba.cut(text))
            self._risk_tokens.append(tokens)
            for token in set(tokens):
                if token not in self._risk_inverted_index:
                    self._risk_inverted_index[token] = set()
                self._risk_inverted_index[token].add(idx)

        if self._provision_tokens:
            self.bm25 = BM25Okapi(self._provision_tokens)
        if self._risk_tokens:
            self.risk_bm25 = BM25Okapi(self._risk_tokens)

    def _get_candidates(self, query_tokens, inverted_index, corpus_size):
        """通过倒排索引获取候选文档ID集合"""
        candidates = set()
        for token in query_tokens:
            if token in inverted_index:
                candidates.update(inverted_index[token])
        # 没有候选时退回全量扫描
        if not candidates:
            return list(range(corpus_size))
        return list(candidates)

    def search_provisions(self, query: str, top_k: int = 8) -> list[dict]:
        """检索相关法律法规 — 倒排索引候选 + 关键词优先 + BM25 辅助排序"""
        if not self.provisions or self.bm25 is None:
            return self.provisions[:top_k]

        query_tokens = list(jieba.cut(query))
        meaningful_tokens = [
            t for t in query_tokens
            if len(t.strip()) >= 2 and t.strip() not in GENERIC_QUERY_TERMS
        ]
        if not meaningful_tokens:
            return []
        query_words = set(meaningful_tokens)

        # 倒排索引取候选。法条检索不做全量兜底，避免泛词把无关法条推上来。
        candidate_set = set()
        for token in meaningful_tokens:
            if token in self._inverted_index:
                candidate_set.update(self._inverted_index[token])
        if not candidate_set:
            return []
        candidates = list(candidate_set)

        scenario_terms = []
        for term, aliases in SCENARIO_CONTEXT_TERMS.items():
            if term in query:
                scenario_terms.extend(aliases)
        if scenario_terms:
            scenario_filtered = []
            for idx in candidates:
                p = self.provisions[idx]
                doc_text = (
                    p.get("law_name", "") + " " +
                    p.get("article", "") + " " +
                    p.get("content", "") + " " +
                    " ".join(p.get("keywords", []))
                )
                if any(term in doc_text for term in scenario_terms):
                    scenario_filtered.append(idx)
            if scenario_filtered:
                candidates = scenario_filtered

        # 用候选子集计算 BM25
        if len(candidates) < len(self.provisions):
            bm25_scores = self.bm25.get_batch_scores(meaningful_tokens, candidates)
        else:
            bm25_scores = self.bm25.get_scores(meaningful_tokens)

        # 关键词优先：有关键词命中的排前面，纯文本匹配排后面
        keyword_matched = []
        text_only = []

        for pos, idx in enumerate(candidates):
            p = self.provisions[idx]
            kw_set = set(p.get("keywords", []))

            # 精确匹配
            exact_weight = 0.0
            for qt in query_words:
                if qt in kw_set:
                    exact_weight += 0.15 if len(qt) < 3 else 0.5

            # 部分匹配（>= 2 字词即可参与，但 2 字词权重较低避免误匹配）
            partial_weight = 0.0
            matched_kw = set()
            matched_query_terms = set()
            for qt in query_words:
                if len(qt) < 2:
                    continue
                if qt in matched_query_terms:
                    continue
                for kw in kw_set:
                    if kw in matched_kw:
                        continue
                    if qt != kw and (qt in kw or kw in qt):
                        partial_weight += 0.15 if len(qt) < 3 else 0.3
                        matched_kw.add(kw)
                        matched_query_terms.add(qt)
                        break

            kw_score = exact_weight + partial_weight
            bm25 = float(bm25_scores[pos])

            if kw_score > 0:
                score = kw_score + min(bm25 / 5.0, 0.5)
                keyword_matched.append((idx, score))
            elif bm25 > 0.5:
                score = min(bm25 / 8.0, 0.35)
                text_only.append((idx, score))

        keyword_matched.sort(key=lambda x: x[1], reverse=True)
        text_only.sort(key=lambda x: x[1], reverse=True)

        ranked = keyword_matched[:top_k]
        remaining = top_k - len(ranked)
        if remaining > 0:
            ranked.extend(text_only[:remaining])

        results = []
        for idx, score in ranked:
            if score >= MIN_PROVISION_RELEVANCE:
                item = dict(self.provisions[idx])
                item["relevance"] = round(min(float(score), 1.0), 3)
                results.append(item)
        return results

    def search_risk_patterns(self, query: str, top_k: int = 8) -> list[dict]:
        """检索合同风险模式 — 倒排索引候选 + BM25"""
        if not self.risk_patterns or self.risk_bm25 is None:
            return self.risk_patterns[:top_k]

        query_tokens = list(jieba.cut(query))
        candidates = self._get_candidates(query_tokens, self._risk_inverted_index, len(self.risk_patterns))

        if len(candidates) < len(self.risk_patterns):
            scores = self.risk_bm25.get_batch_scores(query_tokens, candidates)
        else:
            scores = self.risk_bm25.get_scores(query_tokens)

        ranked = sorted(
            enumerate(scores),
            key=lambda x: x[1],
            reverse=True
        )[:top_k]

        results = []
        for pos, score in ranked:
            if score >= 0.5:
                idx = candidates[pos]
                item = dict(self.risk_patterns[idx])
                item["relevance"] = round(float(score), 3)
                results.append(item)
        return results

    def get_all_provisions_text(self) -> str:
        lines = []
        for i, p in enumerate(self.provisions, 1):
            lines.append(f"{i}. {p['law_name']}{p['article']}: {p['content'][:100]}")
        return "\n".join(lines)

    def get_all_risks_text(self) -> str:
        lines = []
        for i, r in enumerate(self.risk_patterns, 1):
            lines.append(f"{i}. [{r['risk_type']}] {r['pattern'][:150]}")
        return "\n".join(lines)


_kb_instance = None


def get_kb() -> LegalKnowledgeBase:
    global _kb_instance
    if _kb_instance is None:
        _kb_instance = LegalKnowledgeBase()
    return _kb_instance
