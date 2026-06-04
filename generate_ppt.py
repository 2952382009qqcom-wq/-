"""生成中国国际大学生创新大赛 — 明鉴项目 PPT"""

from pptx import Presentation
from pptx.util import Inches, Pt, Emu, Cm
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
import os

# ===== 配色方案 — 法律科技午夜金 =====
NAVY = RGBColor(0x0D, 0x1B, 0x2A)        # 深海军蓝（封面/结尾背景）
DARK_NAVY = RGBColor(0x08, 0x12, 0x1E)    # 更深的蓝
GOLD = RGBColor(0xC9, 0xA2, 0x34)         # 金色（强调色）
LIGHT_GOLD = RGBColor(0xE8, 0xD5, 0x8F)   # 浅金
DARK_BG = RGBColor(0x1B, 0x2A, 0x4A)      # 内容页标题栏背景
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
OFF_WHITE = RGBColor(0xF5, 0xF3, 0xEC)    # 暖白（内容页背景）
LIGHT_GRAY = RGBColor(0xE8, 0xE6, 0xE0)   # 浅灰线条
TEXT_DARK = RGBColor(0x1A, 0x1A, 0x1A)    # 正文黑
TEXT_GRAY = RGBColor(0x6B, 0x6B, 0x6B)    # 灰色文字
TEXT_MUTED = RGBColor(0x99, 0x99, 0x99)   # 更淡的灰
SLATE = RGBColor(0x5A, 0x6A, 0x7E)        # 石板蓝
CARD_BG = RGBColor(0xFF, 0xFF, 0xFF)      # 卡片白
TECH_BLUE = RGBColor(0x3B, 0x6F, 0xB6)    # 科技蓝


def add_bg(slide, color):
    """设置幻灯片背景色"""
    bg = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = color


def add_rect(slide, left, top, width, height, color, border=None):
    """添加矩形"""
    shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, left, top, width, height)
    shape.fill.solid()
    shape.fill.fore_color.rgb = color
    if border:
        shape.line.color.rgb = border
        shape.line.width = Pt(1)
    else:
        shape.line.fill.background()
    return shape


def add_text_box(slide, left, top, width, height, text, font_size=14, color=TEXT_DARK,
                 bold=False, align=PP_ALIGN.LEFT, font_name="Microsoft YaHei"):
    """添加文本框"""
    txBox = slide.shapes.add_textbox(left, top, width, height)
    tf = txBox.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = text
    p.font.size = Pt(font_size)
    p.font.color.rgb = color
    p.font.bold = bold
    p.font.name = font_name
    p.alignment = align
    return tf


def add_rich_text_box(slide, left, top, width, height):
    """返回 text_frame 用于添加富文本"""
    txBox = slide.shapes.add_textbox(left, top, width, height)
    tf = txBox.text_frame
    tf.word_wrap = True
    return tf


def add_paragraph(tf, text, font_size=14, color=TEXT_DARK, bold=False,
                  align=PP_ALIGN.LEFT, font_name="Microsoft YaHei", spacing_before=0, spacing_after=6):
    """向 text_frame 添加段落"""
    if len(tf.paragraphs) == 1 and tf.paragraphs[0].text == "":
        p = tf.paragraphs[0]
    else:
        p = tf.add_paragraph()
    p.text = text
    p.font.size = Pt(font_size)
    p.font.color.rgb = color
    p.font.bold = bold
    p.font.name = font_name
    p.alignment = align
    p.space_before = Pt(spacing_before)
    p.space_after = Pt(spacing_after)
    return p


def add_gold_bar(slide, left, top, width, height):
    """添加金色装饰条"""
    bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, left, top, width, height)
    bar.fill.solid()
    bar.fill.fore_color.rgb = GOLD
    bar.line.fill.background()
    return bar


def add_dark_slide_header(slide, title_text, subtitle_text=""):
    """内容页标题（深蓝顶栏风格）"""
    # 深蓝顶栏
    add_rect(slide, Inches(0), Inches(0), Inches(13.33), Inches(1.2), DARK_BG)
    # 金色细线
    add_gold_bar(slide, Inches(0.8), Inches(1.15), Inches(1.2), Pt(3))
    # 标题
    add_text_box(slide, Inches(0.8), Inches(0.2), Inches(11.5), Inches(0.7),
                 title_text, font_size=32, color=WHITE, bold=True)
    if subtitle_text:
        add_text_box(slide, Inches(0.8), Inches(0.72), Inches(11.5), Inches(0.4),
                     subtitle_text, font_size=13, color=LIGHT_GOLD, bold=False)
    # 浅灰底
    add_rect(slide, Inches(0), Inches(1.2), Inches(13.33), Inches(6.3), OFF_WHITE)


def add_card(slide, left, top, width, height):
    """白色卡片"""
    card = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, left, top, width, height)
    card.fill.solid()
    card.fill.fore_color.rgb = CARD_BG
    card.line.color.rgb = LIGHT_GRAY
    card.line.width = Pt(0.5)
    return card


def add_stat_card(slide, left, top, width, height, number, label):
    """大数字统计卡片"""
    card = add_card(slide, left, top, width, height)
    tf = add_rich_text_box(slide, left + Inches(0.15), top + Inches(0.15),
                           width - Inches(0.3), height - Inches(0.3))
    add_paragraph(tf, number, font_size=36, color=GOLD, bold=True, align=PP_ALIGN.CENTER)
    add_paragraph(tf, label, font_size=11, color=TEXT_GRAY, bold=False, align=PP_ALIGN.CENTER)
    return card


def add_icon_text_block(slide, left, top, width, icon_char, title, desc, icon_color=GOLD):
    """图标 + 标题 + 描述 块"""
    # 图标（用字符模拟）
    icon_box = add_rect(slide, left, top, Inches(0.45), Inches(0.45), icon_color)
    tf = add_rich_text_box(slide, left, top, Inches(0.45), Inches(0.45))
    p = tf.paragraphs[0]
    p.text = icon_char
    p.font.size = Pt(18)
    p.font.color.rgb = WHITE
    p.font.bold = True
    p.alignment = PP_ALIGN.CENTER

    add_text_box(slide, left + Inches(0.6), top, width - Inches(0.6), Inches(0.4),
                 title, font_size=14, color=TEXT_DARK, bold=True)
    add_text_box(slide, left + Inches(0.6), top + Inches(0.4), width - Inches(0.6), Inches(0.6),
                 desc, font_size=11, color=TEXT_GRAY, bold=False)


def add_module_card(slide, left, top, width, height, number, title, items, color=TECH_BLUE):
    """功能模块卡片"""
    card = add_card(slide, left, top, width, height)
    # 顶部分色条
    add_rect(slide, left, top, width, Pt(4), color)
    # 编号圆
    circle = slide.shapes.add_shape(MSO_SHAPE.OVAL, left + Inches(0.2), top + Inches(0.2),
                                    Inches(0.4), Inches(0.4))
    circle.fill.solid()
    circle.fill.fore_color.rgb = color
    circle.line.fill.background()
    tf = circle.text_frame
    tf.paragraphs[0].text = str(number)
    tf.paragraphs[0].font.size = Pt(14)
    tf.paragraphs[0].font.color.rgb = WHITE
    tf.paragraphs[0].font.bold = True
    tf.paragraphs[0].alignment = PP_ALIGN.CENTER
    # 标题
    add_text_box(slide, left + Inches(0.7), top + Inches(0.2), width - Inches(0.9), Inches(0.35),
                 title, font_size=14, color=TEXT_DARK, bold=True)
    # 条目
    y_offset = Inches(0.65)
    for item in items:
        add_text_box(slide, left + Inches(0.3), top + y_offset, width - Inches(0.5), Inches(0.3),
                     f"  {item}", font_size=10, color=TEXT_GRAY, bold=False)
        y_offset += Inches(0.22)


# ===== 开始生成 =====
prs = Presentation()
prs.slide_width = Inches(13.33)
prs.slide_height = Inches(7.5)

# ====== Slide 1: 封面 ======
slide = prs.slides.add_slide(prs.slide_layouts[6])  # blank
add_bg(slide, DARK_NAVY)

# 装饰：右上角金色大圆（半透明）
circle = slide.shapes.add_shape(MSO_SHAPE.OVAL, Inches(8.5), Inches(-1.5), Inches(6), Inches(6))
circle.fill.solid()
circle.fill.fore_color.rgb = NAVY
circle.line.fill.background()

# 金色竖线
add_gold_bar(slide, Inches(2.0), Inches(1.8), Pt(3), Inches(4.0))

# 主标题
add_text_box(slide, Inches(2.5), Inches(1.8), Inches(8), Inches(1.2),
             "明  鉴", font_size=72, color=WHITE, bold=True)
# 副标题
add_text_box(slide, Inches(2.5), Inches(2.9), Inches(8), Inches(0.6),
             "AI 法律文书智能助手", font_size=28, color=GOLD, bold=False)
# 分隔线
add_gold_bar(slide, Inches(2.5), Inches(3.8), Inches(3.0), Pt(1.5))
# 简介
add_text_box(slide, Inches(2.5), Inches(4.1), Inches(8), Inches(0.5),
             "基于大语言模型的法律文书分析、检索、审查、生成与策略辅助平台",
             font_size=14, color=LIGHT_GOLD)
# 底部信息
add_text_box(slide, Inches(2.5), Inches(5.5), Inches(8), Inches(0.4),
             "中国国际大学生创新大赛  |  高教主赛道  |  AI + 法律科技",
             font_size=12, color=TEXT_MUTED)
add_text_box(slide, Inches(2.5), Inches(5.9), Inches(8), Inches(0.4),
             "北京科技大学天津学院", font_size=14, color=TEXT_GRAY)

# ====== Slide 2: 痛点分析 ======
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_dark_slide_header(slide, "法律服务的三大痛点", "WHY WE BUILD THIS")

# 三个痛点卡片
pain_point = [
    ("高昂的法律服务成本", "普通公众难以负担律师咨询费用\n一次法律咨询动辄数百至数千元\n中小企业和个人面对法律问题望而却步"),
    ("法律文书门槛极高", "法律文书格式规范严格、术语复杂\n普通人无法独立撰写起诉状、合同等\n律师资源分布不均，基层法律服务匮乏"),
    ("传统办案效率低下", "律师需手动检索法律法规、审查合同\n同类案件缺乏系统化的策略参考\n法律知识更新快，个人难以持续跟进"),
]

for i, (title, desc) in enumerate(pain_point):
    x = Inches(0.8 + i * 4.1)
    y = Inches(2.0)
    w = Inches(3.7)
    h = Inches(4.2)
    add_card(slide, x, y, w, h)

    # 红色序号
    colors = [RGBColor(0xCC, 0x44, 0x44), RGBColor(0xD4, 0x7A, 0x2E), RGBColor(0x3B, 0x6F, 0xB6)]
    circle = slide.shapes.add_shape(MSO_SHAPE.OVAL, x + Inches(0.3), y + Inches(0.3),
                                    Inches(0.55), Inches(0.55))
    circle.fill.solid()
    circle.fill.fore_color.rgb = colors[i]
    circle.line.fill.background()
    tf = circle.text_frame
    tf.paragraphs[0].text = str(i + 1)
    tf.paragraphs[0].font.size = Pt(20)
    tf.paragraphs[0].font.color.rgb = WHITE
    tf.paragraphs[0].font.bold = True
    tf.paragraphs[0].alignment = PP_ALIGN.CENTER

    add_text_box(slide, x + Inches(1.0), y + Inches(0.35), w - Inches(1.3), Inches(0.4),
                 title, font_size=17, color=TEXT_DARK, bold=True)
    add_text_box(slide, x + Inches(0.3), y + Inches(1.15), w - Inches(0.6), Inches(2.8),
                 desc, font_size=12, color=TEXT_GRAY)

# 底部结论
add_text_box(slide, Inches(0.8), Inches(6.5), Inches(11.5), Inches(0.5),
             "痛点核心：法律服务供给严重不足  ×  群众法律需求快速增长  =  巨大的技术与服务鸿沟",
             font_size=13, color=TEXT_GRAY, bold=False, align=PP_ALIGN.CENTER)

# ====== Slide 3: 产品概述 ======
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_dark_slide_header(slide, "明鉴：五大核心能力，覆盖法律服务全流程", "PRODUCT OVERVIEW")

modules_overview = [
    ("01", "文书智能分析", "上传法律文书，AI 自动识别\n文书类型、提取关键条款、\n标注风险点并给出修订建议", TECH_BLUE),
    ("02", "法规智能检索", "自然语言提问，基于 BM25\n+ 关键词混合算法精准匹配\n349 部法律法规知识库", RGBColor(0x4A, 0x90, 0xD9)),
    ("03", "合同风险审查", "上传合同文件，自动审查\n风险条款，标注风险等级\n提供修改建议和法律依据", RGBColor(0x3B, 0xA6, 0x8A)),
    ("04", "文书智能生成", "像填空题一样填写案情，\nAI 自动生成起诉状/答辩状\n/律师函/合同等规范文书", GOLD),
    ("05", "案情策略分析", "输入案件事实，获取法律\n适用、证据指引和诉讼策略\n的综合分析建议", RGBColor(0xCC, 0x6B, 0x2E)),
]

for i, (num, title, desc, color) in enumerate(modules_overview):
    x = Inches(0.5 + i * 2.5)
    y = Inches(1.8)
    w = Inches(2.2)
    h = Inches(4.5)
    add_card(slide, x, y, w, h)
    # 顶部色条
    add_rect(slide, x, y, w, Pt(5), color)
    # 编号
    add_text_box(slide, x + Inches(0.15), y + Inches(0.3), Inches(0.5), Inches(0.5),
                 num, font_size=32, color=color, bold=True)
    # 标题
    add_text_box(slide, x + Inches(0.15), y + Inches(0.85), w - Inches(0.3), Inches(0.4),
                 title, font_size=16, color=TEXT_DARK, bold=True)
    # 描述
    add_text_box(slide, x + Inches(0.15), y + Inches(1.4), w - Inches(0.3), Inches(2.8),
                 desc, font_size=11, color=TEXT_GRAY)

# ====== Slide 4: 核心数据 ======
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_dark_slide_header(slide, "项目核心数据", "KEY METRICS")

stats = [
    ("349", "法律法规条目", "覆盖42部法律/法规"),
    ("5", "核心功能模块", "分析·检索·审查·生成·策略"),
    ("2.8万+", "中文分词词库", "jieba 法律领域适配"),
    ("100%", "关键法条命中", "BM25+关键词混合算法"),
]

for i, (num, title, sub) in enumerate(stats):
    x = Inches(1.0 + i * 3.0)
    add_stat_card(slide, x, Inches(2.2), Inches(2.5), Inches(2.2), num, "")
    add_text_box(slide, x + Inches(0.1), Inches(3.4), Inches(2.3), Inches(0.4),
                 title, font_size=16, color=TEXT_DARK, bold=True, align=PP_ALIGN.CENTER)
    add_text_box(slide, x + Inches(0.1), Inches(3.8), Inches(2.3), Inches(0.3),
                 sub, font_size=11, color=TEXT_GRAY, align=PP_ALIGN.CENTER)

# 技术亮点
add_text_box(slide, Inches(0.8), Inches(5.0), Inches(11.5), Inches(0.4),
             "技术亮点", font_size=16, color=TEXT_DARK, bold=True)

tech_highlights = [
    "✦  基于 BM25 + 关键词混合检索算法，中文法律文本匹配准确率远超传统 TF-IDF",
    "✦  流式 LLM 响应架构，用户无需等待——生成结果实时输出，体验流畅",
    "✦  结构化表单式输入设计，降低使用门槛——像做填空题一样生成法律文书",
    "✦  ONNX 轻量级语义模型，无需 GPU 即可部署，适配云服务器和个人终端",
]

for i, item in enumerate(tech_highlights):
    add_text_box(slide, Inches(0.8), Inches(5.45 + i * 0.32), Inches(11.5), Inches(0.3),
                 item, font_size=11, color=TEXT_GRAY)

# ====== Slide 5: 模块详解 — 法规检索 ======
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_dark_slide_header(slide, "法规智能检索 — 技术突破", "MODULE HIGHLIGHT: LEGAL SEARCH")

# 左边：技术栈
add_card(slide, Inches(0.8), Inches(1.7), Inches(5.8), Inches(5.0))
add_text_box(slide, Inches(1.1), Inches(1.85), Inches(5.3), Inches(0.4),
             "技术架构演进", font_size=18, color=TEXT_DARK, bold=True)

arch_items = [
    ("V1.0", "TF-IDF + 余弦相似度", "基础检索，准确率低，常见词干扰严重", RGBColor(0xCC, 0x44, 0x44)),
    ("V2.0", "BM25 + 关键词加权", "引入领域关键词，部分匹配，权重 0.08", RGBColor(0xD4, 0x7A, 0x2E)),
    ("V3.0", "BM25 + 关键词优先排序", "关键词分权重（2字/3字+，精确/部分匹配），准确率大幅提升", RGBColor(0x3B, 0xA6, 0x8A)),
]

for i, (ver, name, desc, color) in enumerate(arch_items):
    y = Inches(2.5 + i * 1.3)
    add_rect(slide, Inches(1.1), y, Inches(0.08), Inches(0.8), color)
    add_text_box(slide, Inches(1.4), y, Inches(1.0), Inches(0.3),
                 ver, font_size=11, color=color, bold=True)
    add_text_box(slide, Inches(1.4), y + Inches(0.25), Inches(5.0), Inches(0.3),
                 name, font_size=14, color=TEXT_DARK, bold=True)
    add_text_box(slide, Inches(1.4), y + Inches(0.55), Inches(5.0), Inches(0.25),
                 desc, font_size=11, color=TEXT_GRAY)

# 右边：示例
add_card(slide, Inches(7.0), Inches(1.7), Inches(5.5), Inches(5.0))
add_text_box(slide, Inches(7.3), Inches(1.85), Inches(5.0), Inches(0.4),
             "检索效果对比", font_size=18, color=TEXT_DARK, bold=True)

add_text_box(slide, Inches(7.3), Inches(2.4), Inches(5.0), Inches(0.3),
             '查询："加班是否合法"', font_size=13, color=TEXT_DARK, bold=True)

# Before
add_rect(slide, Inches(7.3), Inches(2.9), Inches(2.3), Inches(1.6),
         RGBColor(0xFF, 0xEE, 0xEE))
add_text_box(slide, Inches(7.45), Inches(2.95), Inches(2.0), Inches(0.25),
             "修复前", font_size=11, color=RGBColor(0xCC, 0x44, 0x44), bold=True)
add_text_box(slide, Inches(7.45), Inches(3.25), Inches(2.0), Inches(1.0),
             '第1名：行政诉讼法\n第6条 100%\n→ 与加班完全无关！',
             font_size=10, color=TEXT_GRAY)

# After
add_rect(slide, Inches(9.9), Inches(2.9), Inches(2.3), Inches(1.6),
         RGBColor(0xEE, 0xFF, 0xEE))
add_text_box(slide, Inches(10.05), Inches(2.95), Inches(2.0), Inches(0.25),
             "修复后", font_size=11, color=RGBColor(0x3B, 0xA6, 0x8A), bold=True)
add_text_box(slide, Inches(10.05), Inches(3.25), Inches(2.0), Inches(1.0),
             '第1名：劳动法\n第41条 65%\n→ 加班时限规定！',
             font_size=10, color=TEXT_GRAY)

# 优化方法
add_text_box(slide, Inches(7.3), Inches(4.7), Inches(5.0), Inches(0.25),
             "关键优化策略", font_size=13, color=TEXT_DARK, bold=True)
opt_items = [
    "关键词优先排序（非纯文本BM25）",
    "区分词长权重（2字 0.15 / 3字+ 0.3-0.5）",
    "精确+部分匹配双通道打分",
    "纯文本匹配降级（上限0.35）",
]
for i, item in enumerate(opt_items):
    add_text_box(slide, Inches(7.3), Inches(5.05 + i * 0.3), Inches(5.0), Inches(0.25),
                 f"  ✓ {item}", font_size=11, color=TEXT_GRAY)

# ====== Slide 6: 文书生成模块 ======
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_dark_slide_header(slide, "文书智能生成 — 体验创新", "MODULE HIGHLIGHT: DOCUMENT GENERATION")

# 左：表单设计理念
add_card(slide, Inches(0.8), Inches(1.7), Inches(5.8), Inches(5.0))
add_text_box(slide, Inches(1.1), Inches(1.85), Inches(5.3), Inches(0.4),
             "从「大框填空」到「结构化表单」", font_size=18, color=TEXT_DARK, bold=True)

# Before/After 对比
add_text_box(slide, Inches(1.1), Inches(2.5), Inches(2.5), Inches(0.3),
             "❌ 改造前", font_size=13, color=RGBColor(0xCC, 0x44, 0x44), bold=True)
add_rect(slide, Inches(1.1), Inches(2.9), Inches(2.5), Inches(1.8), RGBColor(0xFF, 0xF5, 0xF5))
add_text_box(slide, Inches(1.3), Inches(3.0), Inches(2.1), Inches(1.5),
             "一个巨大的文本框\n\"请描述案件情况...\"\n\n用户看到后无从下手\n→ 心理门槛极高",
             font_size=10, color=TEXT_GRAY)

add_text_box(slide, Inches(4.0), Inches(2.5), Inches(2.5), Inches(0.3),
             "✓ 改造后", font_size=13, color=RGBColor(0x3B, 0xA6, 0x8A), bold=True)
add_rect(slide, Inches(4.0), Inches(2.9), Inches(2.5), Inches(1.8), RGBColor(0xF5, 0xFF, 0xF5))
add_text_box(slide, Inches(4.2), Inches(3.0), Inches(2.1), Inches(1.5),
             "当事人信息：[输入框]\n事情经过：[小文本框]\n核心诉求：[小文本框]\n额外要求：[可选输入]\n\n→ 像做填空题一样简单",
             font_size=10, color=TEXT_GRAY)

# 支持的文书类型
add_text_box(slide, Inches(1.1), Inches(5.0), Inches(5.3), Inches(0.35),
             "支持 6 种法律文书自动生成 + PDF 下载", font_size=14, color=TEXT_DARK, bold=True)
doc_types = ["起诉状", "答辩状", "上诉状", "律师函", "合同", "仲裁申请书"]
for i, dt in enumerate(doc_types):
    col = i % 3
    row = i // 3
    x = Inches(1.2 + col * 1.85)
    y = Inches(5.5 + row * 0.4)
    add_icon_text_block(slide, x, y, Inches(1.7), "●", dt, "", TECH_BLUE)

# 右：PDF 生成
add_card(slide, Inches(7.0), Inches(1.7), Inches(5.5), Inches(5.0))
add_text_box(slide, Inches(7.3), Inches(1.85), Inches(5.0), Inches(0.4),
             "PDF 生成与排版优化", font_size=18, color=TEXT_DARK, bold=True)

pdf_features = [
    ("完整信息", "header 信息（当事人/法院）\n不再丢失，完整写入 PDF"),
    ("中文排版", "首行全角空格缩进、节标题\n加粗、落款右对齐"),
    ("格式补全", "自动检测并补全\"此致\"\n\"具状人\"等法律文书要素"),
    ("字体优化", "文泉驿微米黑字体渲染\n字符宽度一致，无错版"),
]

for i, (title, desc) in enumerate(pdf_features):
    col = i % 2
    row = i // 2
    x = Inches(7.3 + col * 2.65)
    y = Inches(2.5 + row * 2.0)
    add_text_box(slide, x, y, Inches(2.4), Inches(0.3),
                 f"  {title}", font_size=13, color=TEXT_DARK, bold=True)
    add_text_box(slide, x, y + Inches(0.35), Inches(2.4), Inches(1.2),
                 desc, font_size=10, color=TEXT_GRAY)

# ====== Slide 7: 全部模块 ======
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_dark_slide_header(slide, "五大功能模块详解", "ALL MODULES")

modules_detail = [
    ("文书智能分析", TECH_BLUE,
     ["上传判决书/合同/起诉状等法律文书",
      "AI 识别文书类型、当事人信息",
      "提取关键条款并标注风险等级（高/中/低）",
      "提供具体修订建议和法律依据"]),
    ("法规智能检索", RGBColor(0x4A, 0x90, 0xD9),
     ["349条法律法规知识库（42部法律）",
      "BM25 + 关键词混合检索算法",
      "自然语言提问，智能匹配法条",
      "匹配度打分，低匹配自动过滤"]),
    ("合同风险审查", RGBColor(0x3B, 0xA6, 0x8A),
     ["上传合同文件（.txt / .docx）",
      "逐条审查，标注风险条款和等级",
      "提供修改建议和法条依据",
      "生成综合风险评估报告"]),
    ("文书智能生成", GOLD,
     ["结构化表单输入（非大框填空）",
      "支持6种法律文书类型",
      "AI 流式生成，实时输出",
      "专业格式 PDF 下载"]),
    ("案情策略分析", RGBColor(0xCC, 0x6B, 0x2E),
     ["结构化案情输入（当事人/事实/争议/进展）",
      "自动匹配适用法律法规",
      "生成诉讼策略（主攻/备选/调解）",
      "关键证据指引 + 类案参考"]),
]

for i, (title, color, items) in enumerate(modules_detail):
    x = Inches(0.35 + i * 2.55)
    add_module_card(slide, x, Inches(1.7), Inches(2.35), Inches(4.8),
                    i + 1, title, items, color)

# ====== Slide 8: 技术架构 ======
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_dark_slide_header(slide, "技术架构与部署", "TECHNICAL ARCHITECTURE")

# 架构层次
layers = [
    ("展示层", "HTML5 + CSS3 + JavaScript", "响应式 UI · 玻璃态登录 · 流式输出 · 5 模块切换", RGBColor(0x3B, 0xA6, 0x8A)),
    ("API 层", "Flask + Flask-Login + Flask-CORS", "RESTful API · 用户认证 · SSE 流式 · 文件处理", TECH_BLUE),
    ("核心层", "BM25 + jieba + fpdf2", "关键词混合检索 · 中文分词 · PDF 生成 · Prompt 工程", GOLD),
    ("数据层", "SQLite + JSON 知识库", "用户数据 · 操作记录 · 349 法条 · 合同风险模式库", SLATE),
]

for i, (name, tech, desc, color) in enumerate(layers):
    y = Inches(1.7 + i * 1.2)
    # 左侧色块
    add_rect(slide, Inches(0.8), y, Inches(2.0), Inches(0.9), color)
    add_text_box(slide, Inches(0.9), y + Inches(0.2), Inches(1.8), Inches(0.5),
                 name, font_size=16, color=WHITE, bold=True, align=PP_ALIGN.CENTER)
    # 右侧详情
    add_card(slide, Inches(3.0), y, Inches(9.5), Inches(0.9))
    add_text_box(slide, Inches(3.2), y + Inches(0.08), Inches(9.0), Inches(0.3),
                 tech, font_size=14, color=TEXT_DARK, bold=True)
    add_text_box(slide, Inches(3.2), y + Inches(0.42), Inches(9.0), Inches(0.3),
                 desc, font_size=11, color=TEXT_GRAY)

# 部署
add_text_box(slide, Inches(0.8), Inches(6.6), Inches(4.0), Inches(0.3),
             "部署环境", font_size=14, color=TEXT_DARK, bold=True)
add_text_box(slide, Inches(0.8), Inches(6.9), Inches(11.5), Inches(0.3),
             "阿里云 ECS  ·  Alibaba Cloud Linux 3  ·  Python 3.8  ·  Systemd 服务管理  ·  Nginx 反向代理",
             font_size=11, color=TEXT_GRAY)

# ====== Slide 9: 创新点总结 ======
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_dark_slide_header(slide, "创新点与竞争优势", "INNOVATION & COMPETITIVE EDGE")

innov = [
    ("算法创新", "BM25 + 分权重关键词混合检索",
     ["突破传统 TF-IDF 中文法律文本准确率瓶颈",
      "2字词低权重、3字+高权重，精确与部分匹配双通道",
      "关键词优先排序 + 纯文本降级，消除无关匹配"]),
    ("体验创新", "结构化表单替代大框输入",
     ["法律文书生成从\'写作文\'变成\'做填空\'",
      "当事人信息、事实经过、核心诉求分字段引导",
      "降低非专业用户心理门槛和使用障碍"]),
    ("工程创新", "轻量级部署 + 流式架构",
     ["ONNX 模型无需 GPU，普通云服务器即可运行",
      "SSE 流式输出，生成结果实时显示不等待",
      "PDF 中文排版优化（全角缩进、落款对齐、格式补全）"]),
    ("数据创新", "规模化的中文法律知识库",
     ["349 条法律法规，覆盖 42 部核心法律/法规",
      "涵盖 2024-2026 年最新立法动态",
      "合同风险模式库，覆盖常见合同风险类型"]),
]

for i, (title, sub, items) in enumerate(innov):
    col = i % 2
    row = i // 2
    x = Inches(0.8 + col * 6.2)
    y = Inches(1.7 + row * 2.5)
    w = Inches(5.7)
    h = Inches(2.2)
    add_card(slide, x, y, w, h)
    # 金色角标
    add_rect(slide, x, y, Inches(0.08), Inches(0.8), GOLD)
    add_text_box(slide, x + Inches(0.25), y + Inches(0.15), w - Inches(0.5), Inches(0.3),
                 title, font_size=15, color=GOLD, bold=True)
    add_text_box(slide, x + Inches(0.25), y + Inches(0.45), w - Inches(0.5), Inches(0.25),
                 sub, font_size=12, color=TEXT_DARK)
    for j, item in enumerate(items):
        add_text_box(slide, x + Inches(0.25), y + Inches(0.8 + j * 0.35), w - Inches(0.5), Inches(0.3),
                     f"  ✓ {item}", font_size=10, color=TEXT_GRAY)

# ====== Slide 10: 市场分析 ======
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_dark_slide_header(slide, "市场前景与竞品分析", "MARKET & COMPETITION")

# 市场数据
stats_market = [
    ("4.3亿", "中国法律服务\n潜在用户规模"),
    ("6500亿", "2026年法律服务\n市场规模（预估）"),
    ("<5%", "法律 AI 产品\n市场渗透率"),
    ("28.6%", "法律科技市场\n年复合增长率"),
]
for i, (num, label) in enumerate(stats_market):
    add_stat_card(slide, Inches(0.8 + i * 3.15), Inches(1.7), Inches(2.8), Inches(1.8), num, label)

# 竞品对比
add_text_box(slide, Inches(0.8), Inches(3.9), Inches(5.0), Inches(0.35),
             "竞品对比", font_size=16, color=TEXT_DARK, bold=True)

comparison = [
    ("产品", "检索方式", "文书生成", "价格", "中文法律适配"),
    ("明鉴（本产品）", "BM25+关键词混合", "结构化表单+PDF", "免费/低成本", "★★★★★"),
    ("元典智库", "关键词检索", "无", "付费", "★★★"),
    ("北大法宝", "数据库检索", "无", "付费（高）", "★★★"),
    ("法狗狗", "关键词语义", "模板填空", "付费", "★★★★"),
    ("ChatGPT", "通用语义", "需手动提示", "免费/付费", "★★"),
]

for row_idx, cols in enumerate(comparison):
    y = Inches(4.4 + row_idx * 0.42)
    is_header = row_idx == 0
    bg_color = RGBColor(0xF0, 0xF0, 0xF5) if is_header else WHITE
    txt_color = TEXT_DARK if is_header else TEXT_GRAY
    txt_bold = is_header
    for col_idx, text in enumerate(cols):
        widths = [2.8, 2.4, 2.2, 1.8, 2.2]
        x = Inches(0.8 + sum(widths[:col_idx]))
        add_rect(slide, x, y, Inches(widths[col_idx] - 0.05), Inches(0.38), bg_color)
        add_text_box(slide, x + Inches(0.1), y + Inches(0.05), Inches(widths[col_idx] - 0.2), Inches(0.3),
                     text, font_size=10, color=txt_color, bold=txt_bold)

# ====== Slide 11: 商业模式 ======
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_dark_slide_header(slide, "商业模式与落地路径", "BUSINESS MODEL")

biz_models = [
    ("基础版（免费）", GOLD,
     ["法律文书智能分析", "基础法规检索（限次）", "合同风险基础审查", "社区支持"]),
    ("专业版（订阅制）", TECH_BLUE,
     ["无限次法规检索", "全部文书类型生成 + PDF", "深度策略分析", "优先客服支持"]),
    ("企业版（定制）", SLATE,
     ["私有化部署", "企业专属知识库", "API 接口集成", "定制化合同审查模板"]),
]

for i, (name, color, features) in enumerate(biz_models):
    x = Inches(0.8 + i * 4.1)
    add_card(slide, x, Inches(1.8), Inches(3.7), Inches(3.0))
    add_rect(slide, x, Inches(1.8), Inches(3.7), Pt(5), color)
    add_text_box(slide, x + Inches(0.3), Inches(2.0), Inches(3.1), Inches(0.35),
                 name, font_size=16, color=TEXT_DARK, bold=True)
    for j, feat in enumerate(features):
        add_text_box(slide, x + Inches(0.3), Inches(2.5 + j * 0.32), Inches(3.1), Inches(0.28),
                     f"  ✓ {feat}", font_size=11, color=TEXT_GRAY)

# 落地路径
add_text_box(slide, Inches(0.8), Inches(5.2), Inches(11.5), Inches(0.35),
             "落地路径", font_size=16, color=TEXT_DARK, bold=True)

steps = [
    ("阶段一", "MVP 验证\n（已完成）", "核心功能开发完成\n已部署阿里云运行"),
    ("阶段二", "种子用户\n（进行中）", "高校法学院合作\n律所试用反馈"),
    ("阶段三", "产品迭代", "按反馈优化体验\n完善知识库覆盖"),
    ("阶段四", "规模推广", "线上推广获客\n企业合作 + API 输出"),
]
for i, (phase, name, desc) in enumerate(steps):
    x = Inches(0.8 + i * 3.15)
    add_card(slide, x, Inches(5.65), Inches(2.8), Inches(1.4))
    # 编号
    add_text_box(slide, x + Inches(0.2), Inches(5.75), Inches(2.4), Inches(0.25),
                 phase, font_size=10, color=GOLD, bold=True)
    add_text_box(slide, x + Inches(0.2), Inches(5.95), Inches(2.4), Inches(0.3),
                 name, font_size=13, color=TEXT_DARK, bold=True)
    add_text_box(slide, x + Inches(0.2), Inches(6.35), Inches(2.4), Inches(0.55),
                 desc, font_size=10, color=TEXT_GRAY)
    if i < 3:
        # 箭头
        add_text_box(slide, x + Inches(2.8), Inches(5.95), Inches(0.35), Inches(0.3),
                     "→", font_size=20, color=GOLD, bold=True, align=PP_ALIGN.CENTER)

# ====== Slide 12: 未来规划 ======
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_dark_slide_header(slide, "未来发展规划", "ROADMAP")

roadmap = [
    ("短期内", "3个月内", [
        "接入 GLM-5.1 等国产大模型",
        "知识库扩充至 500+ 法律法规",
        "移动端适配（PWA 方案）",
        "接入 12348 法律援助接口",
    ]),
    ("中期", "6-12个月", [
        "上线智能问答对话模式",
        "支持多轮法律咨询对话",
        "多语言支持（藏语、维吾尔语等）",
        "建立用户反馈与案例库闭环",
    ]),
    ("长期", "1-2年", [
        "构建开放法律 AI 平台",
        "支持第三方插件/工具集成",
        "类案推荐与司法大数据分析",
        "覆盖全法律业务流程的 AI 助手",
    ]),
]

for i, (period, time, items) in enumerate(roadmap):
    x = Inches(0.8 + i * 4.1)
    add_card(slide, x, Inches(1.8), Inches(3.7), Inches(4.2))
    add_rect(slide, x, Inches(1.8), Inches(3.7), Pt(5), GOLD)

    # 时间标签
    tag = add_rect(slide, x + Inches(0.2), Inches(2.0), Inches(1.2), Inches(0.35), GOLD)
    add_text_box(slide, x + Inches(0.2), Inches(2.0), Inches(1.2), Inches(0.35),
                 period, font_size=11, color=WHITE, bold=True, align=PP_ALIGN.CENTER)
    add_text_box(slide, x + Inches(1.5), Inches(2.0), Inches(2.0), Inches(0.35),
                 time, font_size=11, color=TEXT_GRAY)

    for j, item in enumerate(items):
        add_text_box(slide, x + Inches(0.25), Inches(2.6 + j * 0.4), Inches(3.2), Inches(0.35),
                     f"  ● {item}", font_size=11, color=TEXT_GRAY)

# ====== Slide 13: 社会价值 ======
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_dark_slide_header(slide, "社会价值与影响", "SOCIAL IMPACT")

# 四个价值维度
values = [
    ("降低法律服务门槛", TECH_BLUE,
     "让普通民众以接近零成本获得基础法律服务\n\\n\"法律面前人人平等\"不仅是原则，更是技术可以推动的现实"),
    ("促进法律知识普及", GOLD,
     "通过 AI 解释法律条文、生成易懂文书\n\\n帮助公众理解法律、运用法律维护权益"),
    ("助力法治中国建设", RGBColor(0x3B, 0xA6, 0x8A),
     "为基层法律工作者提供 AI 辅助工具\n\\n缓解法律服务资源分布不均的结构性矛盾"),
    ("推动法律科技发展", SLATE,
     "开源技术方案，推动产学研合作\n\\n中文法律 NLP 领域的探索与实践"),
]

for i, (title, color, desc) in enumerate(values):
    x = Inches(0.8 + i * 3.15)
    add_card(slide, x, Inches(1.8), Inches(2.8), Inches(4.5))
    add_rect(slide, x, Inches(1.8), Inches(2.8), Pt(5), color)
    add_text_box(slide, x + Inches(0.2), Inches(2.1), Inches(2.4), Inches(0.5),
                 title, font_size=15, color=TEXT_DARK, bold=True)
    add_text_box(slide, x + Inches(0.2), Inches(2.8), Inches(2.4), Inches(3.0),
                 desc, font_size=11, color=TEXT_GRAY)

# ====== Slide 14: 团队（占位） ======
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_dark_slide_header(slide, "团队介绍", "TEAM")
add_text_box(slide, Inches(0.8), Inches(2.5), Inches(11.5), Inches(3.0),
             "（团队成员信息待补充）\n\n指导老师：\n项目负责人：\n团队成员：",
             font_size=16, color=TEXT_GRAY, align=PP_ALIGN.CENTER)

# ====== Slide 15: 致谢 ======
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_bg(slide, DARK_NAVY)

add_text_box(slide, Inches(1.5), Inches(2.0), Inches(10.33), Inches(1.5),
             "感谢聆听", font_size=60, color=WHITE, bold=True, align=PP_ALIGN.CENTER)
add_gold_bar(slide, Inches(5.5), Inches(3.5), Inches(2.33), Pt(2))
add_text_box(slide, Inches(1.5), Inches(3.9), Inches(10.33), Inches(0.5),
             "明鉴 — AI 法律文书智能助手", font_size=20, color=GOLD, align=PP_ALIGN.CENTER)
add_text_box(slide, Inches(1.5), Inches(4.6), Inches(10.33), Inches(0.5),
             "北京科技大学天津学院", font_size=14, color=TEXT_GRAY, align=PP_ALIGN.CENTER)
add_text_box(slide, Inches(1.5), Inches(5.8), Inches(10.33), Inches(0.4),
             "联系方式：[待补充]  |  GitHub：[待补充]", font_size=11, color=TEXT_MUTED, align=PP_ALIGN.CENTER)


# ===== 保存 =====
output_path = "C:/Users/hh/Desktop/ChatLaw-main/明鉴_项目展示.pptx"
prs.save(output_path)
print(f"PPT 已保存至: {output_path}")
print(f"共 {len(prs.slides)} 页幻灯片")
