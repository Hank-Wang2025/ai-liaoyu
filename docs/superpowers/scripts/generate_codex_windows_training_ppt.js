const fs = require("fs");
const path = require("path");
const PptxGenJS = require("../pptx-tool/node_modules/pptxgenjs");

const pptx = new PptxGenJS();
pptx.layout = "LAYOUT_16x9";
pptx.author = "Codex";
pptx.company = "OpenAI";
pptx.subject = "Codex Windows beginner training";
pptx.title = "Codex 安装与使用说明";
pptx.lang = "zh-CN";

const OUT_DIR = path.resolve(__dirname, "../../presentations");
const OUT_FILE = path.join(OUT_DIR, "codex-windows-training.pptx");

const COLORS = {
  navy: "0A1B2E",
  teal: "14B8A6",
  cyan: "38BDF8",
  gold: "F59E0B",
  ink: "163046",
  slate: "5B7186",
  light: "F4F8FB",
  white: "FFFFFF",
  card: "FFFFFF",
  line: "D8E5EE",
  softTeal: "D9F5F1",
  softBlue: "E7F3FB",
  softGold: "FEF3C7",
  softGray: "EDF3F7",
  red: "DC2626",
};

const FONT = {
  title: "Microsoft YaHei",
  body: "Microsoft YaHei",
  mono: "Consolas",
};

function shadow() {
  return { type: "outer", color: "000000", blur: 2, offset: 1, angle: 45, opacity: 0.12 };
}

function addBg(slide) {
  slide.background = { color: COLORS.light };
  slide.addShape(pptx.ShapeType.rect, {
    x: 0,
    y: 0,
    w: 10,
    h: 0.55,
    line: { color: COLORS.navy, transparency: 100 },
    fill: { color: COLORS.navy },
  });
  slide.addShape(pptx.ShapeType.rect, {
    x: 0,
    y: 5.2,
    w: 10,
    h: 0.425,
    line: { color: COLORS.white, transparency: 100 },
    fill: { color: COLORS.white },
  });
}

function addFooter(slide, slideNo) {
  slide.addText(`官方信息核对日期：2026-03-17 | 基于 OpenAI 官方文档与本机 codex-cli 0.114.0`, {
    x: 0.55,
    y: 5.28,
    w: 7.9,
    h: 0.18,
    fontFace: FONT.body,
    fontSize: 8.5,
    color: COLORS.slate,
    margin: 0,
  });
  slide.addShape(pptx.ShapeType.rect, {
    x: 8.82,
    y: 5.16,
    w: 0.63,
    h: 0.28,
    line: { color: COLORS.teal, transparency: 100 },
    fill: { color: COLORS.teal },
  });
  slide.addText(String(slideNo), {
    x: 8.82,
    y: 5.18,
    w: 0.63,
    h: 0.2,
    align: "center",
    fontFace: FONT.body,
    bold: true,
    fontSize: 11,
    color: COLORS.white,
    margin: 0,
  });
}

function addHeader(slide, index, title, eyebrow) {
  addBg(slide);
  slide.addText(eyebrow, {
    x: 0.55,
    y: 0.78,
    w: 2.1,
    h: 0.2,
    fontFace: FONT.body,
    fontSize: 10,
    bold: true,
    color: COLORS.teal,
    charSpacing: 1.5,
    margin: 0,
  });
  slide.addText(title, {
    x: 0.55,
    y: 1.02,
    w: 6.7,
    h: 0.45,
    fontFace: FONT.title,
    fontSize: 25,
    bold: true,
    color: COLORS.ink,
    margin: 0,
  });
  slide.addShape(pptx.ShapeType.rect, {
    x: 8.95,
    y: 0.74,
    w: 0.58,
    h: 0.62,
    line: { color: COLORS.cyan, transparency: 100 },
    fill: { color: COLORS.cyan },
  });
  slide.addText(String(index).padStart(2, "0"), {
    x: 8.95,
    y: 0.84,
    w: 0.58,
    h: 0.2,
    fontFace: FONT.body,
    fontSize: 13,
    bold: true,
    color: COLORS.navy,
    align: "center",
    margin: 0,
  });
  addFooter(slide, index);
}

function addCard(slide, opts) {
  slide.addShape(pptx.ShapeType.rect, {
    x: opts.x,
    y: opts.y,
    w: opts.w,
    h: opts.h,
    line: { color: COLORS.line, width: 1 },
    fill: { color: opts.fill || COLORS.card },
    shadow: shadow(),
  });
  if (opts.accent) {
    slide.addShape(pptx.ShapeType.rect, {
      x: opts.x,
      y: opts.y,
      w: 0.08,
      h: opts.h,
      line: { color: opts.accent, transparency: 100 },
      fill: { color: opts.accent },
    });
  }
}

function addBulletBlock(slide, items, x, y, w, h, color = COLORS.ink, fontSize = 14) {
  const runs = [];
  items.forEach((item, idx) => {
    runs.push({
      text: item,
      options: {
        bullet: true,
        breakLine: idx !== items.length - 1,
        paraSpaceAfterPt: 10,
      },
    });
  });
  slide.addText(runs, {
    x,
    y,
    w,
    h,
    fontFace: FONT.body,
    fontSize,
    color,
    breakLine: true,
    valign: "top",
    margin: 0,
  });
}

function addCommandBox(slide, title, body, x, y, w, h) {
  slide.addShape(pptx.ShapeType.roundRect, {
    x,
    y,
    w,
    h,
    rectRadius: 0.08,
    line: { color: COLORS.navy, transparency: 100 },
    fill: { color: COLORS.navy },
    shadow: shadow(),
  });
  slide.addText(title, {
    x: x + 0.18,
    y: y + 0.12,
    w: w - 0.36,
    h: 0.18,
    fontFace: FONT.body,
    fontSize: 10,
    bold: true,
    color: "8DE7DB",
    margin: 0,
  });
  slide.addText(body, {
    x: x + 0.18,
    y: y + 0.34,
    w: w - 0.36,
    h: h - 0.46,
    fontFace: FONT.mono,
    fontSize: 12.5,
    color: COLORS.white,
    margin: 0,
    valign: "mid",
  });
}

function addStep(slide, stepNo, title, body, x, y, w, accent) {
  addCard(slide, { x, y, w, h: 1.08, accent, fill: COLORS.white });
  slide.addShape(pptx.ShapeType.ellipse, {
    x: x + 0.16,
    y: y + 0.18,
    w: 0.44,
    h: 0.44,
    line: { color: accent, transparency: 100 },
    fill: { color: accent },
  });
  slide.addText(String(stepNo), {
    x: x + 0.16,
    y: y + 0.24,
    w: 0.44,
    h: 0.22,
    align: "center",
    fontFace: FONT.body,
    fontSize: 12,
    bold: true,
    color: COLORS.white,
    margin: 0,
  });
  slide.addText(title, {
    x: x + 0.72,
    y: y + 0.16,
    w: w - 0.9,
    h: 0.24,
    fontFace: FONT.body,
    fontSize: 13,
    bold: true,
    color: COLORS.ink,
    margin: 0,
  });
  slide.addText(body, {
    x: x + 0.72,
    y: y + 0.4,
    w: w - 0.9,
    h: 0.5,
    fontFace: FONT.body,
    fontSize: 10.5,
    color: COLORS.slate,
    margin: 0,
    valign: "mid",
  });
}

function addMiniTitle(slide, text, x, y, w) {
  slide.addText(text, {
    x,
    y,
    w,
    h: 0.2,
    fontFace: FONT.body,
    fontSize: 12,
    bold: true,
    color: COLORS.ink,
    margin: 0,
  });
}

function addMetricCard(slide, title, body, x, y, w, fill, accent) {
  addCard(slide, { x, y, w, h: 1.45, fill, accent });
  slide.addText(title, {
    x: x + 0.2,
    y: y + 0.18,
    w: w - 0.36,
    h: 0.22,
    fontFace: FONT.body,
    fontSize: 13,
    bold: true,
    color: COLORS.ink,
    margin: 0,
  });
  slide.addText(body, {
    x: x + 0.2,
    y: y + 0.48,
    w: w - 0.36,
    h: 0.78,
    fontFace: FONT.body,
    fontSize: 10.5,
    color: COLORS.slate,
    margin: 0,
    valign: "top",
  });
}

function slide1() {
  const slide = pptx.addSlide();
  slide.background = { color: COLORS.navy };
  slide.addShape(pptx.ShapeType.rect, {
    x: 0.62,
    y: 0.72,
    w: 2.2,
    h: 0.2,
    line: { color: COLORS.teal, transparency: 100 },
    fill: { color: COLORS.teal },
  });
  slide.addShape(pptx.ShapeType.line, {
    x: 6.4,
    y: 0.55,
    w: 2.6,
    h: 0,
    line: { color: "1E3A52", width: 1 },
  });
  slide.addShape(pptx.ShapeType.line, {
    x: 6.4,
    y: 1.1,
    w: 2.6,
    h: 0,
    line: { color: "1E3A52", width: 1 },
  });
  slide.addText("Codex 安装与使用说明", {
    x: 0.62,
    y: 1.18,
    w: 5.6,
    h: 0.72,
    fontFace: FONT.title,
    fontSize: 28,
    bold: true,
    color: COLORS.white,
    margin: 0,
  });
  slide.addText("Windows 新同事入门培训", {
    x: 0.65,
    y: 1.98,
    w: 3.6,
    h: 0.26,
    fontFace: FONT.body,
    fontSize: 14,
    color: "9FB7CA",
    margin: 0,
  });
  slide.addText("适用对象：第一次接触 Codex 的团队成员 | 内容口径：中性技术说明书", {
    x: 0.65,
    y: 2.35,
    w: 5.6,
    h: 0.3,
    fontFace: FONT.body,
    fontSize: 10.5,
    color: "8AA4B8",
    margin: 0,
  });
  slide.addShape(pptx.ShapeType.roundRect, {
    x: 6.05,
    y: 1.2,
    w: 3.15,
    h: 2.75,
    rectRadius: 0.06,
    line: { color: "21405A", width: 1 },
    fill: { color: "10263D" },
    shadow: shadow(),
  });
  slide.addShape(pptx.ShapeType.rect, {
    x: 6.05,
    y: 1.2,
    w: 3.15,
    h: 0.34,
    line: { color: "10263D", transparency: 100 },
    fill: { color: "0B2135" },
  });
  ["F59E0B", "14B8A6", "38BDF8"].forEach((color, idx) => {
    slide.addShape(pptx.ShapeType.ellipse, {
      x: 6.18 + idx * 0.18,
      y: 1.31,
      w: 0.09,
      h: 0.09,
      line: { color, transparency: 100 },
      fill: { color },
    });
  });
  slide.addText("$ codex", {
    x: 6.28,
    y: 1.72,
    w: 2.6,
    h: 0.2,
    fontFace: FONT.mono,
    fontSize: 14,
    color: COLORS.white,
    margin: 0,
  });
  slide.addText("• 读取仓库上下文\n• 提出执行计划\n• 修改文件并运行命令\n• 保持审批与沙箱边界", {
    x: 6.28,
    y: 2.08,
    w: 2.45,
    h: 1.2,
    fontFace: FONT.mono,
    fontSize: 11,
    color: "8DE7DB",
    margin: 0,
  });
  slide.addShape(pptx.ShapeType.rect, {
    x: 0.65,
    y: 4.45,
    w: 8.55,
    h: 0.36,
    line: { color: "183551", transparency: 100 },
    fill: { color: "0F2438" },
  });
  slide.addText("核心目标：让新同事在 Windows 环境中完成安装、登录，并用 Codex 安全地开始第一个小任务。", {
    x: 0.85,
    y: 4.56,
    w: 8.1,
    h: 0.14,
    fontFace: FONT.body,
    fontSize: 10.5,
    color: "B8CBD8",
    margin: 0,
  });
  slide.addText("01", {
    x: 8.9,
    y: 4.54,
    w: 0.22,
    h: 0.22,
    fontFace: FONT.body,
    fontSize: 12,
    bold: true,
    color: COLORS.teal,
    margin: 0,
  });
}

function slide2() {
  const slide = pptx.addSlide();
  addHeader(slide, 2, "Codex 是什么", "PRODUCT OVERVIEW");
  addCard(slide, { x: 0.55, y: 1.58, w: 4.15, h: 2.82, fill: COLORS.white, accent: COLORS.teal });
  slide.addText("一句话定义", {
    x: 0.78,
    y: 1.86,
    w: 1.4,
    h: 0.2,
    fontFace: FONT.body,
    fontSize: 12,
    bold: true,
    color: COLORS.teal,
    margin: 0,
  });
  slide.addText("Codex 是运行在终端中的 AI 编码助手。它不只回答问题，还能在仓库上下文里读取文件、提出修改方案、执行命令，并把结果变成可审查的改动。", {
    x: 0.78,
    y: 2.16,
    w: 3.55,
    h: 1.38,
    fontFace: FONT.body,
    fontSize: 15.2,
    color: COLORS.ink,
    margin: 0,
    valign: "mid",
  });
  slide.addText("对新手最重要的区别：它是“可行动”的协作终端，而不是只会聊天的问答窗口。", {
    x: 0.78,
    y: 3.6,
    w: 3.55,
    h: 0.44,
    fontFace: FONT.body,
    fontSize: 11.5,
    color: COLORS.slate,
    italic: true,
    margin: 0,
  });
  addMetricCard(slide, "理解代码库", "读取目录、关键文件与文档，先建立上下文再动手。", 4.98, 1.58, 2.04, COLORS.softBlue, COLORS.cyan);
  addMetricCard(slide, "执行操作", "运行命令、修改文件、给出中间进展更新。", 7.12, 1.58, 2.04, COLORS.softTeal, COLORS.teal);
  addMetricCard(slide, "保留边界", "默认遵守沙箱和审批策略，高风险动作需要确认。", 4.98, 3.18, 2.04, COLORS.softGold, COLORS.gold);
  addMetricCard(slide, "适合协作", "先计划、再执行、最后验证，便于人工审阅和回滚。", 7.12, 3.18, 2.04, COLORS.softGray, COLORS.navy);
}

function slide3() {
  const slide = pptx.addSlide();
  addHeader(slide, 3, "Codex 能帮我们做什么", "COMMON USE CASES");
  addMetricCard(slide, "阅读仓库", "让它总结模块职责、入口文件、依赖关系，帮助新成员快速看懂项目。", 0.55, 1.62, 2.08, COLORS.white, COLORS.teal);
  addMetricCard(slide, "完成小改动", "例如修改文案、补日志、调整配置或添加一个受控范围内的小功能。", 2.9, 1.62, 2.08, COLORS.white, COLORS.cyan);
  addMetricCard(slide, "生成测试与审查", "补单测、解释失败原因、做一次偏风险导向的代码审查。", 5.25, 1.62, 2.08, COLORS.white, COLORS.gold);
  addMetricCard(slide, "定位问题", "结合报错日志和代码路径，提出排障假设并逐步验证。", 7.6, 1.62, 1.85, COLORS.white, COLORS.navy);
  addCard(slide, { x: 0.55, y: 3.55, w: 8.9, h: 1.2, fill: "EAF6F3", accent: COLORS.teal });
  addMiniTitle(slide, "建议的新手起点", 0.8, 3.82, 1.6);
  slide.addText("优先从“低风险、可验证、改动面小”的任务开始，例如：解释一个模块、改一处文案、补一个缺失测试、检查某个接口的调用链。", {
    x: 0.8,
    y: 4.08,
    w: 8.25,
    h: 0.38,
    fontFace: FONT.body,
    fontSize: 13,
    color: COLORS.ink,
    margin: 0,
  });
  slide.addText("不建议第一天就让 Codex 直接做大规模重构、跨仓库迁移、数据库破坏性操作。", {
    x: 0.8,
    y: 4.48,
    w: 8.25,
    h: 0.18,
    fontFace: FONT.body,
    fontSize: 10.5,
    color: COLORS.red,
    margin: 0,
    bold: true,
  });
}

function slide4() {
  const slide = pptx.addSlide();
  addHeader(slide, 4, "使用前准备", "WINDOWS CHECKLIST");
  addCard(slide, { x: 0.55, y: 1.62, w: 4.2, h: 3.15, fill: COLORS.white, accent: COLORS.teal });
  addMiniTitle(slide, "环境与账号", 0.8, 1.88, 1.2);
  addBulletBlock(
    slide,
    [
      "Windows 终端环境：PowerShell、Windows Terminal 或团队统一终端",
      "Node.js 22+ 与 npm，可直接执行全局安装命令",
      "可访问 OpenAI 服务的网络环境",
      "OpenAI 账号；如走 API Key 方式，还需要提前获取密钥",
      "建议在 Git 仓库根目录内使用，便于 Codex 读取上下文",
    ],
    0.8,
    2.16,
    3.55,
    2.2
  );
  addCard(slide, { x: 5.0, y: 1.62, w: 4.45, h: 1.48, fill: COLORS.softGold, accent: COLORS.gold });
  addMiniTitle(slide, "兼容性提示", 5.25, 1.88, 1.3);
  slide.addText("根据 OpenAI 官方资料，原生 Windows 上的 Codex CLI 当前仍属于实验性支持。对于长期开发和类 Unix 工作流，建议后续评估 WSL。", {
    x: 5.25,
    y: 2.16,
    w: 3.85,
    h: 0.58,
    fontFace: FONT.body,
    fontSize: 11.5,
    color: COLORS.ink,
    margin: 0,
  });
  addCard(slide, { x: 5.0, y: 3.28, w: 4.45, h: 1.48, fill: COLORS.softBlue, accent: COLORS.cyan });
  addMiniTitle(slide, "面向新手的替代入口", 5.25, 3.54, 1.8);
  slide.addText("如果团队更希望“先用起来再学命令行”，可以关注官方 Windows App。它适合培训首日演示，但本课件主线仍以 CLI 为主。", {
    x: 5.25,
    y: 3.82,
    w: 3.82,
    h: 0.56,
    fontFace: FONT.body,
    fontSize: 11.5,
    color: COLORS.ink,
    margin: 0,
  });
}

function slide5() {
  const slide = pptx.addSlide();
  addHeader(slide, 5, "Windows 安装流程", "INSTALLATION FLOW");
  addStep(slide, 1, "安装 Node.js 22+", "从官方发行版安装；安装完成后重新打开终端。", 0.55, 1.72, 4.15, COLORS.teal);
  addStep(slide, 2, "验证 node 与 npm", "确认环境变量生效，避免后续全局安装失败。", 0.55, 2.95, 4.15, COLORS.cyan);
  addStep(slide, 3, "安装 Codex CLI", "执行官方命令 npm install -g @openai/codex。", 0.55, 4.18, 4.15, COLORS.gold);
  addStep(slide, 4, "校验安装结果", "执行 codex --version 与 codex --help，确认命令可用。", 5.1, 1.72, 4.35, COLORS.navy);
  addCommandBox(slide, "建议在 PowerShell 中执行", "node --version\nnpm --version\nnpm install -g @openai/codex\ncodex --version", 5.1, 2.95, 4.35, 1.94);
  slide.addText("补充建议：如果团队最终统一用 WSL，只需要在 Ubuntu 终端内重复相同步骤即可。", {
    x: 0.55,
    y: 5.0,
    w: 8.55,
    h: 0.16,
    fontFace: FONT.body,
    fontSize: 10.5,
    color: COLORS.slate,
    margin: 0,
  });
}

function slide6() {
  const slide = pptx.addSlide();
  addHeader(slide, 6, "首次启动与登录", "FIRST RUN");
  addCommandBox(slide, "最常用的首次命令", "codex\ncodex login\ncodex login status\ncodex logout", 0.55, 1.64, 4.2, 2.26);
  addCard(slide, { x: 5.02, y: 1.64, w: 4.43, h: 3.08, fill: COLORS.white, accent: COLORS.teal });
  addMiniTitle(slide, "第一次进入时要理解的概念", 5.28, 1.9, 2.1);
  addBulletBlock(
    slide,
    [
      "登录方式：设备认证或 API Key，两种方式都要先完成身份绑定",
      "工作目录：Codex 会围绕当前目录分析仓库，因此建议先 cd 到项目根目录",
      "审批：涉及高风险命令时，工具会请求用户授权，而不是默认直接执行",
      "沙箱：可写目录与网络权限可能受限，执行环境并不等同于本机完全权限",
    ],
    5.28,
    2.2,
    3.8,
    2.15,
    COLORS.ink,
    12
  );
  slide.addText("培训讲解重点：第一次不要急着让 Codex 改大块代码，先确认登录状态、目录、审批行为都符合预期。", {
    x: 0.62,
    y: 4.2,
    w: 4.05,
    h: 0.36,
    fontFace: FONT.body,
    fontSize: 11,
    color: COLORS.slate,
    italic: true,
    margin: 0,
  });
}

function slide7() {
  const slide = pptx.addSlide();
  addHeader(slide, 7, "基本使用方式", "DAY-ONE COMMANDS");
  addCard(slide, { x: 0.55, y: 1.66, w: 2.7, h: 2.95, fill: COLORS.white, accent: COLORS.teal });
  addMiniTitle(slide, "1. 交互式协作", 0.82, 1.94, 1.6);
  slide.addText("进入一个持续对话的终端会话，适合阅读仓库、持续迭代修改、边做边审查。", {
    x: 0.82,
    y: 2.24,
    w: 2.08,
    h: 0.62,
    fontFace: FONT.body,
    fontSize: 11.5,
    color: COLORS.ink,
    margin: 0,
  });
  addCommandBox(slide, "命令", "codex", 0.82, 3.1, 2.05, 0.86);
  addCard(slide, { x: 3.62, y: 1.66, w: 2.7, h: 2.95, fill: COLORS.white, accent: COLORS.cyan });
  addMiniTitle(slide, "2. 非交互执行", 3.9, 1.94, 1.6);
  slide.addText("一次性提交明确目标并输出最终结果，适合批量说明、脚本化流程或 CI 辅助场景。", {
    x: 3.9,
    y: 2.24,
    w: 2.08,
    h: 0.62,
    fontFace: FONT.body,
    fontSize: 11.5,
    color: COLORS.ink,
    margin: 0,
  });
  addCommandBox(slide, "命令", "codex exec\n\"解释 api 路由\"", 3.9, 3.1, 2.05, 1.02);
  addCard(slide, { x: 6.69, y: 1.66, w: 2.76, h: 2.95, fill: COLORS.white, accent: COLORS.gold });
  addMiniTitle(slide, "3. 在仓库内协作", 6.96, 1.94, 1.7);
  slide.addText("最典型的使用方式：在代码仓库根目录打开 Codex，让它读取文件、提出计划、执行命令并产出 diff。", {
    x: 6.96,
    y: 2.24,
    w: 2.12,
    h: 0.8,
    fontFace: FONT.body,
    fontSize: 11.5,
    color: COLORS.ink,
    margin: 0,
  });
  addCommandBox(slide, "流程", "cd <repo>\ncodex\n说明目标 -> 看计划\n审查改动 -> 验证", 6.96, 3.1, 2.1, 1.3);
}

function slide8() {
  const slide = pptx.addSlide();
  addHeader(slide, 8, "典型工作流示例", "WORKFLOW EXAMPLE");
  addCard(slide, { x: 0.55, y: 1.62, w: 3.35, h: 3.2, fill: COLORS.white, accent: COLORS.teal });
  addMiniTitle(slide, "示例任务", 0.82, 1.88, 1.0);
  slide.addText("“请阅读当前仓库结构，找到报告页面的标题文案，并按新需求修改；完成后告诉我改了哪些文件，以及如何验证。”", {
    x: 0.82,
    y: 2.18,
    w: 2.72,
    h: 1.18,
    fontFace: FONT.body,
    fontSize: 13.2,
    color: COLORS.ink,
    margin: 0,
  });
  slide.addText("这个任务适合新手，因为范围清晰、风险可控、验证方式简单。", {
    x: 0.82,
    y: 3.76,
    w: 2.72,
    h: 0.36,
    fontFace: FONT.body,
    fontSize: 11,
    color: COLORS.slate,
    italic: true,
    margin: 0,
  });
  addStep(slide, 1, "明确目标", "描述文件范围、限制条件、是否允许执行命令。", 4.05, 1.62, 5.4, COLORS.teal);
  addStep(slide, 2, "先看计划", "要求 Codex 先总结要读哪些文件、准备怎么改。", 4.05, 2.42, 5.4, COLORS.cyan);
  addStep(slide, 3, "审查改动", "检查 diff、受影响文件和输出说明，确认没有越界修改。", 4.05, 3.22, 5.4, COLORS.gold);
  addStep(slide, 4, "执行验证", "运行构建、测试或页面验证步骤，证实结果可用。", 4.05, 4.02, 5.4, COLORS.navy);
}

function slide9() {
  const slide = pptx.addSlide();
  addHeader(slide, 9, "常见问题与排障", "TROUBLESHOOTING");
  addMetricCard(slide, "命令找不到", "先重开终端，再查 `node --version`、`npm --version` 和 `where codex`；多数是 PATH 未刷新。", 0.55, 1.66, 2.15, COLORS.white, COLORS.teal);
  addMetricCard(slide, "登录失败", "核查网络、账号状态和认证方式；必要时重新执行 `codex login` 或改用 API Key。", 2.93, 1.66, 2.15, COLORS.white, COLORS.cyan);
  addMetricCard(slide, "审批卡住", "这通常不是故障，而是安全边界生效。先读清楚请求内容，再决定是否授权。", 5.31, 1.66, 2.15, COLORS.white, COLORS.gold);
  addMetricCard(slide, "Windows/WSL", "如果原生终端行为异常、路径处理不稳定或工具链不一致，优先评估切到 WSL。", 7.69, 1.66, 1.76, COLORS.white, COLORS.navy);
  addCommandBox(slide, "常用自检命令", "where codex\ncodex --version\nnode --version\nnpm --version", 0.75, 3.56, 3.2, 1.42);
  addCard(slide, { x: 4.25, y: 3.56, w: 5.0, h: 1.34, fill: COLORS.softGold, accent: COLORS.gold });
  slide.addText("经验法则", {
    x: 4.52,
    y: 3.82,
    w: 0.9,
    h: 0.18,
    fontFace: FONT.body,
    fontSize: 12,
    bold: true,
    color: COLORS.ink,
    margin: 0,
  });
  slide.addText("先查环境命令，再查登录，最后再怀疑项目代码；很多“Codex 不能用”的首发问题，本质上是终端没准备好。", {
    x: 4.52,
    y: 4.08,
    w: 4.35,
    h: 0.5,
    fontFace: FONT.body,
    fontSize: 11.5,
    color: COLORS.ink,
    margin: 0,
  });
}

function slide10() {
  const slide = pptx.addSlide();
  addHeader(slide, 10, "使用规范与最佳实践", "SAFE COLLABORATION");
  addStep(slide, 1, "从小任务开始", "先做可验证的小范围任务，建立对输出质量和边界的判断。", 0.55, 1.66, 4.18, COLORS.teal);
  addStep(slide, 2, "提示词写清楚", "说明目标、范围、限制、是否允许联网或执行命令，以及验证标准。", 5.02, 1.66, 4.43, COLORS.cyan);
  addStep(slide, 3, "先看 diff 再接受", "任何改动都要人工审阅，不要把自动生成结果视作默认正确。", 0.55, 2.96, 4.18, COLORS.gold);
  addStep(slide, 4, "高风险操作必须确认", "删除、覆盖、安装依赖、外网访问、数据库操作都需要额外谨慎。", 5.02, 2.96, 4.43, COLORS.navy);
  addCard(slide, { x: 0.55, y: 4.1, w: 8.9, h: 0.9, fill: COLORS.white, accent: COLORS.teal });
  slide.addText("推荐提示词结构：目标 + 范围 + 约束 + 验证。", {
    x: 0.8,
    y: 4.34,
    w: 3.4,
    h: 0.34,
    fontFace: FONT.body,
    fontSize: 11,
    bold: true,
    color: COLORS.ink,
    margin: 0,
  });
  slide.addText("示例：`请只修改 app/src/views/ReportPage.vue 中的标题文案，\n不要改动接口逻辑；完成后告诉我如何在本地验证。`", {
    x: 4.15,
    y: 4.28,
    w: 4.98,
    h: 0.42,
    fontFace: FONT.mono,
    fontSize: 9.1,
    color: COLORS.navy,
    margin: 0,
  });
}

function slide11() {
  const slide = pptx.addSlide();
  slide.background = { color: COLORS.navy };
  slide.addText("先安装，再从小任务开始协作", {
    x: 0.62,
    y: 0.98,
    w: 5.6,
    h: 0.52,
    fontFace: FONT.title,
    fontSize: 25,
    bold: true,
    color: COLORS.white,
    margin: 0,
  });
  slide.addText("建议的上手顺序", {
    x: 0.65,
    y: 1.72,
    w: 1.8,
    h: 0.2,
    fontFace: FONT.body,
    fontSize: 11,
    bold: true,
    color: COLORS.teal,
    margin: 0,
  });
  ["安装 Node.js 22+", "安装并校验 Codex CLI", "完成登录", "在仓库中执行第一个小任务", "审查改动并验证结果"].forEach((text, idx) => {
    slide.addShape(pptx.ShapeType.rect, {
      x: 0.65,
      y: 2.1 + idx * 0.49,
      w: 3.4,
      h: 0.36,
      line: { color: idx % 2 === 0 ? "17314A" : "10263D", transparency: 100 },
      fill: { color: idx % 2 === 0 ? "17314A" : "10263D" },
    });
    slide.addText(`${idx + 1}. ${text}`, {
      x: 0.86,
      y: 2.2 + idx * 0.49,
      w: 2.95,
      h: 0.2,
      fontFace: FONT.body,
      fontSize: 11.5,
      color: COLORS.white,
      margin: 0,
    });
  });
  addCard(slide, { x: 5.4, y: 1.52, w: 3.9, h: 2.34, fill: "10263D", accent: COLORS.teal });
  slide.addText("Q&A", {
    x: 5.68,
    y: 1.88,
    w: 1.1,
    h: 0.32,
    fontFace: FONT.body,
    fontSize: 19,
    bold: true,
    color: COLORS.white,
    margin: 0,
  });
  slide.addText("如需课后自学，建议同步提供：\n• 官方安装文档链接\n• 团队推荐终端/WSL 规范\n• 一个适合练手的小任务清单", {
    x: 5.68,
    y: 2.34,
    w: 3.05,
    h: 1.0,
    fontFace: FONT.body,
    fontSize: 12,
    color: "C9D7E1",
    margin: 0,
  });
  slide.addText("11", {
    x: 8.86,
    y: 4.72,
    w: 0.3,
    h: 0.18,
    fontFace: FONT.body,
    fontSize: 13,
    bold: true,
    color: COLORS.teal,
    margin: 0,
  });
}

[
  slide1,
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
].forEach((buildSlide) => buildSlide());

fs.mkdirSync(OUT_DIR, { recursive: true });

pptx.writeFile({ fileName: OUT_FILE }).then(() => {
  console.log(`Wrote ${OUT_FILE}`);
});
