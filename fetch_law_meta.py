"""从 flk.npc.gov.cn 批量抓取法律元数据（名称、日期、法条结构）"""
import json
import os
import time
import requests

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

SEARCH_URL = "https://flk.npc.gov.cn/law-search/search/list"
DETAIL_URL = "https://flk.npc.gov.cn/law-search/search/flfgDetails"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Content-Type": "application/json;charset=UTF-8",
    "Accept": "application/json",
    "Origin": "https://flk.npc.gov.cn",
    "Referer": "https://flk.npc.gov.cn/search",
}

LAWS = [
    "中华人民共和国民法典",
    "中华人民共和国刑法",
    "中华人民共和国民事诉讼法",
    "中华人民共和国刑事诉讼法",
    "中华人民共和国行政诉讼法",
    "中华人民共和国公司法",
    "中华人民共和国劳动合同法",
    "中华人民共和国劳动法",
    "中华人民共和国消费者权益保护法",
    "中华人民共和国个人信息保护法",
    "中华人民共和国反不正当竞争法",
    "中华人民共和国商标法",
    "中华人民共和国专利法",
    "中华人民共和国著作权法",
    "中华人民共和国证券法",
    "中华人民共和国企业破产法",
    "中华人民共和国行政处罚法",
    "中华人民共和国行政复议法",
    "中华人民共和国数据安全法",
    "中华人民共和国网络安全法",
    "中华人民共和国电子商务法",
    "中华人民共和国反垄断法",
    "中华人民共和国仲裁法",
    "中华人民共和国外商投资法",
    "中华人民共和国出口管制法",
]


def search_law(name):
    body = {
        "searchRange": 1,
        "sxrq": [],
        "gbrq": [],
        "searchType": 2,
        "sxx": [],
        "gbrqYear": [],
        "flfgCodeId": [],
        "zdjgCodeId": [],
        "searchContent": name,
        "orderByParam": {"order": "-1", "sort": ""},
        "pageNum": 1,
        "pageSize": 5,
    }
    r = requests.post(SEARCH_URL, json=body, headers=HEADERS, timeout=20)
    data = r.json()
    if data.get("code") == 200:
        rows = data.get("rows", [])
        # 过滤：只保留完全匹配的（sxx=3 是现行有效）
        exact = [row for row in rows if row.get("flxz") == "法律" and row.get("sxx") == 3]
        if not exact:
            # fallback: any law type
            exact = [row for row in rows if row.get("sxx") == 3]
        return exact[0] if exact else (rows[0] if rows else None)
    return None


def get_law_detail(bbbs):
    r = requests.get(f"{DETAIL_URL}?bbbs={bbbs}", headers=HEADERS, timeout=30)
    data = r.json()
    if data.get("code") == 200:
        return data.get("data")
    return None


def extract_articles(node, articles=None, path=""):
    """从树形结构中提取所有叶子节点（法条）"""
    if articles is None:
        articles = []
    title = node.get("title", "")
    children = node.get("children", [])
    new_path = f"{path}/{title}" if path else title

    if not children:
        # 找到法条（叶子节点，标题包含"第"和"条"）
        articles.append({
            "article": title,
            "path": new_path,
            "article_id": node.get("id"),
        })
    else:
        for child in children:
            extract_articles(child, articles, new_path)
    return articles


def main():
    all_meta = []

    for i, law_name in enumerate(LAWS):
        print(f"[{i+1}/{len(LAWS)}] {law_name} ...")

        try:
            # 搜索法律
            result = search_law(law_name)
            if not result:
                print(f"  -> 未找到")
                continue

            bbbs = result.get("bbbs")
            title = result.get("title", "").replace("<em class='highlight'>", "").replace("</em>", "")
            gbrq = result.get("gbrq", "")  # 公布日期
            sxrq = result.get("sxrq", "")  # 施行日期
            zdjg = result.get("zdjgName", "")
            print(f"  -> 找到: {title} bbbs={bbbs} 施行={sxrq}")

            # 获取详情（法条结构）
            article_count = 0
            if bbbs:
                detail = get_law_detail(bbbs)
                if detail:
                    content_tree = detail.get("content")
                    if content_tree:
                        articles = extract_articles(content_tree)
                        article_count = len(articles)
                        print(f"     法条数: {article_count}")
                else:
                    print(f"     详情获取失败")
            else:
                print(f"     无 bbbs")

            all_meta.append({
                "law_name": title,
                "bbbs": bbbs,
                "publish_date": gbrq,
                "effective_date": sxrq,
                "issuing_body": zdjg,
                "article_count": article_count,
            })

            time.sleep(0.5)  # 礼貌间隔

        except Exception as e:
            print(f"  -> 异常: {e}")

    # 保存元数据
    meta_path = os.path.join(DATA_DIR, "law_metadata.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(all_meta, f, ensure_ascii=False, indent=2)
    print(f"\n已保存 {len(all_meta)} 部法律元数据到 {meta_path}")


if __name__ == "__main__":
    main()
