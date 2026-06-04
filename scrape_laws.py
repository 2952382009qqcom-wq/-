"""从 flk.npc.gov.cn 抓取法律法规条文"""
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

# 需要抓取的法律列表
LAW_LIST = [
    "中华人民共和国民法典",
    "中华人民共和国刑法",
    "中华人民共和国民事诉讼法",
    "中华人民共和国刑事诉讼法",
    "中华人民共和国行政诉讼法",
    "中华人民共和国公司法",
    "中华人民共和国劳动合同法",
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
    "中华人民共和国劳动法",
    "中华人民共和国仲裁法",
    "中华人民共和国担保法",
    "中华人民共和国物权法",
    "中华人民共和国合同法",
    "中华人民共和国侵权责任法",
    "中华人民共和国婚姻法",
    "中华人民共和国继承法",
]


def search_law(name, page_num=1, page_size=20):
    """搜索法律"""
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
        "pageNum": page_num,
        "pageSize": page_size,
    }
    try:
        r = requests.post(SEARCH_URL, json=body, headers=HEADERS, timeout=20)
        data = r.json()
        if data.get("code") == 500:
            print(f"  搜索 '{name}' 失败: {data.get('msg')}")
            return None
        return data
    except Exception as e:
        print(f"  搜索 '{name}' 异常: {e}")
        return None


def get_law_detail(flfg_id):
    """获取法律法规详情（包括法条内容）"""
    body = {"flfgId": flfg_id, "searchType": 2}
    try:
        r = requests.post(DETAIL_URL, json=body, headers=HEADERS, timeout=30)
        data = r.json()
        return data
    except Exception as e:
        print(f"  获取详情 '{flfg_id}' 异常: {e}")
        return None


def extract_provisions(law_detail):
    """从法律详情中提取法条"""
    provisions = []
    if not law_detail:
        return provisions

    data = law_detail.get("data") or law_detail.get("result")
    if not data:
        return provisions

    law_name = data.get("title") or data.get("flfgName") or ""
    law_info_keys = ["title", "flfgName", "publishDate", "effectiveDate", "lawCode"]

    # 提取法条 - 多种可能的数据结构
    articles = data.get("articles") or data.get("fltks") or data.get("provisions") or []
    if isinstance(articles, list):
        for art in articles:
            if isinstance(art, dict):
                article_num = art.get("article") or art.get("tiao") or art.get("name") or ""
                content = art.get("content") or art.get("text") or art.get("zw") or ""
                if content.strip():
                    provisions.append({
                        "law_name": law_name,
                        "article": article_num,
                        "content": content.strip(),
                        "keywords": [],
                    })
    return provisions


def print_json_structure(obj, prefix="", max_depth=4, depth=0):
    """递归打印JSON结构（帮助理解API返回格式）"""
    if depth >= max_depth:
        return
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, str):
                print(f"{prefix}{k}: str (len={len(v)}) {v[:100]}")
            elif isinstance(v, list):
                print(f"{prefix}{k}: list (len={len(v)})")
            elif isinstance(v, int):
                print(f"{prefix}{k}: int = {v}")
            elif isinstance(v, dict):
                print(f"{prefix}{k}: dict")
                print_json_structure(v, prefix + "  ", max_depth, depth + 1)
            elif v is None:
                print(f"{prefix}{k}: None")
            else:
                print(f"{prefix}{k}: {type(v).__name__}")
    elif isinstance(obj, list) and len(obj) > 0:
        print(f"{prefix}[0]: {type(obj[0]).__name__}")
        if isinstance(obj[0], dict):
            print_json_structure(obj[0], prefix + "  ", max_depth, depth + 1)


def main():
    all_provisions = []

    # 第一步：测试搜索和详情接口
    print("=" * 60)
    print("测试：搜索 '民法典'")
    print("=" * 60)

    result = search_law("民法典")
    if not result:
        print("搜索失败，退出")
        return

    print("搜索响应结构：")
    print(f"  code: {result.get('code')}")
    result_data = result.get("data") or result.get("result") or {}
    if isinstance(result_data, dict):
        print(f"  顶层 keys: {list(result_data.keys())}")
        # 看列表结构
        list_key = None
        for key in ["records", "list", "data", "rows", "flfgs"]:
            if key in result_data:
                list_key = key
                break
        if list_key:
            records = result_data[list_key]
            print(f"  {list_key}: list len={len(records)}")
            if records:
                print(f"  第一条 keys: {list(records[0].keys())}")
                print(f"  第一条 (部分): {json.dumps(records[0], ensure_ascii=False)[:500]}")
        else:
            print(f"  未找到列表字段，完整结构:")
            print_json_structure(result_data)

    # 保存原始响应
    with open(os.path.join(DATA_DIR, "api_search_response.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print("\n搜索响应已保存到 data/api_search_response.json")

    # 第二步：测试详情接口
    print("\n" + "=" * 60)
    print("测试：获取法律详情")
    print("=" * 60)

    result_data = result.get("data") or result.get("result") or {}
    records = result_data.get("records") or result_data.get("list") or result_data.get("data") or []
    if records:
        first = records[0]
        flfg_id = first.get("id") or first.get("flfgId") or first.get("lawId") or first.get("flfgCodeId")
        print(f"法律 ID: {flfg_id}")
        detail = get_law_detail(flfg_id)
        if detail:
            with open(os.path.join(DATA_DIR, "api_detail_response.json"), "w", encoding="utf-8") as f:
                json.dump(detail, f, ensure_ascii=False, indent=2)
            print("详情响应已保存到 data/api_detail_response.json")
            print("详情响应结构:")
            print_json_structure(detail)
        else:
            print("获取详情失败")


if __name__ == "__main__":
    main()
