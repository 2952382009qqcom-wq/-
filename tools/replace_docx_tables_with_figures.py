from pathlib import Path
import re

from docx import Document
from docx.shared import Inches
from docx.text.paragraph import Paragraph
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
INPUT = Path(r"C:\Users\hh\Desktop\明鉴_商业计划书_修改版.docx")
OUT_DIR = ROOT / "outputs" / "publication_figures"
OUTPUT = ROOT / "明鉴_商业计划书_修改版_图表替换版.docx"

OKABE = {
    "orange": "#E69F00",
    "sky": "#56B4E9",
    "green": "#009E73",
    "yellow": "#F0E442",
    "blue": "#0072B2",
    "vermillion": "#D55E00",
    "purple": "#CC79A7",
    "black": "#111111",
}


def font(size, bold=False):
    candidates = [
        r"C:\Windows\Fonts\msyhbd.ttc" if bold else r"C:\Windows\Fonts\msyh.ttc",
        r"C:\Windows\Fonts\simhei.ttf",
        r"C:\Windows\Fonts\arial.ttf",
    ]
    for item in candidates:
        if item and Path(item).exists():
            return ImageFont.truetype(item, size=size)
    return ImageFont.load_default()


F_TITLE = font(64, True)
F_SUB = font(36)
F_LABEL = font(40, True)
F_BODY = font(34)
F_SMALL = font(30)
F_TINY = font(26)


def new_canvas():
    return Image.new("RGB", (2400, 1350), "white")


def draw_wrapped(draw, text, xy, max_width, fnt, fill="#222222", line_gap=8):
    x, y = xy
    lines = []
    for para in str(text).split("\n"):
        line = ""
        for ch in para:
            test = line + ch
            if draw.textlength(test, font=fnt) <= max_width:
                line = test
            else:
                if line:
                    lines.append(line)
                line = ch
        if line:
            lines.append(line)
    for line in lines:
        draw.text((x, y), line, font=fnt, fill=fill)
        y += fnt.size + line_gap
    return y


def rounded(draw, box, radius=24, fill="#FFFFFF", outline="#DDDDDD", width=3):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def save(img, name):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / name
    img.save(path, dpi=(300, 300))
    return path


def parse_money(text):
    nums = [int(n) for n in re.findall(r"\d+", text.replace(",", ""))]
    if not nums:
        return 0
    return sum(nums) / len(nums)


def fig_competition(rows):
    img = new_canvas()
    d = ImageDraw.Draw(img)
    d.text((110, 45), "产品能力对比矩阵", font=F_TITLE, fill=OKABE["black"])
    d.text((112, 125), "结构化评估：产品形态、体验、能力与学生场景覆盖", font=F_SUB, fill="#555555")
    headers = rows[0][1:]
    dims = [r[0] for r in rows[1:]]
    scores = {
        "明鉴": [5, 5, 5, 5, 5],
        "传统法律数据库": [3, 2, 3, 1, 2],
        "通用 AI助手": [2, 2, 3, 2, 2],
    }
    x0, y0 = 410, 260
    cw, ch = 520, 170
    colors = ["#edf7fb", "#d8eff7", "#bde4f0", "#8fd3e8", OKABE["sky"]]
    for j, h in enumerate(headers):
        d.text((x0 + j * cw + 42, y0 - 70), h, font=F_LABEL, fill=OKABE["blue"])
    for i, dim in enumerate(dims):
        d.text((110, y0 + i * ch + 48), dim, font=F_LABEL, fill="#333333")
        for j, h in enumerate(headers):
            val = scores[h][i]
            box = (x0 + j * cw, y0 + i * ch, x0 + (j + 1) * cw - 26, y0 + (i + 1) * ch - 22)
            rounded(d, box, 18, fill=colors[val - 1], outline="#FFFFFF", width=4)
            dots_x = box[0] + 55
            for k in range(5):
                fill = OKABE["blue"] if k < val else "#D9E2E8"
                d.ellipse((dots_x + k * 42, box[1] + 45, dots_x + k * 42 + 24, box[1] + 69), fill=fill)
            draw_wrapped(d, rows[i + 1][j + 1], (box[0] + 55, box[1] + 88), cw - 110, F_TINY, "#27333A", 5)
    return save(img, "figure_table_2_competition.png")


def fig_cost(rows):
    img = new_canvas()
    d = ImageDraw.Draw(img)
    d.text((110, 45), "年度运营成本结构", font=F_TITLE, fill=OKABE["black"])
    d.text((112, 125), "以中位估算展示轻量化启动预算", font=F_SUB, fill="#555555")
    data = [(r[0], parse_money(r[2]), r[1], r[2]) for r in rows[1:]]
    max_v = max(v for _, v, _, _ in data)
    x0, y0 = 650, 315
    bar_h, gap = 112, 46
    palette = [OKABE["blue"], OKABE["green"], OKABE["orange"], OKABE["purple"]]
    for i, (name, value, desc, raw) in enumerate(data):
        y = y0 + i * (bar_h + gap)
        d.text((115, y + 26), name, font=F_LABEL, fill="#333333")
        d.text((115, y + 66), desc, font=F_SMALL, fill="#777777")
        w = int(1050 * value / max_v)
        d.rounded_rectangle((x0, y, x0 + 1050, y + bar_h), radius=22, fill="#EEF2F5")
        d.rounded_rectangle((x0, y, x0 + w, y + bar_h), radius=22, fill=palette[i % len(palette)])
        d.text((x0 + w + 32, y + 34), raw, font=F_BODY, fill="#333333")
    d.line((650, 1045, 1700, 1045), fill="#C8D1D8", width=3)
    for k in range(4):
        x = 650 + k * 350
        d.line((x, 1030, x, 1062), fill="#C8D1D8", width=3)
        label_x = x - (18 if k < 3 else 42)
        d.text((label_x, 1078), f"{k*400}", font=F_TINY, fill="#777777")
    d.text((1785, 1078), "元/年", font=F_TINY, fill="#777777")
    return save(img, "figure_table_4_cost_bar.png")


def fig_roadmap(rows):
    img = new_canvas()
    d = ImageDraw.Draw(img)
    d.text((110, 45), "三年商业化路径", font=F_TITLE, fill=OKABE["black"])
    d.text((112, 125), "从留存验证到机构化交付的阶段推进", font=F_SUB, fill="#555555")
    years = rows[0][1:]
    labels = [r[0] for r in rows[1:]]
    colors = [OKABE["green"], OKABE["blue"], OKABE["orange"]]
    x0, y0 = 340, 310
    col_w = 610
    for j, year in enumerate(years):
        x = x0 + j * col_w
        d.ellipse((x, y0, x + 90, y0 + 90), fill=colors[j])
        d.text((x + 20, y0 + 14), str(j + 1), font=font(46, True), fill="white")
        if j < 2:
            d.line((x + 108, y0 + 45, x + col_w - 80, y0 + 45), fill="#BFCBD3", width=8)
        d.rectangle((x + 112, y0 + 2, x + 275, y0 + 78), fill="white")
        d.text((x + 118, y0 + 18), year, font=F_LABEL, fill="#222222")
    for i, label in enumerate(labels):
        y = 500 + i * 175
        d.text((115, y + 22), label, font=F_LABEL, fill="#333333")
        for j in range(3):
            x = x0 + j * col_w
            rounded(d, (x, y, x + 480, y + 112), 20, fill="#F8FAFB", outline=colors[j], width=4)
            draw_wrapped(d, rows[i + 1][j + 1], (x + 28, y + 26), 425, F_SMALL, "#222222", 7)
    return save(img, "figure_table_5_roadmap.png")


def fig_risk(rows):
    img = new_canvas()
    d = ImageDraw.Draw(img)
    d.text((110, 45), "风险总结矩阵", font=F_TITLE, fill=OKABE["black"])
    d.text((112, 125), "按风险等级归类，并直接对应处置措施", font=F_SUB, fill="#555555")
    colors = {
        "高": OKABE["vermillion"],
        "中高": OKABE["orange"],
        "中": OKABE["blue"],
    }
    fills = {
        "高": "#FCEBE6",
        "中高": "#FFF7DC",
        "中": "#EAF5FB",
    }
    x0, y0 = 120, 245
    col_w = [470, 255, 1335]
    headers = ["风险类别", "等级", "应对措施"]
    header_fill = "#24313A"
    d.rounded_rectangle((x0, y0, x0 + sum(col_w), y0 + 96), radius=22, fill=header_fill)
    x = x0
    for w, h in zip(col_w, headers):
        d.text((x + 32, y0 + 28), h, font=F_LABEL, fill="white")
        x += w
    row_h = 205
    for i, row in enumerate(rows[1:]):
        y = y0 + 112 + i * row_h
        level = row[1]
        accent = colors.get(level, OKABE["blue"])
        fill = fills.get(level, "#F4F8FA")
        rounded(d, (x0, y, x0 + sum(col_w), y + 162), 22, fill="#FFFFFF", outline="#D8E0E6", width=3)
        d.rectangle((x0, y, x0 + 18, y + 162), fill=accent)
        d.text((x0 + 40, y + 52), row[0], font=F_LABEL, fill="#222222")
        pill = (x0 + col_w[0] + 36, y + 48, x0 + col_w[0] + 185, y + 112)
        d.rounded_rectangle(pill, radius=32, fill=fill, outline=accent, width=4)
        d.text((pill[0] + 40, pill[1] + 14), level, font=F_SMALL, fill=accent)
        draw_wrapped(
            d,
            row[2],
            (x0 + col_w[0] + col_w[1] + 35, y + 36),
            col_w[2] - 70,
            F_BODY,
            "#33404A",
            8,
        )
    return save(img, "figure_table_6_risk_matrix.png")


def fig_milestones(rows):
    img = new_canvas()
    d = ImageDraw.Draw(img)
    d.text((110, 45), "关键里程碑节奏", font=F_TITLE, fill=OKABE["black"])
    d.text((112, 125), "按时间节点组织上线、反馈、试点与交付指标", font=F_SUB, fill="#555555")
    colors = [OKABE["blue"], OKABE["green"], OKABE["orange"], OKABE["purple"]]
    x_line = 360
    d.line((x_line, 270, x_line, 1045), fill="#C7D0D7", width=10)
    for i, row in enumerate(rows[1:]):
        y = 305 + i * 210
        d.ellipse((x_line - 42, y - 42, x_line + 42, y + 42), fill=colors[i], outline="white", width=8)
        d.text((105, y - 18), row[0], font=F_LABEL, fill="#222222")
        rounded(d, (470, y - 70, 2160, y + 88), 24, fill="#FBFCFD", outline=colors[i], width=4)
        d.text((505, y - 43), row[1], font=F_LABEL, fill="#222222")
        d.text((505, y + 9), row[2], font=F_BODY, fill="#555555")
    return save(img, "figure_table_7_timeline.png")


def fig_targets(rows):
    img = new_canvas()
    d = ImageDraw.Draw(img)
    d.text((110, 45), "增长目标曲线", font=F_TITLE, fill=OKABE["black"])
    d.text((112, 125), "1年、3年、5年目标的量级跃迁", font=F_SUB, fill="#555555")
    metrics = rows[1:]
    xs = [520, 1180, 1840]
    labels = rows[0][1:]
    for x, lab in zip(xs, labels):
        d.line((x, 280, x, 1030), fill="#E7ECEF", width=4)
        d.text((x - 50, 1060), lab, font=F_LABEL, fill="#333333")
    colors = [OKABE["blue"], OKABE["green"], OKABE["orange"], OKABE["purple"], OKABE["sky"]]
    y_base = [900, 760, 620, 480, 340]
    for i, row in enumerate(metrics):
        vals = row[1:]
        y0 = y_base[i]
        pts = [(xs[0], y0), (xs[1], y0 - 90 - i * 18), (xs[2], y0 - 200 - i * 26)]
        d.line(pts, fill=colors[i], width=8, joint="curve")
        for x, y in pts:
            d.ellipse((x - 20, y - 20, x + 20, y + 20), fill=colors[i], outline="white", width=5)
        d.text((130, y0 - 22), row[0], font=F_SMALL, fill=colors[i])
        d.text((xs[0] + 35, pts[0][1] - 45), vals[0], font=F_TINY, fill="#555555")
        d.text((xs[1] + 35, pts[1][1] - 45), vals[1], font=F_TINY, fill="#555555")
        d.text((xs[2] + 35, pts[2][1] - 45), vals[2], font=F_TINY, fill="#555555")
    return save(img, "figure_table_8_targets_slope.png")


def table_data(table):
    return [[cell.text.strip() for cell in row.cells] for row in table.rows]


def insert_picture_before_table(table, image_path):
    p = table._tbl.getparent().makeelement("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p")
    table._tbl.addprevious(p)
    paragraph = Paragraph(p, table._parent)
    paragraph.alignment = 1
    run = paragraph.add_run()
    run.add_picture(str(image_path), width=Inches(6.45))
    table._tbl.getparent().remove(table._tbl)


def main():
    doc = Document(INPUT)
    generators = {
        2: fig_competition,
        4: fig_cost,
        5: fig_roadmap,
        6: fig_risk,
        7: fig_milestones,
        8: fig_targets,
    }
    images = {}
    for idx, gen in generators.items():
        images[idx] = gen(table_data(doc.tables[idx - 1]))

    for idx in sorted(generators.keys(), reverse=True):
        insert_picture_before_table(doc.tables[idx - 1], images[idx])

    doc.save(OUTPUT)
    print(OUTPUT)
    for idx, path in images.items():
        print(f"table {idx} -> {path}")


if __name__ == "__main__":
    main()
