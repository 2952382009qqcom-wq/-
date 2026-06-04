"""用 Playwright 从 flk.npc.gov.cn 抓取法律条文 v5 — 页面交互提取"""
import json
import os
import time
from playwright.sync_api import sync_playwright

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
MINFADIAN_BBBS = "ff808081729d1efe01729d50b5c500bf"


def main():
    api_responses = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            locale="zh-CN",
        )
        page = context.new_page()

        # 监听所有 response
        def on_response(resp):
            url = resp.url
            if "/law-search/" in url:
                try:
                    body = resp.text()
                    if len(body) < 50000:  # skip huge responses
                        api_responses.append({"url": url, "status": resp.status, "body": body})
                except Exception:
                    pass
        page.on("response", on_response)

        # 访问详情页
        print("1. 访问民法典详情页...")
        page.goto(f"https://flk.npc.gov.cn/detail?bbbs={MINFADIAN_BBBS}", wait_until="networkidle", timeout=60000)
        time.sleep(5)

        print(f"   URL: {page.url}")
        print(f"   Title: {page.title()}")

        # 等待页面内容加载
        try:
            page.wait_for_selector(".el-table, .detail-content, .law-content, table, .article-content, .fl-content", timeout=10000)
            print("   页面内容已加载")
        except Exception:
            print("   等待超时，但继续...")

        # 获取页面文本
        text = page.inner_text("body")
        print(f"   页面文本长度: {len(text)}")
        print(f"   前300字: {text[:300]}")

        page.screenshot(path=os.path.join(DATA_DIR, "v5_detail.png"), full_page=True)

        # 提取所有可见文本元素
        for sel in [".el-table__body tr", "table tbody tr", ".tree-node", ".el-tree-node__content"]:
            count = page.locator(sel).count()
            if count > 0:
                print(f"   {sel}: {count} 个")
                first = page.locator(sel).first
                txt = first.inner_text()
                print(f"      第一个文本: {txt[:200]}")

        # 保存HTML
        html = page.content()
        with open(os.path.join(DATA_DIR, "v5_detail.html"), "w", encoding="utf-8") as f:
            f.write(html[:200000])

        # 尝试点击树节点展开
        print("\n2. 尝试展开树节点...")
        tree_nodes = page.locator(".el-tree-node__content, .el-tree-node__expand-icon, .tree-node-content")
        count = tree_nodes.count()
        print(f"   找到 {count} 个树节点")

        for i in range(min(count, 5)):
            try:
                node = tree_nodes.nth(i)
                text = node.inner_text()
                print(f"   节点 {i}: {text[:100]}")

                # 找展开图标
                expand_icon = node.locator(".el-tree-node__expand-icon, .el-icon-caret-right, [class*='expand']")
                if expand_icon.count() > 0:
                    expand_icon.click()
                    time.sleep(1)
            except Exception as e:
                print(f"   节点 {i} 失败: {e}")

        time.sleep(3)
        page.screenshot(path=os.path.join(DATA_DIR, "v5_expanded.png"), full_page=True)

        # 打印API响应
        print(f"\n3. API响应 ({len(api_responses)}个):")
        for r in api_responses:
            print(f"   [{r['status']}] {r['url'][:120]}")
            try:
                data = json.loads(r['body'])
                code = data.get('code', 'no-code')
                print(f"      code={code}")
            except Exception:
                print(f"      body: {r['body'][:100]}")

        browser.close()


if __name__ == "__main__":
    main()
