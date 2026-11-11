/*
 * يولّد عرض المشرف: docs/presentation/SecureVoice_Supervisor_Presentation.pptx
 * التشغيل (من جذر المشروع):
 *   npm install pptxgenjs react-icons react react-dom sharp
 *   node tools/build_presentation.js
 */
const path = require("path");
const fs = require("fs");
const pptxgen = require("pptxgenjs");
const React = require("react");
const ReactDOMServer = require("react-dom/server");
const sharp = require("sharp");
const fa = require("react-icons/fa");

const ROOT = path.resolve(__dirname, "..");
const IMG = (p) => path.join(ROOT, "docs", "images", p);
const OUT_DIR = path.join(ROOT, "docs", "presentation");
const OUT = path.join(OUT_DIR, "SecureVoice_Supervisor_Presentation.pptx");
fs.mkdirSync(OUT_DIR, { recursive: true });

const THEME = {
  name: "SecureVoice",
  headFontFace: "Arial",
  bodyFontFace: "Arial",
  colors: {
    dk1: "0B1220", lt1: "FFFFFF", dk2: "1E293B", lt2: "EEF2F7",
    accent1: "059669", accent2: "0891B2", accent3: "D97706", accent4: "DC2626",
    accent5: "7C3AED", accent6: "64748B", hlink: "0891B2", folHlink: "7C3AED",
  },
};
const HEX = THEME.colors;

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.333 x 7.5
pres.title = "SecureVoice - Supervisor Presentation";
pres.subject = "Secure Voice Communication System Based on Lightweight Encryption Algorithms";
pres.rtlMode = true;
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
const C = pres.SchemeColor;
const W = 13.333;

// ------------------------------------------------------------------ layouts
pres.defineSlideMaster({
  title: "TITLE_DARK",
  background: { color: C.text1 },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: 0.8, y: 2.1, w: 11.7, h: 1.9, fontSize: 38, bold: true,
      color: C.background1, align: "right", valign: "middle", rtlMode: true }, text: "" } },
    { placeholder: { options: { name: "body", type: "body", x: 0.8, y: 4.05, w: 11.7, h: 0.8, fontSize: 20,
      color: "94A3B8", align: "right", valign: "top" }, text: "" } },
  ],
});
pres.defineSlideMaster({
  title: "CONTENT",
  background: { color: C.background1 },
  margin: [0.5, 0.6, 0.6, 0.6],
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: 0.6, y: 0.3, w: 12.13, h: 0.85, fontSize: 30, bold: true,
      color: C.text1, align: "right", valign: "middle", rtlMode: true }, text: "" } },
    { text: { text: "SecureVoice  •  نظام الاتصال الصوتي الآمن بالتشفير خفيف الوزن", options: {
      x: 4.5, y: 7.05, w: 8.23, h: 0.3, fontSize: 10, color: C.accent6, align: "right", rtlMode: true } } },
  ],
  slideNumber: { x: 0.6, y: 7.05, w: 0.6, h: 0.3, fontSize: 10, color: C.accent6 },
});
pres.defineSlideMaster({
  title: "SECTION_DARK",
  background: { color: C.text1 },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: 0.6, y: 0.3, w: 12.13, h: 0.85, fontSize: 30, bold: true,
      color: C.background1, align: "right", valign: "middle", rtlMode: true }, text: "" } },
  ],
  slideNumber: { x: 0.6, y: 7.05, w: 0.6, h: 0.3, fontSize: 10, color: "94A3B8" },
});

// ------------------------------------------------------------------ helpers
async function icon(Comp, hex, size = 256) {
  const svg = ReactDOMServer.renderToStaticMarkup(React.createElement(Comp, { color: "#" + hex, size: String(size) }));
  const png = await sharp(Buffer.from(svg)).png().toBuffer();
  return "image/png;base64," + png.toString("base64");
}
let objN = 0;
const oname = (p) => `${p}_${++objN}`;

function T(slide, text, o) {
  if (typeof text === "string" && !/[\u0600-\u06FF]/.test(text)) o = Object.assign({ rtlMode: false }, o, { rtlMode: false });
  slide.addText(text, Object.assign({ isTextBox: true, rtlMode: true, align: "right", valign: "top", margin: 0,
    fontSize: 14, color: C.text2, objectName: oname("text") }, o));
}
async function iconList(slide, items, x, y, w, rowH, Comp, hex, fontSize = 15) {
  const data = await icon(Comp, hex);
  for (let i = 0; i < items.length; i++) {
    const yy = y + i * rowH;
    slide.addImage({ data, x: x + w - 0.28, y: yy + 0.06, w: 0.22, h: 0.22, objectName: oname("bul"), altText: "bullet" });
    T(slide, items[i], { x, y: yy, w: w - 0.42, h: rowH - 0.05, fontSize });
  }
}
function card(slide, x, y, w, h, fill = C.background2) {
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.12, fill: { color: fill },
    line: { color: fill }, objectName: oname("card") });
}
async function iconCircle(slide, Comp, x, y, d, circleColor, iconHex = "FFFFFF") {
  slide.addShape(pres.shapes.OVAL, { x, y, w: d, h: d, fill: { color: circleColor }, line: { color: circleColor },
    objectName: oname("iconbg") });
  const pad = d * 0.24;
  slide.addImage({ data: await icon(Comp, iconHex), x: x + pad, y: y + pad, w: d - 2 * pad, h: d - 2 * pad,
    objectName: oname("icon"), altText: "icon" });
}
function newSlide(section, master = "CONTENT") {
  return pres.addSlide({ masterName: master, sectionTitle: section });
}
function img(slide, file, x, y, w, h, alt) {
  slide.addImage({ path: IMG(file), x, y, w, h, objectName: oname("img"), altText: alt });
}
const tableOpts = (o) => Object.assign({ fontSize: 12, color: HEX.dk2, border: { type: "solid", pt: 0.75, color: "CBD5E1" },
  valign: "middle", align: "right", rtlMode: true, margin: [0.04, 0.08, 0.04, 0.08] }, o);
const th = (t) => ({ text: t, options: { bold: true, color: "FFFFFF", fill: { color: HEX.dk2 }, align: "center" } });
const td = (t, o = {}) => ({ text: t, options: o });

// ================================================================== slides
(async () => {
  // ---------------------------------------------------------------- 1 Title
  pres.addSection({ title: "المقدمة" });
  let s = newSlide("المقدمة", "TITLE_DARK");
  await iconCircle(s, fa.FaLock, 11.5, 0.8, 1.05, C.accent1);
  s.addText("نظام الاتصال الصوتي الآمن المعتمد على خوارزميات التشفير خفيفة الوزن", { placeholder: "title" });
  s.addText("Secure Voice Communication System Based on Lightweight Encryption Algorithms", { placeholder: "body" });
  T(s, "عرض المشروع للمشرف — التصميم، التنفيذ، الاختبار، والنتائج", { x: 0.8, y: 4.95, w: 11.7, h: 0.45, fontSize: 18, color: C.background1 });
  T(s, "إعداد: ...........................      إشراف: ...........................", { x: 0.8, y: 5.75, w: 11.7, h: 0.45, fontSize: 16, color: "CBD5E1" });
  T(s, "Python  •  PySide6  •  Ascon-128  •  X25519  •  HKDF  •  UDP / TCP", { x: 0.8, y: 6.55, w: 11.7, h: 0.4, fontSize: 13, color: "34D399", align: "left", rtlMode: false });
  s.addNotes("شريحة العنوان. عرّف بالمشروع: برنامج سطح مكتب لـ Windows يجري مكالمة صوتية حية مشفرة بين جهازين بخوارزمية Ascon-128.");

  // ---------------------------------------------------------------- 2 Agenda
  s = newSlide("المقدمة");
  s.addText("محاور العرض", { placeholder: "title" });
  const agenda = ["المشكلة والأهداف", "لماذا التشفير خفيف الوزن و Ascon", "معمارية النظام والقنوات", "المصافحة واشتقاق المفاتيح",
    "مسار الصوت وبنية الحزمة", "خوارزمية Ascon-128 من الداخل", "التحليل الأمني والهجمات", "البرنامج (الواجهة)",
    "الاختبارات والنتائج", "التسليمات وخطة العرض والأعمال المستقبلية"];
  for (let i = 0; i < agenda.length; i++) {
    const col = i < 5 ? 0 : 1, row = i % 5;
    const x = col === 0 ? 7.0 : 0.6, y = 1.5 + row * 1.05;
    card(s, x, y, 5.73, 0.85);
    s.addShape(pres.shapes.OVAL, { x: x + 5.73 - 0.75, y: y + 0.14, w: 0.57, h: 0.57, fill: { color: C.accent1 }, line: { color: C.accent1 }, objectName: oname("num") });
    T(s, String(i + 1), { x: x + 5.73 - 0.75, y: y + 0.14, w: 0.57, h: 0.57, align: "center", valign: "middle", fontSize: 16, bold: true, color: C.background1, rtlMode: false });
    T(s, agenda[i], { x: x + 0.25, y: y + 0.1, w: 4.6, h: 0.65, valign: "middle", fontSize: 17, color: C.text1 });
  }

  // ---------------------------------------------------------------- 3 Problem
  pres.addSection({ title: "المشكلة والأهداف" });
  s = newSlide("المشكلة والأهداف");
  s.addText("المشكلة: الصوت عبر الشبكة مكشوف وحسّاس للتأخير", { placeholder: "title" });
  const threats = [
    [fa.FaUserSecret, "التنصت", "أي جهاز على نفس الشبكة يلتقط الحزم بـ Wireshark ويعيد تجميع المكالمة"],
    [fa.FaEdit, "التعديل والتزوير", "تغيير محتوى الحزم أو حقن صوت مزيف أثناء المرور"],
    [fa.FaRedo, "إعادة الإرسال", "تسجيل حزم صحيحة وإعادة بثها لاحقاً"],
    [fa.FaPeopleArrows, "رجل في المنتصف", "الوقوف بين الطرفين وانتحال كل منهما للآخر"],
  ];
  for (let i = 0; i < 4; i++) {
    const y = 1.45 + i * 1.32;
    card(s, 5.2, y, 7.53, 1.15);
    await iconCircle(s, threats[i][0], 11.85, y + 0.2, 0.75, C.accent4);
    T(s, threats[i][1], { x: 5.45, y: y + 0.13, w: 6.2, h: 0.4, fontSize: 18, bold: true, color: C.text1 });
    T(s, threats[i][2], { x: 5.45, y: y + 0.55, w: 6.2, h: 0.5, fontSize: 14 });
  }
  const stats = [["20 ms", "مدة الإطار الصوتي: يجب تشفيره وإرساله قبل الإطار التالي"],
    ["150 ms", "الحد الأقصى للتأخير الكلي المقبول (ITU-T G.114)"],
    ["موارد محدودة", "أجهزة IoT والأجهزة المحمولة بلا تسريع عتادي لـ AES"]];
  for (let i = 0; i < 3; i++) {
    const y = 1.45 + i * 1.75;
    card(s, 0.6, y, 4.3, 1.55, "E0F2FE");
    T(s, stats[i][0], { x: 0.8, y: y + 0.1, w: 3.9, h: 0.75, fontSize: i === 2 ? 26 : 36, bold: true, color: C.accent2, valign: "middle" });
    T(s, stats[i][1], { x: 0.8, y: y + 0.85, w: 3.9, h: 0.6, fontSize: 13 });
  }
  s.addNotes("المطلوب تشفير قوي وسريع وخفيف يضمن السرية والسلامة والأصالة دون التأثير على جودة المكالمة.");

  // ---------------------------------------------------------------- 4 Objectives
  s = newSlide("المشكلة والأهداف");
  s.addText("أهداف المشروع وحالة الإنجاز", { placeholder: "title" });
  const goals = ["مكالمة صوتية حية ثنائية الاتجاه بين جهازين على Windows", "تنفيذ Ascon-128 من الصفر والتحقق بالمتجهات الرسمية",
    "تشفير موثّق AEAD لكل إطار صوتي (20ms)", "تبادل مفاتيح X25519 مع سرية أمامية ومصادقة متبادلة",
    "الحماية من التعديل والتزوير وإعادة الإرسال و MITM", "مقارنة Ascon مع ChaCha20-Poly1305 و AES-128-GCM",
    "إثبات الزمن الحقيقي: تأخير كلي < 150ms", "واجهة عربية مع مراقبة حية ومحاكاة هجمات", "48 اختباراً آلياً + بناء exe تلقائي"];
  const chk = await icon(fa.FaCheckCircle, HEX.accent1);
  for (let i = 0; i < 9; i++) {
    const col = 2 - (i % 3), row = Math.floor(i / 3);
    const x = 0.6 + col * 4.11, y = 1.5 + row * 1.75;
    card(s, x, y, 3.91, 1.55);
    s.addImage({ data: chk, x: x + 3.91 - 0.65, y: y + 0.2, w: 0.45, h: 0.45, objectName: oname("chk"), altText: "done" });
    T(s, goals[i], { x: x + 0.2, y: y + 0.2, w: 2.95, h: 1.15, fontSize: 15, color: C.text1 });
  }
  T(s, "جميع الأهداف منجزة ومختبرة", { x: 0.6, y: 6.55, w: 12.13, h: 0.4, fontSize: 15, bold: true, color: C.accent1 });

  // ---------------------------------------------------------------- 5 Why Ascon
  pres.addSection({ title: "الخلفية والتصميم" });
  s = newSlide("الخلفية والتصميم");
  s.addText("لماذا التشفير خفيف الوزن؟ ولماذا Ascon-128؟", { placeholder: "title" });
  const rows = [
    [th("ChaCha20-Poly1305"), th("AES-128-GCM"), th("Ascon-128 ✔"), th("الخاصية")],
    [td("تياري ARX + Poly1305"), td("كتلي + GHASH"), td("إسفنجي Sponge + تبديل", { bold: true }), td("البنية", { bold: true })],
    [td("512 بت"), td("128 بت + جدول مفاتيح"), td("320 بت فقط", { bold: true }), td("حجم الحالة", { bold: true })],
    [td("ADD, ROT, XOR"), td("S-box بجداول + ضرب GF"), td("AND, NOT, XOR, ROT", { bold: true }), td("العمليات", { bold: true })],
    [td("نعم"), td("برمجياً: معرّض"), td("نعم (bitsliced)", { bold: true }), td("مقاومة هجمات التوقيت", { bold: true })],
    [td("لا"), td("AES-NI للأداء"), td("لا", { bold: true }), td("يحتاج تسريع عتادي", { bold: true })],
    [td("RFC 8439"), td("FIPS 197 + SP 800-38D"), td("NIST LWC 2023 / SP 800-232", { bold: true }), td("المعيار", { bold: true })],
    [td("256 / 96 / 128"), td("128 / 96 / 128"), td("128 / 128 / 128", { bold: true }), td("المفتاح / Nonce / Tag", { bold: true })],
  ];
  s.addTable(rows, tableOpts({ x: 0.6, y: 1.45, w: 8.3, colW: [2.0, 2.1, 2.3, 1.9], rowH: 0.52, fontSize: 13 }));
  card(s, 9.2, 1.45, 3.53, 4.2, "ECFDF5");
  await iconCircle(s, fa.FaTrophy, 10.55, 1.65, 0.85, C.accent1);
  T(s, "الفائزة بمسابقة NIST للتشفير خفيف الوزن (فبراير 2023) بعد تقييم 57 تصميماً", { x: 9.4, y: 2.65, w: 3.13, h: 1.1, fontSize: 15, bold: true, color: C.text1 });
  T(s, "أساس المعيار NIST SP 800-232، والخيار الأول في محفظة CAESAR للتطبيقات خفيفة الوزن", { x: 9.4, y: 3.8, w: 3.13, h: 1.0, fontSize: 13 });
  T(s, "مصممة للمعالجات الصغيرة: مساحة عتادية وطاقة أقل", { x: 9.4, y: 4.85, w: 3.13, h: 0.7, fontSize: 13, color: C.accent1, bold: true });
  T(s, "AES-GCM و ChaCha20 مضمّنتان للمقارنة العلمية ويمكن اختيارهما من البرنامج", { x: 0.6, y: 5.95, w: 12.13, h: 0.4, fontSize: 13, color: C.accent6 });

  // ---------------------------------------------------------------- 6 Architecture
  s = newSlide("الخلفية والتصميم");
  s.addText("معمارية النظام: نظير لنظير بين جهازين", { placeholder: "title" });
  img(s, "diagrams/01_architecture.png", 0.75, 1.35, 11.83, 4.55, "مخطط معمارية النظام");
  T(s, "نفس البرنامج على الجهازين: A ينتظر الاتصال و B يتصل. بعد المصافحة يرسل كل طرف صوته ويستقبل صوت الآخر في نفس الوقت (Full-duplex).",
    { x: 0.6, y: 6.1, w: 12.13, h: 0.7, fontSize: 14 });

  // ---------------------------------------------------------------- 7 Layers + threads
  s = newSlide("الخلفية والتصميم");
  s.addText("الطبقات والخيوط المتوازية", { placeholder: "title" });
  const layers = [
    [fa.FaDesktop, "الواجهة الرسومية", "gui/ — PySide6: إعدادات، حالة، 7 تبويبات", C.accent2],
    [fa.FaCogs, "محرك المكالمة", "session.py — القنوات والخيوط والإحصائيات والهجمات", C.accent1],
    [fa.FaKey, "التشفير", "crypto/ — Ascon، AEAD، المصافحة، منع التكرار", C.accent5],
    [fa.FaNetworkWired, "الشبكة", "net/packet.py + TCP/UDP sockets", C.accent3],
    [fa.FaMicrophone, "الصوت", "audio/ — الالتقاط، الترميز، مخزن الارتعاش", C.accent4],
  ];
  for (let i = 0; i < 5; i++) {
    const y = 1.4 + i * 1.05;
    card(s, 7.3, y, 5.43, 0.9);
    await iconCircle(s, layers[i][0], 12.0, y + 0.13, 0.64, layers[i][3]);
    T(s, layers[i][1], { x: 7.5, y: y + 0.08, w: 4.3, h: 0.38, fontSize: 16, bold: true, color: C.text1 });
    T(s, layers[i][2], { x: 7.5, y: y + 0.47, w: 4.3, h: 0.35, fontSize: 12 });
  }
  img(s, "diagrams/10_threads.png", 0.6, 1.5, 6.4, 3.22, "مخطط الخيوط");
  T(s, "دوال كرت الصوت لا تُشفّر شيئاً: تضع الإطار في طابور فقط. التشفير في خيط الإرسال، وفك التشفير في خيط الاستقبال، والأحداث تصل للواجهة عبر Qt Signal بأمان.",
    { x: 0.6, y: 4.95, w: 6.4, h: 1.2, fontSize: 14 });

  // ---------------------------------------------------------------- 8 Channels
  s = newSlide("الخلفية والتصميم");
  s.addText("القناة الناقلة: قناتان بين الجهازين", { placeholder: "title" });
  const ch = [
    [fa.FaHandshake, "قناة التحكم — TCP :5000", C.accent5, ["المصافحة وتبادل المفاتيح", "ثم رسائل مشفرة: CHAT / MUTE / BYE", "وصول مضمون ومرتب", "انقطاعها = إنهاء المكالمة تلقائياً"]],
    [fa.FaBroadcastTower, "قناة الوسائط — UDP :5001", C.accent1, ["حزم الصوت المشفرة: 50 حزمة/ثانية لكل اتجاه", "PING/PONG مشفرة لقياس RTT كل ثانية", "الحزمة المتأخرة لا قيمة لها: لا إعادة إرسال", "نفس اختيار SIP/RTP و WhatsApp و Zoom"]],
  ];
  for (let i = 0; i < 2; i++) {
    const x = i === 0 ? 6.83 : 0.6;
    card(s, x, 1.45, 5.9, 4.7);
    await iconCircle(s, ch[i][0], x + 4.85, 1.7, 0.85, ch[i][2]);
    T(s, ch[i][1], { x: x + 0.3, y: 1.75, w: 4.4, h: 0.75, fontSize: 20, bold: true, color: C.text1, valign: "middle" });
    await iconList(s, ch[i][3], x + 0.3, 2.9, 5.3, 0.75, fa.FaChevronLeft, i === 0 ? HEX.accent5 : HEX.accent1, 16);
  }
  T(s, "لماذا لا يكون الصوت عبر TCP؟ لأن إعادة إرسال المفقود توقف ما بعده (Head-of-line blocking) فيتراكم التأخير ويتقطع الصوت.",
    { x: 0.6, y: 6.35, w: 12.13, h: 0.5, fontSize: 14, color: C.accent6 });

  // ---------------------------------------------------------------- 9 Handshake
  pres.addSection({ title: "التشفير والبروتوكول" });
  s = newSlide("التشفير والبروتوكول");
  s.addText("المصافحة: X25519 + PBKDF2 + HKDF + Finished", { placeholder: "title" });
  img(s, "diagrams/02_handshake_sequence.png", 0.6, 1.3, 3.97, 5.6, "مخطط تسلسل المصافحة");
  const steps = [
    ["ClientHello", "B يرسل: الخوارزمية، الترميز، منفذ UDP، رقم عشوائي Rc، مفتاح X25519 عام مؤقت (57 بايت)"],
    ["ServerHello", "A يرد بنفس البنية: Rs + مفتاحه العام المؤقت"],
    ["السر المشترك", "كل طرف يحسب X25519(خاصّه، عام الآخر) — لا يُرسل أي سر"],
    ["ربط كلمة السر", "PSK = PBKDF2(كلمة السر، Rc‖Rs، 100,000 تكرار)"],
    ["اشتقاق المفاتيح", "HKDF(PSK، السر، hash الرسائل) ← 264 بايت = 10 مفاتيح وقيم"],
    ["Finished", "HMAC يثبت معرفة كلمة السر؛ أي اختلاف = رفض (MITM / كلمة سر خاطئة)"],
    ["رمز الأمان SAS", "6 أرقام تظهر على الشاشتين؛ تطابقها = لا وسيط"],
  ];
  for (let i = 0; i < steps.length; i++) {
    const y = 1.35 + i * 0.8;
    s.addShape(pres.shapes.OVAL, { x: 12.2, y: y + 0.08, w: 0.5, h: 0.5, fill: { color: C.accent2 }, line: { color: C.accent2 }, objectName: oname("n") });
    T(s, String(i + 1), { x: 12.2, y: y + 0.08, w: 0.5, h: 0.5, align: "center", valign: "middle", fontSize: 14, bold: true, color: C.background1, rtlMode: false });
    T(s, steps[i][0], { x: 4.9, y: y, w: 7.1, h: 0.32, fontSize: 15, bold: true, color: C.text1 });
    T(s, steps[i][1], { x: 4.9, y: y + 0.33, w: 7.1, h: 0.4, fontSize: 13 });
  }
  s.addNotes("زمن المصافحة الكامل حوالي 20 إلى 50 ميلي ثانية، معظمه في PBKDF2. مفاتيح X25519 مؤقتة لكل مكالمة فتتحقق السرية الأمامية.");

  // ---------------------------------------------------------------- 10 Key schedule
  s = newSlide("التشفير والبروتوكول");
  s.addText("اشتقاق مفاتيح الجلسة وفصلها", { placeholder: "title" });
  img(s, "diagrams/07_key_derivation.png", 0.6, 1.35, 6.6, 4.82, "مخطط اشتقاق المفاتيح");
  const keyRows = [
    [th("الاستخدام"), th("الحجم"), th("المفتاح")],
    [td("صوت B ← A"), td("32 + IV 16", { align: "center" }), td("c2s_key", { bold: true })],
    [td("صوت A ← B"), td("32 + IV 16", { align: "center" }), td("s2c_key", { bold: true })],
    [td("رسائل التحكم (اتجاهان)"), td("2 × (32 + 16)", { align: "center" }), td("ctl keys", { bold: true })],
    [td("Finished MAC"), td("32", { align: "center" }), td("confirm", { bold: true })],
    [td("رمز الأمان (6 أرقام)"), td("8", { align: "center" }), td("sas", { bold: true })],
  ];
  s.addTable(keyRows, tableOpts({ x: 7.5, y: 1.4, w: 5.23, colW: [2.35, 1.48, 1.4], rowH: 0.5, fontSize: 13 }));
  card(s, 7.5, 4.6, 5.23, 1.6, "F5F3FF");
  T(s, "Nonce = IV ⊕ رقم التسلسل", { x: 7.7, y: 4.75, w: 4.83, h: 0.4, fontSize: 17, bold: true, color: C.accent5 });
  T(s, "نفس أسلوب TLS 1.3: لا يتكرر أبداً، ولا يُرسل على الشبكة، ومفتاح مختلف لكل اتجاه يمنع هجوم الانعكاس", { x: 7.7, y: 5.2, w: 4.83, h: 0.9, fontSize: 13 });

  // ---------------------------------------------------------------- 11 Voice path
  s = newSlide("التشفير والبروتوكول");
  s.addText("طريقة نقل الصوت وتشفيره: من الميكروفون إلى السماعة", { placeholder: "title" });
  const txSteps = [
    [fa.FaMicrophone, "الميكروفون", "320 عينة / 20ms\n16kHz • 640 بايت"],
    [fa.FaWaveSquare, "الترميز", "PCM16: 640B\nأو μ-law: 320B"],
    [fa.FaHashtag, "التسلسل والـ Nonce", "seq += 1\nNonce = IV ⊕ seq"],
    [fa.FaLock, "تشفير Ascon-128", "AD = الترويسة 10B\n+ وسم 16B"],
    [fa.FaPaperPlane, "إرسال UDP", "حزمة 666 بايت\n50 حزمة/ثانية"],
  ];
  const rxSteps = [
    [fa.FaInbox, "استقبال UDP", "فحص البنية\nوالإصدار"],
    [fa.FaRedo, "منع التكرار", "نافذة 64 حزمة\nالمكرر ← رفض"],
    [fa.FaUnlock, "تحقق + فك", "وسم خاطئ ← رفض\n+ تنبيه أمني"],
    [fa.FaLayerGroup, "مخزن الارتعاش", "ترتيب + 60ms\n+ إخفاء الفقد"],
    [fa.FaVolumeUp, "السماعة", "إطار كل 20ms\nصوت واضح"],
  ];
  async function flowRow(list, y, color, label) {
    T(s, label, { x: 0.6, y: y - 0.45, w: 12.13, h: 0.35, fontSize: 15, bold: true, color });
    for (let i = 0; i < 5; i++) {
      const x = 10.45 - i * 2.46;
      card(s, x, y, 2.18, 2.1);
      await iconCircle(s, list[i][0], x + 0.79, y + 0.15, 0.6, color);
      T(s, list[i][1], { x: x + 0.1, y: y + 0.82, w: 1.98, h: 0.4, fontSize: 14, bold: true, color: C.text1, align: "center" });
      T(s, list[i][2], { x: x + 0.1, y: y + 1.22, w: 1.98, h: 0.8, fontSize: 12, align: "center" });
      if (i < 4) s.addShape(pres.shapes.LEFT_ARROW, { x: x - 0.25, y: y + 0.9, w: 0.22, h: 0.3, fill: { color }, line: { color }, objectName: oname("arrow") });
    }
  }
  await flowRow(txSteps, 1.75, C.accent1, "① الجهاز المرسل");
  await flowRow(rxSteps, 4.55, C.accent2, "② الجهاز المستقبل");

  // ---------------------------------------------------------------- 12 Packet format
  s = newSlide("التشفير والبروتوكول");
  s.addText("بنية حزمة الصوت على UDP", { placeholder: "title" });
  const fields = [["Version", 1, C.accent6, "1B"], ["Type", 1, C.accent6, "1B"], ["Sequence", 2.2, C.accent5, "4B"],
    ["Frame #", 2.2, C.accent5, "4B"], ["Ciphertext (الصوت المشفر)", 4.7, C.accent1, "640B / 320B"], ["Tag", 1.93, C.accent3, "16B"]];
  let fx = 0.6;
  for (const [name, w, col, size] of fields) {
    s.addShape(pres.shapes.RECTANGLE, { x: fx, y: 1.6, w, h: 1.0, fill: { color: col }, line: { color: "FFFFFF", width: 2 }, objectName: oname("field") });
    T(s, name, { x: fx, y: 1.6, w, h: 0.6, align: "center", valign: "middle", fontSize: 13, bold: true, color: C.background1, rtlMode: false });
    T(s, size, { x: fx, y: 2.15, w, h: 0.4, align: "center", valign: "middle", fontSize: 12, color: C.background1, rtlMode: false });
    fx += w;
  }
  T(s, "← الترويسة 10 بايت: غير مشفرة لكنها موثّقة كـ Associated Data", { x: 0.6, y: 2.75, w: 6.4, h: 0.4, fontSize: 13, color: C.accent5, align: "left" });
  const pktRows = [
    [th("موثّق؟"), th("مشفر؟"), th("الوظيفة"), th("الحقل")],
    [td("✅", { align: "center" }), td("❌", { align: "center" }), td("رقم التسلسل: يبني الـ Nonce وتفحصه نافذة منع التكرار"), td("Sequence", { bold: true })],
    [td("✅", { align: "center" }), td("❌", { align: "center" }), td("رقم الإطار: ترتيب مخزن الارتعاش وحساب Jitter"), td("Frame #", { bold: true })],
    [td("✅", { align: "center" }), td("✅", { align: "center" }), td("الصوت المشفر بـ Ascon-128"), td("Ciphertext", { bold: true })],
    [td("—", { align: "center" }), td("—", { align: "center" }), td("وسم 128 بت يغطي الترويسة والصوت: أي تعديل = رفض"), td("Tag", { bold: true })],
  ];
  s.addTable(pktRows, tableOpts({ x: 0.6, y: 3.4, w: 7.9, colW: [0.9, 0.9, 4.6, 1.5], rowH: 0.5, fontSize: 13 }));
  const bw = [["666 B", "حجم الحزمة (PCM16)"], ["277.6", "kbit/s لكل اتجاه مع IP/UDP"], ["3.7%", "الحمل الأمني: 26 بايت فقط"]];
  for (let i = 0; i < 3; i++) {
    const y = 3.4 + i * 1.12;
    card(s, 8.8, y, 3.93, 0.98, "FFFBEB");
    T(s, bw[i][0], { x: 10.6, y: y + 0.1, w: 1.95, h: 0.78, fontSize: 28, bold: true, color: C.accent3, valign: "middle", rtlMode: false, align: "right" });
    T(s, bw[i][1], { x: 9.0, y: y + 0.1, w: 1.6, h: 0.78, fontSize: 12, valign: "middle" });
  }

  // ---------------------------------------------------------------- 13 Ascon internals
  s = newSlide("التشفير والبروتوكول");
  s.addText("Ascon-128 من الداخل (مكتوبة من الصفر في ascon.py)", { placeholder: "title" });
  img(s, "diagrams/08_ascon_structure.png", 0.6, 1.35, 8.3, 4.0, "بنية Ascon");
  const params = [["320 بت", "الحالة: 5 كلمات × 64"], ["64 بت", "معدل الامتصاص لكل كتلة"], ["12 / 6", "جولات التهيئة / البيانات"], ["128 بت", "المفتاح والـ Nonce والوسم"]];
  for (let i = 0; i < 4; i++) {
    const y = 1.35 + i * 1.02;
    card(s, 9.2, y, 3.53, 0.88);
    T(s, params[i][0], { x: 10.9, y: y + 0.1, w: 1.65, h: 0.68, fontSize: 22, bold: true, color: C.accent1, valign: "middle" });
    T(s, params[i][1], { x: 9.35, y: y + 0.1, w: 1.55, h: 0.68, fontSize: 12, valign: "middle" });
  }
  card(s, 0.6, 5.55, 12.13, 1.3, "ECFDF5");
  T(s, "الجولة = ثابت + صندوق استبدال 5-بت (AND/NOT/XOR فقط، بلا جداول بحث) + انتشار خطي بالتدوير", { x: 0.8, y: 5.65, w: 11.73, h: 0.45, fontSize: 15, bold: true, color: C.text1 });
  T(s, "التحقق: مطابقة متجه الاختبار الرسمي E355159F292911F794CB1432A0103A8A + المطابقة بايت ببايت مع التنفيذ المرجعي لمصممي الخوارزمية", { x: 0.8, y: 6.15, w: 11.73, h: 0.6, fontSize: 13 });
  s.addNotes("التنفيذ هو Ascon-128 v1.2 الفائز. المعيار SP 800-232 سماه Ascon-AEAD128 مع تعديلات طفيفة (ترتيب البايتات، معدل 128 بت) ونفس التبديل.");

  // ---------------------------------------------------------------- 14 Security
  pres.addSection({ title: "الأمان والبرنامج" });
  s = newSlide("الأمان والبرنامج");
  s.addText("التحليل الأمني: كل هجوم ودفاعه وطريقة إثباته", { placeholder: "title" });
  const sec = [
    [th("الإثبات أمام اللجنة"), th("الدفاع في النظام"), th("الهجوم")],
    [td("Wireshark + وضع المتنصت (ضجيج)"), td("Ascon-128 بمفتاح 128 بت لكل اتجاه"), td("التنصت", { bold: true })],
    [td("زر هجوم التعديل ← AUTH FAIL"), td("وسم AEAD 128 بت (احتمال التزوير 2⁻¹²⁸)"), td("قلب بت / تعديل", { bold: true })],
    [td("زر هجوم التزوير ← رفض"), td("بدون المفتاح لا يمكن إنتاج وسم صحيح"), td("حقن حزم مزيفة", { bold: true })],
    [td("زر إعادة الإرسال ← REPLAY"), td("رقم تسلسل + نافذة انزلاقية 64"), td("إعادة الإرسال", { bold: true })],
    [td("كلمة سر خاطئة ← فشل المصافحة"), td("PSK + Finished MAC + رمز SAS"), td("رجل في المنتصف", { bold: true })],
    [td("اختبار: مفاتيح جديدة لكل مكالمة"), td("X25519 مؤقت لكل مكالمة"), td("سرقة مفتاح لاحقاً", { bold: true })],
    [td("اختبار تفرد 9,999 Nonce"), td("IV ⊕ seq مع عداد لا يتكرر"), td("تكرار الـ Nonce", { bold: true })],
    [td("—"), td("مفتاح مختلف لكل اتجاه + transcript hash"), td("الانعكاس / خفض الخوارزمية", { bold: true })],
  ];
  s.addTable(sec, tableOpts({ x: 0.6, y: 1.4, w: 12.13, colW: [3.9, 4.73, 3.5], rowH: 0.56, fontSize: 13 }));
  T(s, "النتيجة في الاختبارات: رُفضت 100% من الحزم المعدّلة والمزوّرة والمكررة، واستمرت المكالمة الأصلية دون تأثر", { x: 0.6, y: 6.6, w: 12.13, h: 0.4, fontSize: 14, bold: true, color: C.accent1 });

  // ---------------------------------------------------------------- 15 App screenshot
  s = newSlide("الأمان والبرنامج");
  s.addText("البرنامج: واجهة عربية كاملة لنظام Windows", { placeholder: "title" });
  img(s, "04_in_call_monitor_A.png", 0.6, 1.3, 7.06, 5.62, "لقطة البرنامج أثناء مكالمة");
  const feats = [["مكالمة آمنة جارية", "الحالة، المؤقت، الطرف الآخر، الخوارزمية، زمن المصافحة"],
    ["رمز الأمان SAS", "يتطابق على الجهازين ← لا وسيط"],
    ["لوحة مراقبة حيّة", "12 مؤشراً: الحزم، معدل البت، زمن التشفير، RTT، الفقد، الهجمات"],
    ["رسوم بيانية حيّة", "معدل البت وزمن التشفير لحظة بلحظة"],
    ["7 تبويبات", "مراقبة، فاحص الحزم، الهجمات، الرسائل، المقارنة، السجل، حول"]];
  for (let i = 0; i < 5; i++) {
    const y = 1.35 + i * 1.1;
    card(s, 7.95, y, 4.78, 0.95);
    T(s, feats[i][0], { x: 8.15, y: y + 0.08, w: 4.38, h: 0.38, fontSize: 15, bold: true, color: C.text1 });
    T(s, feats[i][1], { x: 8.15, y: y + 0.46, w: 4.38, h: 0.45, fontSize: 12 });
  }

  // ---------------------------------------------------------------- 16 Attack demo screenshots
  s = newSlide("الأمان والبرنامج");
  s.addText("محاكاة الهجمات وفاحص الحزم داخل البرنامج", { placeholder: "title" });
  img(s, "07_attack_simulation.png", 6.73, 1.3, 6.0, 4.78, "تبويب محاكاة الهجمات");
  img(s, "06b_packet_inspector_rejected_only.png", 0.6, 1.3, 6.0, 4.78, "فاحص الحزم المرفوضة");
  T(s, "الجهاز B يطلق الهجمات: تعديل بت، تزوير بمفتاح عشوائي، إعادة 10 حزم قديمة", { x: 6.73, y: 6.2, w: 6.0, h: 0.6, fontSize: 13, align: "center" });
  T(s, "الجهاز A يرفضها: AUTH FAIL و REPLAY، مع النص الأصلي مقابل المشفر لكل حزمة", { x: 0.6, y: 6.2, w: 6.0, h: 0.6, fontSize: 13, align: "center" });

  // ---------------------------------------------------------------- 17 Tests
  pres.addSection({ title: "الاختبارات والنتائج" });
  s = newSlide("الاختبارات والنتائج");
  s.addText("الاختبارات الآلية: 48 من 48 ناجحة", { placeholder: "title" });
  card(s, 9.1, 1.45, 3.63, 2.3, "ECFDF5");
  T(s, "48 / 48", { x: 9.3, y: 1.6, w: 3.23, h: 1.1, fontSize: 48, bold: true, color: C.accent1, align: "center", valign: "middle", rtlMode: false });
  T(s, "اختبار ناجح على Windows و Linux (GitHub Actions)", { x: 9.3, y: 2.75, w: 3.23, h: 0.8, fontSize: 13, align: "center" });
  const tnotes = ["متجهات الاختبار الرسمية لـ Ascon-128", "مكالمات حقيقية عبر TCP/UDP: الصوت يصل مطابقاً بت ببت", "رفض كل هجوم مع استمرار المكالمة", "كلمة سر خاطئة ← لا مكالمة", "نافذتا برنامج حقيقيتان تُجريان مكالمة"];
  await iconList(s, tnotes, 9.1, 3.95, 3.63, 0.58, fa.FaCheck, HEX.accent1, 12);
  s.addChart(pres.charts.BAR, [{ name: "عدد الاختبارات", labels: ["الواجهة", "الصوت والحزم", "مكالمات حقيقية", "التشفير والمصافحة", "Ascon-128"], values: [1, 6, 10, 11, 20] }], {
    x: 0.6, y: 1.45, w: 8.2, h: 5.4, barDir: "bar", chartColors: [HEX.accent1], showValue: true, dataLabelPosition: "outEnd",
    dataLabelColor: HEX.dk2, dataLabelFontSize: 12, dataLabelFontFace: "+mn-lt", catAxisLabelColor: HEX.dk2, catAxisLabelFontSize: 13,
    catAxisLabelFontFace: "+mn-lt", valAxisHidden: true, valGridLine: { style: "none" }, catGridLine: { style: "none" },
    showLegend: false, showTitle: true, title: "توزيع الاختبارات حسب الطبقة", titleFontSize: 14, titleColor: HEX.dk2, titleFontFace: "+mn-lt",
    objectName: oname("chart"), altText: "توزيع الاختبارات",
  });

  // ---------------------------------------------------------------- 18 Performance
  s = newSlide("الاختبارات والنتائج");
  s.addText("أداء التشفير: الزمن الحقيقي متحقق بهامش كبير", { placeholder: "title" });
  s.addChart(pres.charts.BAR, [{ name: "زمن تشفير إطار 640 بايت (µs)", labels: ["AES-128-GCM", "ChaCha20-Poly1305", "Ascon-128"], values: [0.5, 1.9, 1152] }], {
    x: 4.5, y: 1.4, w: 8.23, h: 4.6, barDir: "col", chartColors: [HEX.accent3, HEX.accent2, HEX.accent1], invertedColors: [HEX.accent3, HEX.accent2, HEX.accent1],
    valAxisLogScaleBase: 10, valAxisMinVal: 0.01, showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: "0.0", dataLabelColor: HEX.dk2, dataLabelFontSize: 12,
    dataLabelFontFace: "+mn-lt", catAxisLabelColor: HEX.dk2, catAxisLabelFontSize: 13, catAxisLabelFontFace: "+mn-lt", valAxisLabelColor: "64748B",
    valAxisLabelFontSize: 11, valAxisLabelFontFace: "+mn-lt", valGridLine: { color: "E2E8F0", size: 0.5 }, catGridLine: { style: "none" },
    showLegend: false, showTitle: true, title: "زمن تشفير إطار 640 بايت (ميكروثانية، مقياس لوغاريتمي)", titleFontSize: 14, titleColor: HEX.dk2,
    titleFontFace: "+mn-lt", objectName: oname("chart"), altText: "زمن التشفير",
  });
  const perf = [["1.2 ms", "متوسط زمن تشفير إطار بـ Ascon-128"], ["≈ 11%", "من زمن الإطار المتاح (20ms) للتشفير + فك التشفير"], ["16 بايت", "الحمل الإضافي لكل حزمة لكل الخوارزميات"]];
  for (let i = 0; i < 3; i++) {
    const y = 1.4 + i * 1.6;
    card(s, 0.6, y, 3.6, 1.42, "ECFDF5");
    T(s, perf[i][0], { x: 0.8, y: y + 0.1, w: 3.2, h: 0.7, fontSize: 28, bold: true, color: C.accent1, valign: "middle" });
    T(s, perf[i][1], { x: 0.8, y: y + 0.8, w: 3.2, h: 0.55, fontSize: 12 });
  }
  T(s, "ملاحظة علمية: Ascon هنا بلغة Python خالصة (للشفافية والشرح)، بينما AES و ChaCha20 من OpenSSL بلغة C مع تسريع AES-NI. المقارنة العادلة بنفس اللغة والعتاد.",
    { x: 0.6, y: 6.2, w: 12.13, h: 0.65, fontSize: 13, color: C.accent6 });

  // ---------------------------------------------------------------- 19 Real call results
  s = newSlide("الاختبارات والنتائج");
  s.addText("نتائج مكالمات حقيقية (10 ثوانٍ لكل خوارزمية)", { placeholder: "title" });
  const kpis = [["0%", "فقد الحزم"], ["≈ 104 ms", "التأخير الكلي (< 150)"], ["≈ 25 ms", "زمن المصافحة"], ["499 / 501", "إطار مطابق بت ببت"]];
  for (let i = 0; i < 4; i++) {
    const x = 9.73 - i * 3.04;
    card(s, x, 1.4, 2.9, 1.65);
    T(s, kpis[i][0], { x: x + 0.1, y: 1.5, w: 2.7, h: 0.85, fontSize: 30, bold: true, color: C.accent2, align: "center", valign: "middle" });
    T(s, kpis[i][1], { x: x + 0.1, y: 2.4, w: 2.7, h: 0.5, fontSize: 13, align: "center" });
  }
  const e2e = [
    [th("Jitter"), th("RTT"), th("مطابق بت ببت"), th("مرفوضة"), th("مفقودة"), th("مستقبلة"), th("المصافحة"), th("الخوارزمية")],
    ["0.2 ms", "2.4 ms", "499", "0", "0", "501", "26 ms", "Ascon-128"],
    ["0.2 ms", "0.5 ms", "499", "0", "0", "502", "21 ms", "ChaCha20-Poly1305"],
    ["0.3 ms", "1.0 ms", "499", "0", "0", "502", "18 ms", "AES-128-GCM"],
  ].map((r, i) => i === 0 ? r : r.map((c, j) => td(c, { align: "center", bold: j === 7 })));
  s.addTable(e2e, tableOpts({ x: 0.6, y: 3.35, w: 12.13, colW: [1.25, 1.25, 1.6, 1.2, 1.2, 1.3, 1.5, 2.83], rowH: 0.55, fontSize: 14 }));
  T(s, "ميزانية التأخير: التقاط 20 + تشفير 1.3 + شبكة 1 + فك 1.4 + مخزن الارتعاش 60 + السماعة 20 ≈ 104 ms — مساهمة التشفير أقل من 3%",
    { x: 0.6, y: 5.75, w: 12.13, h: 0.5, fontSize: 14, bold: true, color: C.text1 });
  T(s, "عرض النطاق: 277.6 kbit/s لكل اتجاه (PCM16) أو 149.6 kbit/s (G.711 μ-law)", { x: 0.6, y: 6.3, w: 12.13, h: 0.45, fontSize: 14 });

  // ---------------------------------------------------------------- 20 Deliverables
  pres.addSection({ title: "التسليم والخطة" });
  s = newSlide("التسليم والخطة");
  s.addText("ما تم تسليمه في المستودع", { placeholder: "title" });
  const dels = [
    [fa.FaWindows, "برنامج Windows", "SecureVoice.exe يُبنى تلقائياً بـ GitHub Actions، أو تشغيل بـ run.bat"],
    [fa.FaCode, "الكود المصدري", "16 وحدة Python مقسمة على طبقات، مع Ascon-128 من الصفر"],
    [fa.FaVial, "48 اختباراً آلياً", "وحدات + تكامل + مكالمات حقيقية + واجهة"],
    [fa.FaBook, "توثيق عربي كامل", "12 ملفاً: التشفير، البروتوكول، الصوت، التثبيت، الأمان، العرض"],
    [fa.FaProjectDiagram, "12 مخططاً", "معمارية، Flowcharts، تسلسل المصافحة، الحالات، Ascon، الهجمات"],
    [fa.FaChartBar, "نتائج ورسوم", "مقارنة الخوارزميات، التأخير، عرض النطاق، 16 لقطة شاشة"],
  ];
  for (let i = 0; i < 6; i++) {
    const col = 2 - (i % 3), row = Math.floor(i / 3);
    const x = 0.6 + col * 4.11, y = 1.45 + row * 2.6;
    card(s, x, y, 3.91, 2.35);
    await iconCircle(s, dels[i][0], x + 3.91 - 1.0, y + 0.25, 0.75, C.accent2);
    T(s, dels[i][1], { x: x + 0.2, y: y + 0.35, w: 2.6, h: 0.55, fontSize: 17, bold: true, color: C.text1, valign: "middle" });
    T(s, dels[i][2], { x: x + 0.2, y: y + 1.15, w: 3.51, h: 1.05, fontSize: 13 });
  }

  // ---------------------------------------------------------------- 21 Demo plan
  s = newSlide("التسليم والخطة");
  s.addText("خطة العرض أمام اللجنة (≈ 12 دقيقة)", { placeholder: "title" });
  const demo = [["0:00", "المشكلة والحل"], ["2:00", "بدء المكالمة بين الجهازين"], ["3:00", "تطابق رمز الأمان"], ["3:30", "التحدث + لوحة المراقبة"],
    ["5:00", "فاحص الحزم + وضع المتنصت"], ["8:00", "هجمات: تعديل، إعادة، تزوير"], ["10:20", "كلمة سر خاطئة"], ["11:00", "المقارنة والنتائج"]];
  s.addShape(pres.shapes.LINE, { x: 0.9, y: 3.05, w: 11.5, h: 0, line: { color: "CBD5E1", width: 2 }, objectName: oname("timeline") });
  for (let i = 0; i < 8; i++) {
    const x = 11.6 - i * 1.53;
    s.addShape(pres.shapes.OVAL, { x: x + 0.38, y: 2.83, w: 0.44, h: 0.44, fill: { color: C.accent1 }, line: { color: C.background1, width: 2 }, objectName: oname("dot") });
    T(s, demo[i][0], { x, y: 2.2, w: 1.2, h: 0.4, fontSize: 14, bold: true, color: C.accent1, align: "center", rtlMode: false });
    T(s, demo[i][1], { x: x - 0.05, y: 3.45, w: 1.3, h: 1.0, fontSize: 13, align: "center", color: C.text1 });
  }
  card(s, 0.6, 4.85, 12.13, 1.9, "FEF2F2");
  T(s, "خطة بديلة يوم المناقشة", { x: 0.8, y: 4.98, w: 11.73, h: 0.4, fontSize: 16, bold: true, color: C.accent4 });
  T(s, "شبكة القاعة لا تعمل ← Hotspot الهاتف  •  جهاز واحد فقط ← نافذتان على 127.0.0.1 بمنفذ UDP 5002  •  صفير ← نغمة الاختبار بدل الميكروفون  •  تعطل كامل ← فيديو مسجل + صور + تشغيل الاختبارات أمام اللجنة",
    { x: 0.8, y: 5.45, w: 11.73, h: 1.2, fontSize: 14 });

  // ---------------------------------------------------------------- 22 Limitations & future
  s = newSlide("التسليم والخطة");
  s.addText("القيود والأعمال المستقبلية", { placeholder: "title" });
  const lim = ["المصادقة بكلمة سر مشتركة (عرضة للتخمين offline إذا كانت ضعيفة)", "Ascon بلغة Python أبطأ من تنفيذ C",
    "الاتصال على الشبكة المحلية فقط", "تنفيذ Ascon-128 v1.2 لا Ascon-AEAD128 النهائي", "ترويسة الحزمة مكشوفة (موثّقة لا مشفرة)"];
  const fut = ["بروتوكول PAKE (CPace / SPAKE2) أو شهادات رقمية", "تنفيذ النواة بلغة C/Rust (تسريع 50–100×)",
    "اجتياز NAT عبر STUN/TURN للعمل على الإنترنت", "الانتقال إلى SP 800-232 + ضغط Opus", "تطبيق هاتف + مكالمات جماعية + تجديد المفاتيح الدوري"];
  for (const [x, title, list, col, ic] of [[6.83, "القيود الحالية", lim, C.accent3, fa.FaExclamationTriangle], [0.6, "الأعمال المستقبلية", fut, C.accent1, fa.FaRocket]]) {
    card(s, x, 1.45, 5.9, 5.3);
    await iconCircle(s, ic, x + 4.95, 1.65, 0.7, col);
    T(s, title, { x: x + 0.3, y: 1.7, w: 4.5, h: 0.6, fontSize: 20, bold: true, color: C.text1, valign: "middle" });
    await iconList(s, list, x + 0.3, 2.65, 5.3, 0.78, fa.FaChevronLeft, col === C.accent3 ? HEX.accent3 : HEX.accent1, 15);
  }

  // ---------------------------------------------------------------- 23 Closing
  s = newSlide("التسليم والخطة", "SECTION_DARK");
  s.addText("الخلاصة", { placeholder: "title" });
  const fin = [["🔐", "Ascon-128 مكتوبة من الصفر ومُتحقق منها رسمياً تشفّر كل 20ms من الصوت"], ["🤝", "مصافحة X25519 + كلمة سر + رمز أمان: سرية أمامية ومصادقة متبادلة"],
    ["🛡", "رفض 100% من هجمات التعديل والتزوير وإعادة الإرسال و MITM"], ["⚡", "تأخير كلي ≈ 104ms وفقد 0% — مساهمة التشفير < 3%"], ["✅", "برنامج Windows جاهز + 48 اختباراً + توثيق عربي كامل"]];
  for (let i = 0; i < 5; i++) {
    const y = 1.5 + i * 0.92;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.6, y, w: 12.13, h: 0.78, rectRadius: 0.1, fill: { color: "1E293B" }, line: { color: "1E293B" }, objectName: oname("row") });
    T(s, fin[i][0], { x: 11.9, y: y + 0.12, w: 0.6, h: 0.55, fontSize: 22, align: "center", valign: "middle", color: C.background1, rtlMode: false });
    T(s, fin[i][1], { x: 0.85, y: y + 0.12, w: 10.9, h: 0.55, fontSize: 17, valign: "middle", color: C.background1 });
  }
  T(s, "github.com/blackangiliq/norhan_graduate_project", { x: 0.6, y: 6.35, w: 12.13, h: 0.45, fontSize: 15, color: "34D399", align: "center", rtlMode: false,
    hyperlink: { url: "https://github.com/blackangiliq/norhan_graduate_project" } });

  await pres.writeFile({ fileName: OUT });
  const applyThemePath = process.env.APPLY_THEME;
  if (applyThemePath) {
    const { applyTheme } = require(applyThemePath);
    await applyTheme(OUT, THEME);
  }
  console.log("written", OUT);
})().catch((e) => { console.error(e); process.exit(1); });
