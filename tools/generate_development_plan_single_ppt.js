const pptxgen = require("pptxgenjs");

const pptx = new pptxgen();
pptx.defineLayout({ name: "WIDE", width: 13.333, height: 7.5 });
pptx.layout = "WIDE";
pptx.author = "明鉴项目团队";
pptx.company = "北京科技大学天津学院";
pptx.subject = "发展规划单页";
pptx.title = "明鉴发展规划";
pptx.lang = "zh-CN";
pptx.theme = {
  headFontFace: "Microsoft YaHei",
  bodyFontFace: "Microsoft YaHei",
  lang: "zh-CN",
};

const font = "Microsoft YaHei";
const C = {
  bg: "07111F",
  grid: "12304A",
  grid2: "0D253A",
  white: "F4F8FF",
  muted: "8FA3B8",
  dim: "5D7085",
  cyan: "38D9F7",
  cyan2: "66E7FF",
  blue: "7EA6FF",
  gold: "E4BF57",
  teal: "20D1B5",
  green: "57D68D",
  rose: "D87BAE",
  ink: "0A1728",
  panel: "0B1828",
  panel2: "0E2135",
};

const W = 13.333;
const H = 7.5;

function addText(slide, text, x, y, w, h, opts = {}) {
  slide.addText(text, {
    x, y, w, h,
    fontFace: font,
    margin: 0,
    fit: "shrink",
    breakLine: false,
    ...opts,
  });
}

function line(slide, x1, y1, x2, y2, color = C.grid, width = 0.7, transparency = 0) {
  slide.addShape(pptx.ShapeType.line, {
    x: x1, y: y1, w: x2 - x1, h: y2 - y1,
    line: { color, width, transparency },
  });
}

function rect(slide, x, y, w, h, fill, lineColor = fill, transparency = 0, radius = false) {
  slide.addShape(radius ? pptx.ShapeType.roundRect : pptx.ShapeType.rect, {
    x, y, w, h,
    rectRadius: radius ? 0.08 : undefined,
    fill: { color: fill, transparency },
    line: { color: lineColor, width: 0.7, transparency },
  });
}

function marker(slide, x, y, color, label) {
  slide.addShape(pptx.ShapeType.ellipse, {
    x: x - 0.08, y: y - 0.08, w: 0.16, h: 0.16,
    fill: { color },
    line: { color: C.bg, width: 1.2 },
  });
  if (label) {
    addText(slide, label, x - 0.18, y - 0.34, 0.36, 0.16, {
      fontSize: 6.5,
      bold: true,
      color,
      align: "center",
    });
  }
}

function polyline(slide, points, color, width = 2) {
  for (let i = 0; i < points.length - 1; i++) {
    line(slide, points[i][0], points[i][1], points[i + 1][0], points[i + 1][1], color, width);
  }
}

function addGrid(slide) {
  slide.background = { color: C.bg };
  for (let x = 0; x <= W + 0.01; x += 0.84) line(slide, x, 0, x, H, C.grid2, 0.45);
  for (let y = 0; y <= H + 0.01; y += 0.84) line(slide, 0, y, W, y, C.grid2, 0.45);
  line(slide, 0, 1.68, W, 1.68, C.grid, 0.8);
  line(slide, 0, 5.85, W, 5.85, C.grid, 0.8);
  line(slide, 0.62, 7.04, 11.62, 7.04, "2A4A68", 0.9);
}

function addHeader(slide) {
  rect(slide, 0.62, 0.55, 0.09, 0.09, C.cyan, C.cyan);
  addText(slide, "PLAN", 0.86, 0.51, 0.58, 0.14, {
    fontSize: 7.5,
    bold: true,
    color: "AABBD0",
    charSpace: 2.5,
  });
  addText(slide, "发展规划以产品能力、试点规模与商业化验证三条曲线同步推进", 0.62, 0.9, 9.4, 0.42, {
    fontSize: 22,
    bold: true,
    color: C.white,
  });
  addText(slide, "05 发展规划", 10.55, 0.66, 2.2, 0.42, {
    fontSize: 27,
    bold: true,
    color: "B8D8F8",
    align: "right",
  });
  slide.addShape(pptx.ShapeType.ellipse, {
    x: 0.63, y: 1.55, w: 0.09, h: 0.09,
    fill: { color: C.white },
    line: { color: C.white },
  });
}

function addChart(slide) {
  const cx = 0.95;
  const cy = 2.08;
  const cw = 7.65;
  const ch = 3.85;
  line(slide, cx, cy + ch, cx + cw, cy + ch, "2A4A68", 1.1);
  line(slide, cx, cy, cx, cy + ch, "2A4A68", 1.1);
  for (let i = 1; i <= 4; i++) {
    line(slide, cx, cy + ch - (ch * i) / 5, cx + cw, cy + ch - (ch * i) / 5, C.grid, 0.55, 20);
  }
  const phases = [
    { label: "2026\n验证期", x: cx + 1.05, band: C.teal },
    { label: "2027\n复制期", x: cx + 3.85, band: C.cyan },
    { label: "2028\n规模期", x: cx + 6.65, band: C.gold },
  ];
  phases.forEach((p, i) => {
    const bx = cx + 0.18 + i * 2.57;
    rect(slide, bx, cy + 0.08, 2.1, ch - 0.18, p.band, p.band, 88);
    line(slide, p.x, cy, p.x, cy + ch, "2A4A68", 0.65);
    addText(slide, p.label, p.x - 0.45, cy + ch + 0.16, 0.9, 0.38, {
      fontSize: 9,
      bold: true,
      color: C.white,
      align: "center",
      valign: "mid",
    });
  });

  addText(slide, "能力成熟度", cx - 0.08, cy - 0.28, 1.2, 0.17, {
    fontSize: 8,
    color: C.muted,
    bold: true,
  });
  addText(slide, "阶段节奏", cx + cw - 0.7, cy + ch + 0.18, 0.7, 0.14, {
    fontSize: 7.5,
    color: C.muted,
    align: "right",
  });

  const series = [
    { name: "产品能力", color: C.cyan, pts: [[1.25, 4.75], [4.0, 3.75], [6.8, 2.35]], vals: ["MVP", "机构版", "平台化"] },
    { name: "试点场景", color: C.gold, pts: [[1.25, 5.0], [4.0, 4.25], [6.8, 3.05]], vals: ["5+", "30+", "100+"] },
    { name: "用户规模", color: C.teal, pts: [[1.25, 5.35], [4.0, 4.55], [6.8, 3.45]], vals: ["3k+", "10w+", "50w+"] },
    { name: "商业化", color: C.blue, pts: [[1.25, 5.65], [4.0, 5.0], [6.8, 4.05]], vals: ["试点", "订阅", "API"] },
  ];
  series.forEach((s) => {
    const pts = s.pts.map(([x, y]) => [cx + x, cy + y - 2.0]);
    polyline(slide, pts, s.color, 2.2);
    pts.forEach((p, idx) => marker(slide, p[0], p[1], s.color, s.vals[idx]));
  });

  series.forEach((s, i) => {
    const lx = cx + 0.25 + i * 1.52;
    slide.addShape(pptx.ShapeType.line, {
      x: lx, y: cy + ch + 0.73, w: 0.35, h: 0,
      line: { color: s.color, width: 2.1 },
    });
    addText(slide, s.name, lx + 0.44, cy + ch + 0.65, 0.72, 0.16, {
      fontSize: 7.5,
      color: C.muted,
      bold: true,
    });
  });
}

function addStageCards(slide) {
  const cards = [
    { t: "阶段一｜产品验证", v: "六大模块稳定上线\n完成种子用户闭环", c: C.teal },
    { t: "阶段二｜试点复制", v: "高校/基层场景协作\n形成标准化交付包", c: C.cyan },
    { t: "阶段三｜规模拓展", v: "机构版与 API 服务\n沉淀行业数据资产", c: C.gold },
  ];
  cards.forEach((card, i) => {
    const x = 8.92;
    const y = 2.02 + i * 1.22;
    line(slide, x, y, x + 3.35, y, card.c, 1.7);
    addText(slide, card.t, x, y + 0.22, 2.7, 0.22, {
      fontSize: 13.5,
      bold: true,
      color: C.white,
    });
    addText(slide, card.v, x, y + 0.58, 3.15, 0.35, {
      fontSize: 9.5,
      color: C.muted,
      breakLine: true,
      fit: "shrink",
    });
    addText(slide, `0${i + 1}`, x + 2.92, y + 0.17, 0.42, 0.24, {
      fontSize: 12,
      bold: true,
      color: card.c,
      align: "right",
    });
  });
}

function addBottomProof(slide) {
  const items = [
    { k: "3 条", v: "主增长曲线", c: C.cyan },
    { k: "5+ → 100+", v: "试点场景", c: C.gold },
    { k: "3k → 50w", v: "服务人次", c: C.teal },
    { k: "API", v: "规模化接口", c: C.blue },
  ];
  items.forEach((it, i) => {
    const x = 0.88 + i * 2.16;
    addText(slide, it.k, x, 6.18, 1.28, 0.28, {
      fontSize: 17,
      bold: true,
      color: it.c,
    });
    addText(slide, it.v, x, 6.55, 1.28, 0.16, {
      fontSize: 7.8,
      color: C.muted,
    });
  });
  addText(slide, "明鉴 AI法律文书智能助手", 0.62, 7.16, 2.3, 0.12, {
    fontSize: 6.5,
    color: C.dim,
  });
  addText(slide, "11", 12.72, 7.1, 0.24, 0.18, {
    fontSize: 9,
    bold: true,
    color: C.gold,
    align: "right",
  });
}

async function main() {
  const slide = pptx.addSlide();
  addGrid(slide);
  addHeader(slide);
  addChart(slide);
  addStageCards(slide);
  addBottomProof(slide);

  await pptx.writeFile({ fileName: "明鉴_单页_发展规划_高级图表版.pptx" });
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
