const fs = require("fs");
const path = require("path");
const pptxgen = require("pptxgenjs");

const pptx = new pptxgen();
pptx.layout = "LAYOUT_WIDE";
pptx.author = "明鉴项目团队";
pptx.company = "北京科技大学天津学院";
pptx.subject = "中国国际大学生创新大赛项目展示";
pptx.title = "明鉴 AI法律文书智能助手";
pptx.lang = "zh-CN";
pptx.theme = {
  headFontFace: "Microsoft YaHei",
  bodyFontFace: "Microsoft YaHei",
  lang: "zh-CN",
};
pptx.defineLayout({ name: "WIDE", width: 13.333, height: 7.5 });
pptx.layout = "WIDE";

const C = {
  ink: "172033",
  ink2: "223049",
  paper: "F7F5EF",
  white: "FFFFFF",
  muted: "687284",
  line: "D8D3C8",
  gold: "C09A3E",
  blue: "326AA6",
  teal: "2E8A7D",
  red: "B65A4A",
  green: "4E8D63",
  amberBg: "F2E7CB",
  blueBg: "E7EDF5",
  greenBg: "E5EFEA",
  redBg: "F2E6E1",
};

const W = 13.333;
const H = 7.5;
const M = 0.62;
const font = "Microsoft YaHei";

function loadProjectStats() {
  const provisions = JSON.parse(fs.readFileSync(path.join(__dirname, "data/provisions.json"), "utf8"));
  const risks = JSON.parse(fs.readFileSync(path.join(__dirname, "data/contract_risks.json"), "utf8"));
  return {
    provisions: provisions.provisions.length,
    laws: new Set(provisions.provisions.map((x) => x.law_name)).size,
    principles: (provisions.legal_principles || []).length,
    risks: risks.risk_patterns.length,
  };
}

const stats = loadProjectStats();

function addBg(slide, color = C.paper) {
  slide.background = { color };
}

function addFooter(slide, idx) {
  slide.addShape(pptx.ShapeType.line, {
    x: M,
    y: 7.05,
    w: 10.9,
    h: 0,
    line: { color: C.line, width: 0.6 },
  });
  slide.addText("明鉴 AI法律文书智能助手 · 中国国际大学生创新大赛", {
    x: M,
    y: 7.12,
    w: 7.5,
    h: 0.18,
    fontFace: font,
    fontSize: 7.5,
    color: C.muted,
    margin: 0,
    breakLine: false,
  });
  slide.addText(String(idx).padStart(2, "0"), {
    x: 12.25,
    y: 7.08,
    w: 0.45,
    h: 0.2,
    fontFace: font,
    fontSize: 8,
    bold: true,
    color: C.ink,
    margin: 0,
    align: "right",
  });
}

function title(slide, kicker, claim, idx) {
  slide.addShape(pptx.ShapeType.rect, {
    x: M,
    y: 0.45,
    w: 0.08,
    h: 0.42,
    fill: { color: C.gold },
    line: { color: C.gold },
  });
  slide.addText(kicker, {
    x: M + 0.18,
    y: 0.47,
    w: 2.4,
    h: 0.25,
    fontFace: font,
    fontSize: 8.5,
    bold: true,
    color: C.gold,
    margin: 0,
    charSpace: 1.5,
  });
  slide.addText(claim, {
    x: M,
    y: 0.82,
    w: 11.6,
    h: 0.5,
    fontFace: font,
    fontSize: 23,
    bold: true,
    color: C.ink,
    margin: 0,
    fit: "shrink",
  });
  addFooter(slide, idx);
}

function paragraph(slide, text, x, y, w, h, size = 11, color = C.muted, bold = false) {
  slide.addText(text, {
    x,
    y,
    w,
    h,
    fontFace: font,
    fontSize: size,
    color,
    bold,
    margin: 0.03,
    breakLine: false,
    fit: "shrink",
  });
}

function pill(slide, text, x, y, w, color, fill) {
  slide.addShape(pptx.ShapeType.roundRect, {
    x,
    y,
    w,
    h: 0.32,
    rectRadius: 0.05,
    fill: { color: fill },
    line: { color: fill },
  });
  slide.addText(text, {
    x: x + 0.08,
    y: y + 0.075,
    w: w - 0.16,
    h: 0.12,
    fontFace: font,
    fontSize: 8,
    bold: true,
    color,
    margin: 0,
    align: "center",
  });
}

function metric(slide, value, label, note, x, y, w, color = C.ink) {
  slide.addShape(pptx.ShapeType.line, { x, y, w, h: 0, line: { color: C.line, width: 0.8 } });
  slide.addText(value, {
    x,
    y: y + 0.18,
    w,
    h: 0.42,
    fontFace: font,
    fontSize: 25,
    bold: true,
    color,
    margin: 0,
    fit: "shrink",
  });
  paragraph(slide, label, x, y + 0.66, w, 0.22, 10, C.ink, true);
  paragraph(slide, note, x, y + 0.95, w, 0.34, 8.8, C.muted);
}

function card(slide, x, y, w, h, fill = C.white, stroke = C.line) {
  slide.addShape(pptx.ShapeType.rect, {
    x,
    y,
    w,
    h,
    fill: { color: fill },
    line: { color: stroke, width: 0.7 },
  });
}

function bulletList(slide, items, x, y, w, size = 10.5, color = C.muted, gap = 0.34) {
  items.forEach((item, i) => {
    slide.addShape(pptx.ShapeType.ellipse, {
      x,
      y: y + i * gap + 0.08,
      w: 0.07,
      h: 0.07,
      fill: { color: C.gold },
      line: { color: C.gold },
    });
    paragraph(slide, item, x + 0.16, y + i * gap, w - 0.16, 0.28, size, color);
  });
}

function bar(slide, label, val, max, x, y, w, color = C.blue, note = "") {
  paragraph(slide, label, x, y - 0.03, 2.25, 0.2, 9, C.ink, true);
  slide.addShape(pptx.ShapeType.rect, { x: x + 2.0, y, w, h: 0.16, fill: { color: "E5E1D7" }, line: { color: "E5E1D7" } });
  slide.addShape(pptx.ShapeType.rect, { x: x + 2.0, y, w: w * val / max, h: 0.16, fill: { color }, line: { color } });
  paragraph(slide, note, x + 2.0 + w + 0.15, y - 0.03, 1.4, 0.2, 8.5, C.muted);
}

function addCover() {
  const slide = pptx.addSlide();
  addBg(slide, C.ink);
  slide.addShape(pptx.ShapeType.rect, { x: 0, y: 0, w: W, h: H, fill: { color: C.ink }, line: { color: C.ink } });
  slide.addShape(pptx.ShapeType.rect, { x: 0, y: 0, w: 0.16, h: H, fill: { color: C.gold }, line: { color: C.gold } });
  slide.addText("明鉴", {
    x: 0.82,
    y: 1.55,
    w: 5.0,
    h: 0.9,
    fontFace: font,
    fontSize: 50,
    bold: true,
    color: C.white,
    margin: 0,
  });
  slide.addText("AI 法律文书智能助手", {
    x: 0.85,
    y: 2.55,
    w: 5.8,
    h: 0.36,
    fontFace: font,
    fontSize: 20,
    color: C.gold,
    margin: 0,
  });
  slide.addText("面向公众与基层法律服务场景，提供文书分析、法规检索、合同审查、文书生成与案情策略辅助的一体化平台。", {
    x: 0.86,
    y: 3.26,
    w: 6.5,
    h: 0.72,
    fontFace: font,
    fontSize: 13,
    color: "D5DBE6",
    margin: 0,
    breakLine: false,
    fit: "shrink",
  });
  slide.addShape(pptx.ShapeType.line, { x: 0.86, y: 4.25, w: 4.0, h: 0, line: { color: C.gold, width: 1.2 } });
  slide.addText("中国国际大学生创新大赛 · 高教主赛道", {
    x: 0.86,
    y: 5.36,
    w: 5.5,
    h: 0.25,
    fontFace: font,
    fontSize: 10,
    bold: true,
    color: "D7C38B",
    margin: 0,
  });
  slide.addText("北京科技大学天津学院", {
    x: 0.86,
    y: 5.72,
    w: 5.5,
    h: 0.25,
    fontFace: font,
    fontSize: 10,
    color: "AAB3C2",
    margin: 0,
  });
  slide.addShape(pptx.ShapeType.arc, {
    x: 8.4,
    y: 0.55,
    w: 4.7,
    h: 4.7,
    adjustPoint: 0.25,
    line: { color: C.gold, transparency: 8, width: 1.1 },
  });
  ["文书分析", "法规检索", "合同审查", "文书生成", "策略辅助", "学生法律"].forEach((t, i) => {
    card(slide, 7.65 + (i % 2) * 2.3, 1.25 + Math.floor(i / 2) * 1.05, 1.95, 0.56, i === 5 ? C.gold : C.ink2, i === 5 ? C.gold : "38465F");
    slide.addText(t, {
      x: 7.78 + (i % 2) * 2.3,
      y: 1.43 + Math.floor(i / 2) * 1.05,
      w: 1.65,
      h: 0.18,
      fontFace: font,
      fontSize: 10,
      bold: true,
      color: i === 5 ? C.ink : "DEE5EF",
      margin: 0,
      align: "center",
    });
  });
}

function slide2() {
  const slide = pptx.addSlide(); addBg(slide); title(slide, "PROBLEM", "法律服务供需错配，基础法律需求仍缺少低门槛入口。", 2);
  const cols = [
    ["成本高", "一次咨询动辄数百至数千元，普通个人与小微主体难以持续负担。", C.red, C.redBg],
    ["门槛高", "起诉状、合同、律师函等文书格式严谨，非专业用户很难独立完成。", C.gold, C.amberBg],
    ["效率低", "检索法条、审查合同、梳理证据仍依赖人工，基层服务响应慢。", C.blue, C.blueBg],
  ];
  cols.forEach((c, i) => {
    const x = 0.85 + i * 4.05;
    slide.addText("0" + (i + 1), { x, y: 1.92, w: 0.6, h: 0.35, fontFace: font, fontSize: 20, bold: true, color: c[2], margin: 0 });
    slide.addShape(pptx.ShapeType.line, { x, y: 2.45, w: 3.3, h: 0, line: { color: c[2], width: 1.3 } });
    paragraph(slide, c[0], x, 2.75, 3.25, 0.28, 18, C.ink, true);
    paragraph(slide, c[1], x, 3.28, 3.2, 1.1, 12, C.muted);
    card(slide, x, 4.78, 3.25, 0.8, c[3], c[3]);
  });
  paragraph(slide, "机会判断：将高频、标准化、可结构化的法律服务环节产品化，用 AI 补足“第一步咨询”和“第一稿文书”的服务缺口。", 0.9, 6.16, 11.5, 0.36, 12, C.ink, true);
}

function slide3() {
  const slide = pptx.addSlide(); addBg(slide); title(slide, "SOLUTION", "明鉴把复杂法律任务拆成六个可操作模块。", 3);
  const items = [
    ["文书分析", "识别文书类型、提取关键条款、提示风险点"],
    ["法规检索", "自然语言提问，返回匹配法条与适用说明"],
    ["合同审查", "识别常见风险条款并给出修改建议"],
    ["文书生成", "结构化表单输入，生成规范法律文书与 PDF"],
    ["策略辅助", "基于案情梳理请求、证据与诉讼路径"],
    ["学生法律", "聚焦校园管理、奖助学金、宿舍纠纷和兼职被骗"],
  ];
  items.forEach((it, i) => {
    const col = i % 3;
    const row = Math.floor(i / 3);
    const x = 0.9 + col * 4.05;
    const y = 1.82 + row * 1.85;
    const colors = [C.blue, C.gold, C.teal, C.red, C.ink2, C.green];
    slide.addShape(pptx.ShapeType.line, { x, y, w: 3.1, h: 0, line: { color: colors[i], width: i === 5 ? 1.8 : 1.1 } });
    slide.addShape(pptx.ShapeType.ellipse, { x, y: y + 0.34, w: 0.42, h: 0.42, fill: { color: colors[i] }, line: { color: colors[i] } });
    slide.addText(String(i + 1), { x, y: y + 0.47, w: 0.42, h: 0.12, fontFace: font, fontSize: 8.5, bold: true, color: i === 1 ? C.ink : C.white, margin: 0, align: "center" });
    paragraph(slide, it[0], x + 0.58, y + 0.38, 2.3, 0.24, 14.5, C.ink, true);
    paragraph(slide, it[1], x + 0.58, y + 0.78, 2.85, 0.42, 9.2, C.muted);
  });
  card(slide, 1.05, 5.75, 11.2, 0.62, C.white, C.line);
  paragraph(slide, "核心体验：通用法律能力 + 学生专题能力并行，学生模块把校园事实、证据、校规边界和救济路径整理成可执行报告。", 1.28, 5.92, 10.7, 0.22, 11, C.ink, true);
}

function slide4() {
  const slide = pptx.addSlide(); addBg(slide); title(slide, "PROOF", "项目已具备可演示、可部署、可迭代的 MVP 基础。", 4);
  metric(slide, String(stats.provisions), "本地法条条目", `覆盖 ${stats.laws} 部法律/法规`, 0.85, 1.95, 2.55, C.gold);
  metric(slide, "6", "核心功能模块", "新增大学生法律问题咨询", 3.95, 1.95, 2.55, C.blue);
  metric(slide, String(stats.risks), "合同风险模式", "服务于风险审查与修改建议", 7.05, 1.95, 2.55, C.teal);
  metric(slide, "PDF", "文书导出能力", "中文排版、落款与格式补全", 10.15, 1.95, 2.35, C.ink);
  card(slide, 0.85, 4.55, 11.6, 1.25, C.white, C.line);
  paragraph(slide, "说明", 1.1, 4.8, 0.6, 0.2, 10, C.gold, true);
  paragraph(slide, "以上数据来自项目本地知识库与源码文件；新增学生模块已完成独立 Prompt、前端表单、流式接口和专题报告展示。", 1.85, 4.78, 9.85, 0.36, 11, C.muted);
}

function slide5() {
  const slide = pptx.addSlide(); addBg(slide); title(slide, "SEARCH", "法规检索从“相似文本”升级为“法律关键词优先”。", 5);
  card(slide, 0.85, 1.78, 5.45, 4.85, C.white, C.line);
  paragraph(slide, "演进路径", 1.15, 2.02, 2.5, 0.3, 16, C.ink, true);
  const steps = [
    ["V1", "TF-IDF + 余弦相似度", "常见词干扰明显，法律语义弱"],
    ["V2", "BM25 + 关键词加权", "引入领域关键词，提高相关性"],
    ["V3", "关键词优先排序", "区分词长、精确匹配与部分匹配"],
  ];
  steps.forEach((s, i) => {
    const y = 2.72 + i * 1.1;
    pill(slide, s[0], 1.15, y, 0.58, [C.red, C.gold, C.teal][i], ["F2E6E1", "F2E7CB", "E5EFEA"][i]);
    paragraph(slide, s[1], 1.95, y - 0.02, 3.7, 0.22, 12, C.ink, true);
    paragraph(slide, s[2], 1.95, y + 0.3, 3.7, 0.25, 9.5, C.muted);
  });
  card(slide, 6.82, 1.78, 5.6, 4.85, C.white, C.line);
  paragraph(slide, "查询样例：加班是否合法", 7.12, 2.02, 4.8, 0.26, 15, C.ink, true);
  bar(slide, "劳动法 第41条", 0.86, 1, 7.12, 2.82, 2.7, C.teal, "相关");
  bar(slide, "劳动合同法", 0.62, 1, 7.12, 3.45, 2.7, C.blue, "可参考");
  bar(slide, "行政诉讼法", 0.18, 1, 7.12, 4.08, 2.7, C.red, "降级");
  paragraph(slide, "价值：减少“看似高分但语义无关”的结果，把用户更快带到可适用的法条。", 7.12, 5.18, 4.8, 0.45, 11, C.muted);
}

function slide6() {
  const slide = pptx.addSlide(); addBg(slide); title(slide, "DOCUMENT", "文书生成把“写作文”改造成“填字段”。", 6);
  card(slide, 0.85, 1.9, 5.55, 4.7, C.white, C.line);
  paragraph(slide, "传统输入", 1.18, 2.18, 2.0, 0.26, 15, C.red, true);
  card(slide, 1.18, 2.7, 4.78, 1.35, "F7EEEE", "E2C8C0");
  paragraph(slide, "请描述案件情况……", 1.45, 3.02, 4.2, 0.24, 12, C.muted);
  paragraph(slide, "问题：用户不知道应写什么、按什么顺序写、哪些事实会影响法律结论。", 1.18, 4.72, 4.9, 0.55, 11, C.muted);
  card(slide, 6.95, 1.9, 5.45, 4.7, C.white, C.line);
  paragraph(slide, "明鉴输入", 7.28, 2.18, 2.0, 0.26, 15, C.teal, true);
  ["当事人信息", "事实经过", "核心诉求", "证据材料", "额外要求"].forEach((t, i) => {
    slide.addShape(pptx.ShapeType.rect, { x: 7.28, y: 2.68 + i * 0.46, w: 1.45, h: 0.28, fill: { color: "EDF2F5" }, line: { color: "EDF2F5" } });
    paragraph(slide, t, 7.38, 2.735 + i * 0.46, 1.22, 0.12, 7.5, C.ink, true);
    slide.addShape(pptx.ShapeType.line, { x: 8.95, y: 2.82 + i * 0.46, w: 2.75, h: 0, line: { color: C.line, width: 0.8 } });
  });
  paragraph(slide, "结果：系统用结构化事实生成起诉状、答辩状、上诉状、律师函、合同、仲裁申请书，并支持 PDF 下载。", 7.28, 5.26, 4.65, 0.48, 11, C.muted);
}

function slide7() {
  const slide = pptx.addSlide(); addBg(slide); title(slide, "ARCHITECTURE", "轻量化架构让产品可以在普通云服务器上运行。", 7);
  const layers = [
    ["展示层", "HTML5 / CSS3 / JavaScript", "响应式页面、模块切换、流式输出"],
    ["API 层", "Flask / Flask-Login / Flask-CORS", "认证、文件处理、REST API、SSE"],
    ["核心层", "BM25 / jieba / fpdf2 / Prompt", "检索、中文分词、PDF 生成、提示词编排"],
    ["数据层", "SQLite / JSON 知识库", "用户记录、法条库、合同风险库"],
  ];
  layers.forEach((l, i) => {
    const y = 1.82 + i * 1.08;
    slide.addShape(pptx.ShapeType.rect, { x: 0.95, y, w: 1.55, h: 0.54, fill: { color: [C.teal, C.blue, C.gold, C.ink2][i] }, line: { color: [C.teal, C.blue, C.gold, C.ink2][i] } });
    slide.addText(l[0], { x: 0.95, y: y + 0.18, w: 1.55, h: 0.12, fontFace: font, fontSize: 9, bold: true, color: i === 2 ? C.ink : C.white, margin: 0, align: "center" });
    paragraph(slide, l[1], 3.0, y + 0.02, 4.3, 0.2, 12, C.ink, true);
    paragraph(slide, l[2], 3.0, y + 0.32, 4.8, 0.22, 9.5, C.muted);
    slide.addShape(pptx.ShapeType.line, { x: 2.62, y: y + 0.27, w: 0.22, h: 0, line: { color: C.line, width: 1 } });
  });
  card(slide, 8.4, 1.82, 3.75, 3.78, C.white, C.line);
  paragraph(slide, "部署环境", 8.72, 2.18, 2.5, 0.24, 14, C.ink, true);
  bulletList(slide, ["阿里云 ECS", "Alibaba Cloud Linux 3", "Python 3.8", "Systemd 服务管理", "Nginx 反向代理"], 8.75, 2.72, 2.9, 10.2, C.muted, 0.42);
}

function slide8() {
  const slide = pptx.addSlide(); addBg(slide); title(slide, "INNOVATION", "创新点集中在算法、交互、工程与数据四个层面。", 8);
  const items = [
    ["算法创新", "BM25 + 分权重关键词混合检索，适配中文法律文本。", C.blue],
    ["交互创新", "结构化表单降低文书生成门槛，减少空白输入焦虑。", C.teal],
    ["工程创新", "轻量部署、流式输出、PDF 中文排版优化。", C.gold],
    ["场景创新", "学生法律模块聚焦校园、兼职、实习和校规边界。", C.ink2],
  ];
  items.forEach((it, i) => {
    const x = 0.95 + (i % 2) * 6.05;
    const y = 1.95 + Math.floor(i / 2) * 2.05;
    slide.addShape(pptx.ShapeType.line, { x, y, w: 4.8, h: 0, line: { color: it[2], width: 1.2 } });
    paragraph(slide, it[0], x, y + 0.34, 3.0, 0.28, 17, C.ink, true);
    paragraph(slide, it[1], x, y + 0.84, 4.75, 0.52, 11, C.muted);
  });
  paragraph(slide, "答辩表达建议：不要只说“用了 AI”，要强调明鉴如何把法律任务拆成可验证的产品流程。", 0.95, 6.18, 10.7, 0.28, 11, C.ink, true);
}

function slide9() {
  const slide = pptx.addSlide(); addBg(slide); title(slide, "COMPETITION", "明鉴的差异化在“生成闭环”和“本地法律适配”。", 9);
  const rows = [
    ["维度", "明鉴", "数据库产品", "通用大模型"],
    ["法规检索", "自然语言 + 本地法条匹配", "依赖关键词与检索经验", "可能缺少权威出处"],
    ["文书生成", "结构化字段 + PDF 导出", "通常不覆盖生成闭环", "需用户自行提示与排版"],
    ["学生场景", "校园法律专题报告", "通常不覆盖", "需自行组织提示"],
    ["合同审查", "风险模式 + 修改建议", "偏资料检索", "输出稳定性需约束"],
  ];
  const widths = [1.55, 3.55, 3.25, 3.25];
  rows.forEach((r, ri) => {
    let x = 0.92;
    r.forEach((cell, ci) => {
      const fill = ri === 0 ? C.ink : ci === 1 ? "F6F0DE" : C.white;
      slide.addShape(pptx.ShapeType.rect, { x, y: 1.85 + ri * 0.72, w: widths[ci], h: 0.58, fill: { color: fill }, line: { color: C.line, width: 0.6 } });
      paragraph(slide, cell, x + 0.11, 2.02 + ri * 0.72, widths[ci] - 0.22, 0.2, ri === 0 ? 9 : 8.8, ri === 0 ? C.white : C.ink, ri === 0 || ci === 1);
      x += widths[ci];
    });
  });
  paragraph(slide, "定位：不是替代律师，而是成为普通用户、学生群体和基层法律服务工作者的“第一稿工具”和“第一轮检索助手”。", 0.95, 6.02, 11.1, 0.32, 11, C.muted);
}

function slide10() {
  const slide = pptx.addSlide(); addBg(slide); title(slide, "BUSINESS", "商业化从免费验证走向专业订阅与机构定制。", 10);
  const plans = [
    ["基础版", "免费/低门槛", ["文书分析", "基础法规检索", "学生法律初步分析"], C.gold],
    ["专业版", "订阅制", ["不限次检索", "全部文书生成", "学生专题报告"], C.blue],
    ["机构版", "项目制/定制", ["私有化部署", "高校/基层试点", "API 集成"], C.teal],
  ];
  plans.forEach((p, i) => {
    const x = 0.95 + i * 4.05;
    slide.addShape(pptx.ShapeType.line, { x, y: 1.92, w: 3.0, h: 0, line: { color: p[3], width: 1.2 } });
    paragraph(slide, p[0], x, 2.26, 2.6, 0.3, 18, C.ink, true);
    paragraph(slide, p[1], x, 2.72, 2.6, 0.22, 10, p[3], true);
    bulletList(slide, p[2], x, 3.26, 3.1, 10.5, C.muted, 0.45);
  });
  card(slide, 0.95, 5.68, 11.35, 0.72, C.white, C.line);
  paragraph(slide, "落地逻辑：先用高校学生法律场景验证需求，再沉淀高频模板与知识库，最后面向高校、基层和机构输出部署与 API 能力。", 1.18, 5.92, 10.7, 0.24, 11, C.ink, true);
}

function slide11() {
  const slide = pptx.addSlide(); addBg(slide); title(slide, "ROADMAP", "未来规划围绕模型能力、知识库与真实用户反馈迭代。", 11);
  const phases = [
    ["0-3个月", "打磨 MVP", ["强化学生模块", "扩充法律法规库", "优化移动端体验"]],
    ["6-12个月", "验证场景", ["高校学生试用", "校规边界模板", "用户反馈闭环"]],
    ["1-2年", "开放平台", ["高校/基层试点", "第三方工具集成", "机构级知识库"]],
  ];
  phases.forEach((p, i) => {
    const x = 1.05 + i * 3.95;
    slide.addText(p[0], { x, y: 1.9, w: 2.2, h: 0.32, fontFace: font, fontSize: 17, bold: true, color: [C.gold, C.blue, C.teal][i], margin: 0 });
    slide.addShape(pptx.ShapeType.line, { x, y: 2.42, w: 2.9, h: 0, line: { color: [C.gold, C.blue, C.teal][i], width: 1.2 } });
    paragraph(slide, p[1], x, 2.72, 2.8, 0.26, 15, C.ink, true);
    bulletList(slide, p[2], x, 3.25, 2.9, 10, C.muted, 0.42);
  });
  paragraph(slide, "阶段重点：先把学生法律模块做成可演示、可复用、可验证的样板场景，再扩展到基层和机构协作。", 1.05, 6.18, 10.7, 0.28, 11, C.muted);
}

function slide12() {
  const slide = pptx.addSlide(); addBg(slide); title(slide, "IMPACT", "项目价值落在普法、基层服务和法治教育三个层面。", 12);
  const impact = [
    ["公众", "降低法律服务第一步门槛，帮助用户理解问题、整理材料、生成初稿。"],
    ["基层", "提升高频文书与合同初筛效率，缓解基础法律服务供给压力。"],
    ["学生", "新增校园法律专题入口，把校规边界、证据清单和救济路径变成可执行报告。"],
  ];
  impact.forEach((it, i) => {
    const y = 1.95 + i * 1.35;
    slide.addText(it[0], { x: 1.0, y, w: 1.0, h: 0.28, fontFace: font, fontSize: 16, bold: true, color: [C.blue, C.teal, C.gold][i], margin: 0 });
    slide.addShape(pptx.ShapeType.line, { x: 2.15, y: y + 0.15, w: 0.8, h: 0, line: { color: C.line, width: 0.8 } });
    paragraph(slide, it[1], 3.15, y - 0.02, 8.3, 0.3, 12, C.ink);
  });
  card(slide, 1.0, 6.0, 11.1, 0.5, C.white, C.line);
  paragraph(slide, "边界意识：AI 输出用于辅助，不替代学校正式处理或律师判断；涉及重大权益的案件仍需专业审核。", 1.23, 6.16, 10.3, 0.16, 10.5, C.muted);
}

function slide13() {
  const slide = pptx.addSlide(); addBg(slide); title(slide, "STUDENT", "学生法律模块是明鉴最有辨识度的新增场景。", 13);
  const tri = [
    ["高频", "覆盖宿舍纠纷、奖助学金、师生矛盾、入党政审、社团合规、校外兼职被骗和实习争议。"],
    ["可执行", "输出法律关系、校规边界、证据清单、风险提醒、处理路径和可直接改写的沟通文本。"],
    ["适合比赛", "高校场景天然贴近大学生创新大赛，能展示真实用户、真实痛点和真实产品闭环。"],
  ];
  tri.forEach((t, i) => {
    const x = 1.05 + i * 3.95;
    paragraph(slide, t[0], x, 2.1, 2.8, 0.35, 21, [C.blue, C.gold, C.teal][i], true);
    slide.addShape(pptx.ShapeType.line, { x, y: 2.72, w: 2.8, h: 0, line: { color: [C.blue, C.gold, C.teal][i], width: 1.2 } });
    paragraph(slide, t[1], x, 3.08, 3.0, 0.9, 11, C.muted);
  });
  card(slide, 1.05, 5.72, 10.95, 0.72, C.white, C.line);
  paragraph(slide, "建议路演现场重点演示：选择“校外兼职被骗”或“奖助学金争议”场景，填入事实与证据，展示专题报告如何给出校内沟通和外部救济路径。", 1.28, 5.94, 10.4, 0.25, 10.8, C.ink, true);
}

function slide14() {
  const slide = pptx.addSlide(); addBg(slide); title(slide, "TEAM", "团队页改为可补充信息的简洁版，避免空泛。", 14);
  const roles = [
    ["项目负责人", "产品规划 / 路演统筹 / 需求验证"],
    ["算法与后端", "检索算法 / API / 知识库建设"],
    ["前端与体验", "交互设计 / 页面实现 / 演示流程"],
    ["指导老师", "方向把关 / 法律合规 / 创赛指导"],
  ];
  roles.forEach((r, i) => {
    const x = 0.95 + (i % 2) * 6.05;
    const y = 1.9 + Math.floor(i / 2) * 1.85;
    slide.addShape(pptx.ShapeType.line, { x, y, w: 4.65, h: 0, line: { color: [C.blue, C.teal, C.gold, C.ink2][i], width: 1 } });
    paragraph(slide, r[0], x, y + 0.32, 3.2, 0.26, 15, C.ink, true);
    paragraph(slide, r[1], x, y + 0.76, 4.6, 0.24, 10.5, C.muted);
    paragraph(slide, "姓名 / 学院 / 专业 / 分工可在此处替换", x, y + 1.15, 4.6, 0.18, 8.5, "9AA1AC");
  });
  paragraph(slide, "注：因原稿未提供成员姓名，我保留可编辑文本框，正式提交前请替换为真实团队信息。", 0.95, 6.2, 10.5, 0.24, 10.5, C.muted);
}

function slide15() {
  const slide = pptx.addSlide();
  addBg(slide, C.ink);
  slide.addShape(pptx.ShapeType.rect, { x: 0, y: 0, w: W, h: H, fill: { color: C.ink }, line: { color: C.ink } });
  slide.addText("感谢聆听", {
    x: 0.9,
    y: 2.1,
    w: 5.2,
    h: 0.72,
    fontFace: font,
    fontSize: 38,
    bold: true,
    color: C.white,
    margin: 0,
  });
  slide.addText("明鉴 · AI 法律文书智能助手", {
    x: 0.92,
    y: 3.12,
    w: 5.8,
    h: 0.28,
    fontFace: font,
    fontSize: 16,
    color: C.gold,
    margin: 0,
  });
  slide.addShape(pptx.ShapeType.line, { x: 0.92, y: 3.72, w: 3.6, h: 0, line: { color: C.gold, width: 1.2 } });
  slide.addText("北京科技大学天津学院", {
    x: 0.92,
    y: 4.55,
    w: 5.2,
    h: 0.25,
    fontFace: font,
    fontSize: 11,
    color: "B8C0CE",
    margin: 0,
  });
  slide.addText("联系方式 / GitHub / 演示地址：请在正式提交前补充", {
    x: 0.92,
    y: 4.92,
    w: 6.4,
    h: 0.22,
    fontFace: font,
    fontSize: 9.5,
    color: "8D98AA",
    margin: 0,
  });
  card(slide, 8.0, 1.78, 3.8, 3.7, C.ink2, "38465F");
  paragraph(slide, "答辩收束语", 8.35, 2.12, 2.7, 0.24, 14, C.gold, true);
  paragraph(slide, "让学生遇到法律问题时，先知道该找谁、留什么证据、怎么说清楚。", 8.35, 2.72, 2.95, 1.1, 18, C.white, true);
  paragraph(slide, "AI 辅助法律服务，不替代专业判断，但可以把更多人带到正确的入口。", 8.35, 4.36, 2.9, 0.48, 10, "C8D0DD");
}

[
  addCover,
  slide2,
  slide3,
  slide4,
  slide5,
  slide6,
  slide7,
  slide8,
  slide9,
  slide10,
  slide11,
  slide12,
  slide13,
  slide14,
  slide15,
].forEach((fn) => fn());

pptx.writeFile({ fileName: path.join(__dirname, "明鉴_项目展示_优化版(2).pptx") });
