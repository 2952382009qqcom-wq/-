"""生成明鉴项目书 - Word 文档"""
from docx import Document
from docx.shared import Inches, Pt, Cm, RGBColor, Emu
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.section import WD_ORIENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import os

doc = Document()

# ===== 页面设置 =====
for section in doc.sections:
    section.orientation = WD_ORIENT.PORTRAIT
    section.page_width = Cm(21)
    section.page_height = Cm(29.7)
    section.top_margin = Cm(2.5)
    section.bottom_margin = Cm(2.5)
    section.left_margin = Cm(2.5)
    section.right_margin = Cm(2.5)

# ===== 样式定义 =====
style = doc.styles['Normal']
style.font.name = '宋体'
style.font.size = Pt(12)
style.paragraph_format.line_spacing = 1.5
style.font.color.rgb = RGBColor(0x1A, 0x1A, 0x1A)
r = style.element.rPr
if r is None:
    r = OxmlElement('w:rPr')
    style.element.append(r)
rFonts = OxmlElement('w:rFonts')
rFonts.set(qn('w:eastAsia'), '宋体')
r.append(rFonts)

def add_title(doc, text):
    """文档主标题"""
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(40)
    p.paragraph_format.space_after = Pt(20)
    run = p.add_run(text)
    run.font.size = Pt(28)
    run.font.bold = True
    run.font.color.rgb = RGBColor(0x0D, 0x1B, 0x2A)
    run.font.name = '黑体'
    rPr = run._element.rPr
    rFonts = OxmlElement('w:rFonts')
    rFonts.set(qn('w:eastAsia'), '黑体')
    rPr.append(rFonts)

def add_subtitle(doc, text):
    """副标题"""
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(30)
    run = p.add_run(text)
    run.font.size = Pt(14)
    run.font.color.rgb = RGBColor(0x6B, 0x6B, 0x6B)
    run.font.name = '宋体'

def add_h1(doc, text):
    """一级标题"""
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(24)
    p.paragraph_format.space_after = Pt(12)
    run = p.add_run(text)
    run.font.size = Pt(18)
    run.font.bold = True
    run.font.color.rgb = RGBColor(0x0D, 0x1B, 0x2A)
    run.font.name = '黑体'
    rPr = run._element.rPr
    rFonts = OxmlElement('w:rFonts')
    rFonts.set(qn('w:eastAsia'), '黑体')
    rPr.append(rFonts)

def add_h2(doc, text):
    """二级标题"""
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(16)
    p.paragraph_format.space_after = Pt(8)
    run = p.add_run(text)
    run.font.size = Pt(15)
    run.font.bold = True
    run.font.color.rgb = RGBColor(0x1B, 0x2A, 0x4A)
    run.font.name = '黑体'
    rPr = run._element.rPr
    rFonts = OxmlElement('w:rFonts')
    rFonts.set(qn('w:eastAsia'), '黑体')
    rPr.append(rFonts)

def add_h3(doc, text):
    """三级标题"""
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(12)
    p.paragraph_format.space_after = Pt(6)
    run = p.add_run(text)
    run.font.size = Pt(13)
    run.font.bold = True
    run.font.color.rgb = RGBColor(0x33, 0x33, 0x33)
    run.font.name = '楷体'
    rPr = run._element.rPr
    rFonts = OxmlElement('w:rFonts')
    rFonts.set(qn('w:eastAsia'), '楷体')
    rPr.append(rFonts)

def add_body(doc, text, indent=True):
    """正文段落"""
    p = doc.add_paragraph()
    p.paragraph_format.first_line_indent = Cm(0.74) if indent else Cm(0)
    p.paragraph_format.line_spacing = 1.5
    run = p.add_run(text)
    run.font.size = Pt(12)
    run.font.name = '宋体'
    rPr = run._element.rPr
    rFonts = OxmlElement('w:rFonts')
    rFonts.set(qn('w:eastAsia'), '宋体')
    rPr.append(rFonts)

def add_bullet(doc, text, level=0):
    """项目符号"""
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Cm(0.74 + level * 0.74)
    p.paragraph_format.line_spacing = 1.5
    prefix = "● " if level == 0 else "○ " if level == 1 else "▪ "
    run = p.add_run(prefix + text)
    run.font.size = Pt(12)
    run.font.name = '宋体'
    rPr = run._element.rPr
    rFonts = OxmlElement('w:rFonts')
    rFonts.set(qn('w:eastAsia'), '宋体')
    rPr.append(rFonts)

def add_table_from_data(doc, headers, rows):
    """添加表格"""
    table = doc.add_table(rows=len(rows) + 1, cols=len(headers))
    table.style = 'Table Grid'
    # Header
    for i, h in enumerate(headers):
        cell = table.rows[0].cells[i]
        cell.text = ''
        p = cell.paragraphs[0]
        run = p.add_run(h)
        run.font.size = Pt(11)
        run.font.bold = True
        run.font.name = '宋体'
        rPr = run._element.rPr
        rFonts = OxmlElement('w:rFonts')
        rFonts.set(qn('w:eastAsia'), '宋体')
        rPr.append(rFonts)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        # 灰色背景
        shading = OxmlElement('w:shd')
        shading.set(qn('w:fill'), '1B2A4A')
        shading.set(qn('w:val'), 'clear')
        cell._element.get_or_add_tcPr().append(shading)
        run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

    # Data rows
    for r, row in enumerate(rows):
        for c, val in enumerate(row):
            cell = table.rows[r + 1].cells[c]
            cell.text = ''
            p = cell.paragraphs[0]
            run = p.add_run(str(val))
            run.font.size = Pt(10)
            run.font.name = '宋体'
            rPr = run._element.rPr
            rFonts = OxmlElement('w:rFonts')
            rFonts.set(qn('w:eastAsia'), '宋体')
            rPr.append(rFonts)
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER

    doc.add_paragraph()  # 表后空行


# ============================================================
# 封面
# ============================================================
add_title(doc, "明  鉴")
add_subtitle(doc, "AI 法律文书智能助手")
add_subtitle(doc, "")

# 项目信息
info_items = [
    ("项目名称", "明鉴 — AI 法律文书智能助手"),
    ("参赛赛道", "高教主赛道"),
    ("项目方向", "AI + 法律科技"),
    ("所属学校", "北京科技大学天津学院"),
]
for label, value in info_items:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(4)
    run = p.add_run(f"{label}：{value}")
    run.font.size = Pt(12)
    run.font.color.rgb = RGBColor(0x33, 0x33, 0x33)
    run.font.name = '宋体'

doc.add_page_break()

# ============================================================
# 目录页
# ============================================================
add_h1(doc, "目  录")
add_body(doc, "")
toc = [
    "一、项目概述",
    "二、项目背景与痛点分析",
    "三、产品功能介绍",
    "四、核心技术方案",
    "五、创新点与竞争优势",
    "六、市场分析",
    "七、商业模式",
    "八、团队介绍",
    "九、发展规划",
    "十、社会价值",
]
for item in toc:
    add_body(doc, item, indent=False)
doc.add_page_break()

# ============================================================
# 一、项目概述
# ============================================================
add_h1(doc, "一、项目概述")

add_h2(doc, "1.1 项目简介")
add_body(doc, "明鉴是一款基于大语言模型（LLM）的 AI 法律文书智能助手，致力于利用人工智能技术降低法律服务门槛，让普通民众能够以接近零成本获得专业级的法律文书分析、法规检索、合同审查、文书生成和案情策略分析服务。")
add_body(doc, "项目采用 BM25 + 关键词混合检索算法替代传统 TF-IDF 方案，构建了覆盖 349 条法律法规的中文法律知识库（涵盖 42 部核心法律/法规，含 2024-2026 年最新立法），结合流式 LLM 响应架构与结构化表单交互设计，实现了高效、精准、易用的法律 AI 辅助系统。")
add_body(doc, "目前项目已完成全部 5 大核心功能模块的开发与部署，运行于阿里云服务器，具备完整的用户认证、知识库检索、AI 生成与 PDF 输出能力。")

add_h2(doc, "1.2 核心数据")
add_body(doc, "本地法律知识库：349 条法律法规，覆盖 42 部法律/法规", indent=False)
add_body(doc, "核心功能模块：5 个（文书分析、法规检索、合同审查、文书生成、策略分析）", indent=False)
add_body(doc, "关键技术栈：Flask + Python 3.8 + jieba + BM25 + LLM API + fpdf2", indent=False)
add_body(doc, "部署状态：已部署于阿里云 ECS 服务器，支持流式响应", indent=False)

add_h2(doc, "1.3 项目定位")
add_body(doc, "本项目的核心定位是"AI + 法律科技"领域的创新应用，瞄准法律服务供给与公众法律需求之间的结构性矛盾。不同于传统的法律数据库检索工具或律所 SAAS 软件，明鉴强调以下三个定位维度：")
add_bullet(doc, "普惠性：以免费/低成本模式面向普通公众，降低法律服务使用门槛")
add_bullet(doc, "智能性：以大语言模型为核心引擎，实现法律文书的自动生成与智能分析")
add_bullet(doc, "实用性：覆盖老百姓最常见的法律需求场景（借钱不还、合同纠纷、劳动维权等）")

doc.add_page_break()

# ============================================================
# 二、项目背景与痛点分析
# ============================================================
add_h1(doc, "二、项目背景与痛点分析")

add_h2(doc, "2.1 社会背景")
add_body(doc, "随着中国法治建设不断深入，公众的法律意识显著增强，法律服务需求呈现爆发式增长。2025 年中国法律服务市场规模已突破 6000 亿元，预计 2026 年将达到 6500 亿元。然而，法律服务资源分布极不均衡——律师资源高度集中在北上广深等一线城市，广大基层地区和农村面临严重的法律服务供给不足。")

add_body(doc, "与此同时，人工智能技术近年来取得了突破性进展，以 GPT、GLM 为代表的大语言模型在文本理解、生成、推理等方面展现出强大能力，为法律服务的智能化、普惠化提供了技术基础。AI + 法律科技的深度融合，是解决法律服务供需矛盾的重要突破口。")

add_h2(doc, "2.2 三大核心痛点")
add_h3(doc, "痛点一：高昂的法律服务成本")
add_body(doc, "普通公众难以负担专业律师的咨询费用，一次法律咨询动辄数百至数千元。对于小额民间借贷、劳动纠纷等常见法律问题，许多当事人因为法律服务成本过高而放弃维权，导致合法权益受损。中小企业同样面临法律顾问费用高昂的困境。")

add_h3(doc, "痛点二：法律文书门槛极高")
add_body(doc, "法律文书的格式规范严格、术语复杂，普通公众无法独立撰写起诉状、答辩状、合同等规范文书。即使有参考模板，如何准确填写法律事实、引用法律条文、组织诉讼逻辑，对非专业人士来说仍然是巨大的挑战。")

add_h3(doc, "痛点三：传统办案效率低下")
add_body(doc, "律师和法律工作者需要手动检索相关法律法规、逐条审查合同条款。同类案件缺乏系统化的策略参考和类案分析工具支持。法律法规更新频繁，个人难以持续跟进最新的立法动态。")

add_h2(doc, "2.3 现有解决方案的不足")
add_body(doc, "当前市场上的法律科技产品主要存在以下不足：传统法律数据库（如北大法宝、元典智库）以关键词检索为主，缺乏语义理解能力；法律 AI 产品多数面向 B 端律所，价格高昂，不面向普通公众；通用 AI 助手（如 ChatGPT）缺乏中文法律领域的专业知识，法条引用常出现错误。")

doc.add_page_break()

# ============================================================
# 三、产品功能介绍
# ============================================================
add_h1(doc, "三、产品功能介绍")

add_h2(doc, "3.1 法律文书智能分析")
add_body(doc, "用户上传判决书、合同、起诉状等法律文书后，AI 自动识别文书类型、提取当事人信息，标注关键条款并评估风险等级（高/中/低），提供具体的修订建议和法律依据。该模块适用于当事人了解手中法律文书的潜在风险，也可帮助律师快速梳理案件材料。")

add_h2(doc, "3.2 法律法规智能检索")
add_body(doc, "用户以自然语言方式提问（如"加班是否合法""劳动合同到期不续签有补偿吗"），系统通过 BM25 + 关键词混合检索算法，在 349 条法律法规知识库中精准匹配相关法条，返回法条全文、法律分析和实务建议。该模块是本项目的技术核心之一，经历了从 TF-IDF V1.0 到 BM25+关键词优先排序 V3.0 的多次迭代优化，检索准确率大幅提升。")

add_h2(doc, "3.3 合同风险智能审查")
add_body(doc, "用户上传合同文件（支持 .txt / .docx 格式），系统自动逐条审查合同条款，标注风险条款和风险等级（高/中/低），提供具体修改建议和对应法条依据，生成综合风险评估报告。系统内置合同风险模式库，覆盖违约责任不对等、争议解决管辖不利、缺失必备条款等常见合同风险类型。")

add_h2(doc, "3.4 法律文书智能生成")
add_body(doc, "本模块采用创新的结构化表单式输入设计——用户无需面对一个巨大的文本框感到无从下手，而是按"当事人信息""事情经过""核心诉求"等分字段填写，像做填空题一样简单。AI 根据用户输入自动生成规范的法律文书，支持起诉状、答辩状、上诉状、律师函、合同、仲裁申请书共 6 种文书类型，并支持专业格式的 PDF 下载（含中文首行缩进、节标题加粗、落款右对齐等排版优化）。")

add_h2(doc, "3.5 案情策略分析")
add_body(doc, "用户填写"当事人""事情经过""争议焦点""当前进展"四个结构化字段后，系统自动匹配适用法律法规，生成综合诉讼策略分析，包括：案件类型与案由判定、主攻策略与备选策略、调解/和解建议、关键证据指引与证据风险提示、管辖分析与诉讼时效评估、类案参考与下一步行动建议。")

doc.add_page_break()

# ============================================================
# 四、核心技术方案
# ============================================================
add_h1(doc, "四、核心技术方案")

add_h2(doc, "4.1 系统架构")
add_body(doc, "明鉴采用经典的四层 Web 应用架构：")
add_bullet(doc, "展示层：HTML5 + CSS3 + JavaScript（原生），响应式 UI 设计，SSE 流式输出")
add_bullet(doc, "API 层：Flask Web 框架 + Flask-Login 用户认证 + Flask-CORS 跨域支持")
add_bullet(doc, "核心层：BM25 检索算法 + jieba 中文分词 + fpdf2 PDF 生成 + Prompt 工程")
add_bullet(doc, "数据层：SQLite 数据库（用户、操作记录）+ JSON 知识库（349 法条、合同风险模式）")

add_h2(doc, "4.2 BM25 + 关键词混合检索算法（核心技术）")
add_body(doc, "法律文本检索是本项目的核心技术挑战。传统 TF-IDF 算法在面对中文法律文本时存在严重缺陷——常见法律术语（如"是否合法""当事人"等）在大量法条中重复出现，导致检索结果与用户查询主题无关。本项目经历了三个迭代版本：")

add_h3(doc, "V1.0：TF-IDF + 余弦相似度")
add_body(doc, "基础方案，存在常见法律术语干扰严重、短查询匹配效果差等问题。例如查询"加班是否合法"，排名第一的是《行政诉讼法》第 6 条（因为"是否合法"一词匹配），而非《劳动法》中的加班规定。")

add_h3(doc, "V2.0：BM25 + 关键词加权")
add_body(doc, "引入领域关键词匹配，每个关键词命中追加 0.08 权重加分。相比 V1.0 有所改善，但关键词权重过低（仅 0.08），无法有效对抗 BM25 文本相似度的噪声信号。")

add_h3(doc, "V3.0：BM25 + 分权重关键词优先排序（当前版本）")
add_body(doc, "核心创新——关键词优先的排序策略：")
add_bullet(doc, "精确匹配分权重：2 字词 0.15 / 3 字及以上 0.5（避免"补偿""合法"等常见 2 字词过度匹配）")
add_bullet(doc, "部分匹配权重：3 字及以上查询词与关键词互为子串时，追加 0.3 权重")
add_bullet(doc, "双通道排序：关键词命中组优先展示（评分 0.5-1.0），纯文本 BM25 匹配降级处理（上限 0.35）")
add_bullet(doc, "阈值过滤：综合评分低于 0.35 的结果不予展示，避免输出低相关度法条")
add_body(doc, "该算法在测试中表现优异——"加班是否合法"查询正确返回《劳动法》第 41 条，"试用期被辞退有补偿吗"查询返回《劳动合同法》第 19 条（匹配度 100%），解决了此前检索结果与查询主题无关的核心问题。")

add_h2(doc, "4.3 流式 LLM 响应架构")
add_body(doc, "系统采用 SSE（Server-Sent Events）协议实现 LLM 流式输出，用户发起请求后无需等待完整响应，生成结果实时逐字显示在页面上。相比传统的阻塞式请求（用户需等待 30-60 秒），流式架构将首次显示时间缩短至 1-2 秒，大幅改善用户体验。同时支持 OpenAI 兼容接口，可灵活切换底层模型（GPT、GLM、DeepSeek 等）。")

add_h2(doc, "4.4 中文法律 PDF 排版引擎")
add_body(doc, "基于 fpdf2 库构建了专业的中文法律文书 PDF 排版引擎，解决了普通 PDF 生成方案无法正确处理中文排版的问题：")
add_bullet(doc, "字体优化：采用文泉驿微米黑（wqy-microhei）字体，字符宽度一致，彻底消除错版问题")
add_bullet(doc, "首行缩进：使用全角空格实现两字符首行缩进，符合法律文书排版规范")
add_bullet(doc, "节标题加粗：自动识别"诉讼请求""事实与理由"等节标题并加粗显示")
add_bullet(doc, "落款右对齐：自动识别"具状人""起诉人"及日期行并右对齐排版")
add_bullet(doc, "格式补全：检测并自动补全"此致""具状人"等法律文书必备格式要素")

add_h2(doc, "4.5 法律知识库建设")
add_body(doc, "项目构建了规模化的中文法律知识库（data/provisions.json），包含 349 条法律法规，覆盖 42 部核心法律/法规。每条法条包含：法律名称、条款号、条款全文、生效日期、领域关键词。知识库涵盖 2024-2026 年最新立法动态（通过自动化爬虫从 flk.npc.gov.cn 采集），确保法律信息的时效性。配套的合同风险模式库（contract_risks.json）覆盖常见合同风险类型，为合同审查模块提供领域知识支撑。")

doc.add_page_break()

# ============================================================
# 五、创新点与竞争优势
# ============================================================
add_h1(doc, "五、创新点与竞争优势")

add_h2(doc, "5.1 算法创新：BM25 + 分权重关键词混合检索")
add_body(doc, "突破传统 TF-IDF 在中文法律文本上的准确率瓶颈，创新性地提出关键词优先排序策略：区分词长权重（2 字低权重、3 字及以上高权重），建立精确匹配与部分匹配双通道打分机制，将关键词匹配作为主信号、纯文本 BM25 作为辅助信号。该方案有效解决了"常见法律术语误导检索方向"这一行业性难题。")

add_h2(doc, "5.2 体验创新：结构化表单替代大框输入")
add_body(doc, "针对普通用户面对大文本框无从下手的痛点，将文书生成和策略分析的输入方式从"写作文"变为"做填空"——当事人信息、事情经过、核心诉求等分字段独立引导。这一设计显著降低了非专业用户的使用门槛，是本项目在用户体验层面的核心差异化优势。")

add_h2(doc, "5.3 工程创新：轻量级部署 + 流式架构")
add_body(doc, "系统不依赖 GPU 和大型深度学习框架（如 PyTorch），仅需普通云服务器即可运行。SSE 流式输出让用户感知不到 LLM 调用的延迟。PDF 排版引擎针对性解决了中文法律文书的格式痛点（首行缩进、落款对齐、格式要素自动补全）。")

add_h2(doc, "5.4 数据创新：规模化的中文法律知识库")
add_body(doc, "349 条法律法规（42 部核心法律），每条均配备领域关键词标注，支持 BM25 知识增强检索。涵盖 2024-2026 年最新立法，配套合同风险模式库。相比通用 AI 助手的"幻觉法条"问题，明鉴的输出锚定真实法律法规，具备可验证性。")

add_h2(doc, "5.5 竞品对比")
add_table_from_data(doc,
    ["产品", "检索方式", "文书生成", "面向用户", "价格", "中文法律适配"],
    [
        ["明鉴（本产品）", "BM25+关键词混合", "结构化表单+AI+PDF", "公众/律师", "免费/低成本", "★★★★★"],
        ["元典智库", "关键词检索", "无", "律师/法务", "付费", "★★★"],
        ["北大法宝", "数据库检索", "无", "律师/法务", "付费（高）", "★★★"],
        ["法狗狗", "关键词语义", "模板填空", "律所", "付费", "★★★★"],
        ["ChatGPT", "通用语义", "需手动提示", "通用", "免费/付费", "★★"],
    ]
)

doc.add_page_break()

# ============================================================
# 六、市场分析
# ============================================================
add_h1(doc, "六、市场分析")

add_h2(doc, "6.1 市场规模")
add_body(doc, "中国法律服务市场正处于快速增长期。据行业研究数据，2025 年中国法律服务市场规模已突破 6000 亿元，预计 2026 年将达到约 6500 亿元。法律科技（LegalTech）市场年复合增长率约 28.6%，但当前 AI 产品市场渗透率不足 5%，存在巨大的增量空间。")

add_body(doc, "在政策层面，国家持续推进"数字法治""智慧司法"建设。《法治中国建设规划（2020-2025 年）》明确提出推动现代科技与法治建设深度融合。《关于加快推进公共法律服务体系建设的意见》要求到 2035 年基本形成覆盖城乡、便捷高效、均等普惠的现代公共法律服务体系。本项目的定位与国家政策方向高度契合。")

add_h2(doc, "6.2 目标用户")
add_bullet(doc, "核心用户：有常见法律需求的普通公众（民间借贷、劳动纠纷、合同纠纷、婚姻家庭等）")
add_bullet(doc, "延伸用户：基层法律工作者、社区调解员、中小企业主（无专职法务）")
add_bullet(doc, "合作伙伴：高校法学院、法律援助中心、中小型律师事务所")

add_h2(doc, "6.3 市场痛点与机会")
add_body(doc, "中国法律服务市场存在显著的供需矛盾：约 4.3 亿潜在法律服务需求者，但执业律师仅约 70 万人，且 80% 以上集中在一二线城市。基层法律服务资源严重匮乏，公众"找律师难、找律师贵"的问题突出。AI 法律服务产品以近乎为零的边际复制成本，能够有效填补这一市场空白。")

doc.add_page_break()

# ============================================================
# 七、商业模式
# ============================================================
add_h1(doc, "七、商业模式")

add_h2(doc, "7.1 分层定价策略")

add_h3(doc, "基础版（免费）")
add_bullet(doc, "目标用户：普通公众")
add_bullet(doc, "功能：法律文书智能分析、基础法规检索（每日限次）、合同风险基础审查")
add_bullet(doc, "价值：公益导向，降低法律服务门槛，积累用户规模与品牌口碑")

add_h3(doc, "专业版（订阅制，预估 19-49 元/月）")
add_bullet(doc, "目标用户：高频法律需求者、基层法律工作者、中小企业")
add_bullet(doc, "功能：无限次法规检索、全部 6 种文书类型生成 + PDF 下载、深度策略分析、优先客服支持")
add_bullet(doc, "价值：以远低于律师费的价格提供专业级法律辅助服务")

add_h3(doc, "企业版（定制化，按需定价）")
add_bullet(doc, "目标用户：律师事务所、企业法务部门、法律科技平台")
add_bullet(doc, "功能：私有化部署、企业专属法律知识库、API 接口集成、定制化合同审查模板")
add_bullet(doc, "价值：为 B 端客户提供可集成的 AI 法律能力中间件")

add_h2(doc, "7.2 落地路径")
add_body(doc, "阶段一（已完成）：MVP 产品开发与云端部署，5 大核心功能模块全部完成，运行于阿里云服务器。")
add_body(doc, "阶段二（进行中）：种子用户获取——与高校法学院建立合作，邀请律所律师试用并收集反馈。通过微信公众号、法律社区论坛等渠道进行内容推广，建立早期用户社区。")
add_body(doc, "阶段三（3-6 个月）：产品迭代优化——根据种子用户反馈优化产品体验，扩充法律知识库覆盖范围至 500+ 法律法规。接入国产大模型（GLM-5.1 等）以降低 API 调用成本、提升响应速度。推出移动端 PWA 版本，覆盖手机用户。")
add_body(doc, "阶段四（6-12 个月）：规模化推广——线上通过搜索引擎优化、法律问答社区内容营销获客；线下与法律援助中心、社区调解站合作推广。企业端推动与中小律所的 SaaS 合作，提供 API 能力输出。")

doc.add_page_break()

# ============================================================
# 八、团队介绍
# ============================================================
add_h1(doc, "八、团队介绍")
add_body(doc, "（团队成员信息待补充）")
add_body(doc, "")
add_body(doc, "指导老师：", indent=False)
add_body(doc, "项目负责人：", indent=False)
add_body(doc, "团队成员：", indent=False)
add_body(doc, "")
add_body(doc, "（请填写成员姓名、专业、分工及核心能力）", indent=False)

doc.add_page_break()

# ============================================================
# 九、发展规划
# ============================================================
add_h1(doc, "九、发展规划")

add_h2(doc, "9.1 短期规划（3 个月内）")
add_bullet(doc, "接入 GLM-5.1 等国产大语言模型，降低 API 调用成本，提升中文法律场景的响应质量")
add_bullet(doc, "知识库扩充至 500+ 法律法规，增加司法解释、行政法规等子库")
add_bullet(doc, "推出移动端适配版本（PWA 方案），覆盖手机用户使用场景")
add_bullet(doc, "接入 12348 中国法律服务网接口，提供法律援助指引")
add_bullet(doc, "与 2-3 所高校法学院建立合作，获取种子用户和专业反馈")

add_h2(doc, "9.2 中期规划（6-12 个月）")
add_bullet(doc, "上线智能法律咨询对话模式，支持多轮交互式法律问题解答")
add_bullet(doc, "扩充多语言支持能力（藏语、维吾尔语等少数民族语言），服务边疆地区")
add_bullet(doc, "建立用户反馈闭环机制，将用户案例纳入知识库持续优化检索质量")
add_bullet(doc, "推出律师协作功能——用户可通过平台对接合作律师进行深度服务")
add_bullet(doc, "积累 5000+ 注册用户，形成初步的商业模式闭环")

add_h2(doc, "9.3 长期规划（1-2 年）")
add_bullet(doc, "构建开放法律 AI 平台，支持第三方开发者上传插件和工具集成")
add_bullet(doc, "开发类案推荐与司法大数据分析功能，为律师提供办案决策支持")
add_bullet(doc, "实现全法律业务流程的 AI 辅助覆盖（咨询→分析→文书→策略→执行）")
add_bullet(doc, "申请软件著作权和相关技术专利，保护核心知识产权")
add_bullet(doc, "探索与法律服务机构的深度合作模式，实现可持续发展")

doc.add_page_break()

# ============================================================
# 十、社会价值
# ============================================================
add_h1(doc, "十、社会价值")

add_h2(doc, "10.1 降低法律服务门槛，推动法律普惠")
add_body(doc, "\"法律面前人人平等\"不仅是宪法原则，更应成为技术可以推动的现实。明鉴以免费/低成本策略面向普通公众，让经济条件有限的群体也能获得基础法律服务。对于小额民间借贷、劳动报酬追索等常见纠纷，用户无需支付高昂的律师费用即可获得专业的法律文书和策略分析，有效降低了法律服务的经济门槛。")

add_h2(doc, "10.2 促进法律知识普及，增强全民法治意识")
add_body(doc, "通过自然语言检索和 AI 法条解读，帮助普通公众理解法律规定、掌握维权途径。结构化表单引导用户梳理案件事实和诉求，在"做填空"的过程中，用户也潜移默化地学习了法律文书的规范结构和法律逻辑。项目的知识库和检索结果均锚定真实法律法规，有助于公众建立对法律的正确认知。")

add_h2(doc, "10.3 助力法治中国建设，缓解法律服务资源不均")
add_body(doc, "中国法律服务资源分布严重不均——律师高度集中在发达城市，广大基层和农村地区法律服务匮乏。AI 法律服务产品不受地理限制，只要有网络就能使用，能够有效填补基层法律服务的空白。同时，为基层法律工作者（社区调解员、乡镇司法所工作人员等）提供 AI 辅助工具，提升基层法律服务的专业水平。")

add_h2(doc, "10.4 推动法律科技发展，促进产学研融合")
add_body(doc, "项目在中文法律 NLP 领域进行了有价值的探索——BM25 + 关键词混合检索方案、法律文书结构化生成方法等技术创新具有可复制、可推广的学术和应用价值。项目团队计划将核心算法和知识库构建方法论以学术论文形式公开发表，推动中文法律科技领域的学术交流和技术进步。同时，项目可作为高校法学教育与计算机科学交叉学科的实践案例，促进"法律+AI"复合型人才培养。")

doc.add_page_break()

# ============================================================
# 附录
# ============================================================
add_h1(doc, "附录")

add_h2(doc, "A. 技术架构图（文字描述）")
add_body(doc, "展示层（HTML5 + CSS3 + JavaScript）→ API 层（Flask + Flask-Login + SSE）→ 核心层（BM25 + jieba + fpdf2 + Prompt）→ 数据层（SQLite + JSON 知识库 + 349 法条 + 风险模式库）")
add_body(doc, "外部依赖：LLM API（OpenAI 兼容接口，支持 GPT/GLM/DeepSeek 等模型切换）")

add_h2(doc, "B. 核心文件清单")
add_bullet(doc, "app.py——Flask 主应用，含路由、API 端点、PDF 生成")
add_bullet(doc, "core/legal_kb.py——BM25 + 关键词混合检索算法实现")
add_bullet(doc, "core/llm_client.py——LLM API 客户端（OpenAI 兼容，支持流式）")
add_bullet(doc, "core/prompts.py——法律领域 Prompt 模板（5 个模块）")
add_bullet(doc, "data/provisions.json——349 条法律法规知识库（约 230KB）")
add_bullet(doc, "data/contract_risks.json——合同风险模式库")
add_bullet(doc, "static/js/main.js——前端交互逻辑，含流式接收与渲染")
add_bullet(doc, "templates/index.html——单页应用主模板")

add_h2(doc, "C. 技术依赖")
add_table_from_data(doc,
    ["类别", "技术/库", "用途"],
    [
        ["后端框架", "Flask 3.x", "Web 服务"],
        ["中文分词", "jieba", "查询分词与索引构建"],
        ["检索算法", "rank-bm25", "BM25 文本相似度计算"],
        ["PDF 生成", "fpdf2 2.8.3", "中文法律文书 PDF"],
        ["LLM 接口", "OpenAI SDK", "大语言模型调用"],
        ["中文字体", "wqy-microhei", "PDF 渲染（文泉驿微米黑）"],
        ["数据库", "SQLAlchemy + SQLite", "用户与操作记录存储"],
        ["部署", "Systemd + Nginx", "服务管理与反向代理"],
    ]
)

# ===== 保存 =====
output_path = "C:/Users/hh/Desktop/ChatLaw-main/明鉴_项目书.docx"
doc.save(output_path)
print(f"项目书已保存至: {output_path}")
