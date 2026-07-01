const pptxgen = require("pptxgenjs");

const pres = new pptxgen();
pres.layout = "LAYOUT_16x9";
pres.title = "SliceMatic Digital Ordering System — PRD & Business Analysis";
pres.author = "Group 3";

// ─── Palette ──────────────────────────────────────────────────────────────
const P = {
  dark:    "2D3B1A",  // dark olive  — title / dark slides
  med:     "5C6E35",  // medium olive — headers, accents
  lightBg: "F2F5E8",  // light olive  — content slide backgrounds
  card:    "FFFFFF",  // card white
  oliveC:  "EBF0D9",  // olive card tint
  gold:    "C8922A",  // gold accent (cheese!)
  goldL:   "F5DFA0",  // light gold
  text:    "1E2A0F",  // dark body text
  muted:   "7A8F62",  // muted secondary text
  rowAlt:  "F7FAF0",  // alternating row
  errFill: "FAE8E8",  // error card fill
  errText: "7B2828",  // error text
};

// ─── Helpers ──────────────────────────────────────────────────────────────
const mkSh = () => ({ type: "outer", blur: 5, offset: 2, angle: 45, color: "000000", opacity: 0.10 });

function hdr(slide, title, sub) {
  slide.addText(title, {
    x: 0.5, y: 0.2, w: 9.0, h: 0.6,
    fontSize: 26, bold: true, color: P.dark,
    fontFace: "Cambria", align: "left", margin: 0
  });
  if (sub) {
    slide.addText(sub, {
      x: 0.5, y: 0.82, w: 9.0, h: 0.26,
      fontSize: 11, color: P.muted,
      fontFace: "Calibri", align: "left", margin: 0
    });
  }
}

function tblHdrCell(text, w) {
  return { text, options: { bold: true, fill: { color: P.dark }, color: P.card, fontSize: 11, fontFace: "Calibri", align: "center", valign: "middle" } };
}

function tblCell(text, opts) {
  return { text, options: { fontSize: 10, fontFace: "Calibri", valign: "middle", ...opts } };
}

// ══════════════════════════════════════════════════════════════════════════
// SLIDE 1 — Title
// ══════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: P.dark };

  // Decorative circles (pizza motif)
  s.addShape(pres.shapes.OVAL, { x: 7.0, y: -0.9, w: 5.0, h: 5.0, fill: { color: P.med, transparency: 68 } });
  s.addShape(pres.shapes.OVAL, { x: -1.0, y: 3.0, w: 3.8, h: 3.8, fill: { color: P.med, transparency: 72 } });
  s.addShape(pres.shapes.OVAL, { x: 8.6, y: 3.2, w: 2.2, h: 2.2, fill: { color: P.gold, transparency: 75 } });

  s.addText("SliceMatic", {
    x: 0.7, y: 0.6, w: 8.0, h: 1.25,
    fontSize: 54, bold: true, color: P.card,
    fontFace: "Cambria", align: "left", margin: 0, charSpacing: 2
  });
  s.addText("Digital Ordering System", {
    x: 0.7, y: 1.78, w: 7.5, h: 0.65,
    fontSize: 26, color: P.goldL, fontFace: "Cambria", align: "left", margin: 0
  });

  // Gold divider
  s.addShape(pres.shapes.RECTANGLE, { x: 0.7, y: 2.55, w: 3.8, h: 0.04, fill: { color: P.gold } });

  s.addText([
    { text: "PRD + Business Analysis  ·  Stage 1 Submission", options: { bold: true, breakLine: true } },
    { text: "New Ashok Nagar, Delhi  ·  Founder: Mr. Rajan Sharma", options: { breakLine: true } },
    { text: "Group 3  ·  June 23, 2026" }
  ], {
    x: 0.7, y: 2.7, w: 7.0, h: 1.5,
    fontSize: 14, color: "C5DBA0", fontFace: "Calibri", align: "left"
  });

  // Pizza emoji accent
  s.addText("🍕", {
    x: 7.2, y: 1.5, w: 2.2, h: 2.2,
    fontSize: 88, align: "center", valign: "middle"
  });

  // Reference link
  s.addText("🔗 Reference Business Economics Model (Google Drive)", {
    x: 0.7, y: 4.4, w: 6.0, h: 0.4,
    fontSize: 12, color: P.goldL, fontFace: "Calibri", align: "left",
    hyperlink: { url: "https://drive.google.com/file/d/1NfJnI0RF4q8gNfj6VryQtEuzq9XDseHJ/view?usp=sharing", tooltip: "Open Reference Model on Google Drive" }
  });
}

// ══════════════════════════════════════════════════════════════════════════
// SLIDE 2 — Problem & Vision
// ══════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: P.lightBg };

  // Left dark panel
  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 3.5, h: 5.625, fill: { color: P.dark } });
  s.addShape(pres.shapes.OVAL, { x: 0.1, y: 3.5, w: 3.1, h: 3.1, fill: { color: P.gold, transparency: 82 } });
  s.addText("The\nProblem\n& Vision", {
    x: 0.25, y: 0.45, w: 3.0, h: 2.2,
    fontSize: 28, bold: true, color: P.card, fontFace: "Cambria", align: "left", valign: "top"
  });
  s.addText("SliceMatic · Stage 1", {
    x: 0.25, y: 4.85, w: 3.0, h: 0.4,
    fontSize: 10, color: P.goldL, fontFace: "Calibri"
  });

  // Problem box
  s.addText("The Problem", { x: 3.8, y: 0.3, w: 5.8, h: 0.4, fontSize: 16, bold: true, color: P.med, fontFace: "Cambria", margin: 0 });
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 3.8, y: 0.76, w: 5.8, h: 0.72, fill: { color: P.errFill }, rectRadius: 0.06 });
  s.addText("Manual phone ordering — error-prone, slow, and leaves no data for business decisions.", {
    x: 3.95, y: 0.83, w: 5.5, h: 0.58, fontSize: 12, color: P.errText, fontFace: "Calibri"
  });

  // Solution cards
  s.addText("Our Solution — Solves Two Problems at Once", {
    x: 3.8, y: 1.62, w: 5.8, h: 0.38, fontSize: 14, bold: true, color: P.med, fontFace: "Cambria", margin: 0
  });

  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 3.8, y: 2.06, w: 2.75, h: 1.3, fill: { color: P.card }, rectRadius: 0.08, shadow: mkSh() });
  s.addText("🍕  Customer", { x: 3.95, y: 2.16, w: 2.45, h: 0.32, fontSize: 12, bold: true, color: P.med, fontFace: "Calibri" });
  s.addText("Fast, transparent, consistent ordering experience", { x: 3.95, y: 2.5, w: 2.45, h: 0.72, fontSize: 10, color: P.text, fontFace: "Calibri" });

  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 6.75, y: 2.06, w: 2.75, h: 1.3, fill: { color: P.card }, rectRadius: 0.08, shadow: mkSh() });
  s.addText("📊  Owner", { x: 6.9, y: 2.16, w: 2.45, h: 0.32, fontSize: 12, bold: true, color: P.med, fontFace: "Calibri" });
  s.addText("Operational consistency + order-level data to run unit economics", { x: 6.9, y: 2.5, w: 2.45, h: 0.72, fontSize: 10, color: P.text, fontFace: "Calibri" });

  // What it eliminates
  s.addText("What It Eliminates", { x: 3.8, y: 3.52, w: 5.8, h: 0.35, fontSize: 14, bold: true, color: P.med, fontFace: "Cambria", margin: 0 });
  s.addText([
    { text: "Manual GST math and pricing errors", options: { bullet: true, breakLine: true } },
    { text: "Staff tied to a phone line for every order", options: { bullet: true, breakLine: true } },
    { text: "Inconsistent billing and customer disputes", options: { bullet: true, breakLine: true } },
    { text: "Zero order data for any business decision", options: { bullet: true } },
  ], { x: 3.8, y: 3.92, w: 5.8, h: 1.45, fontSize: 12, color: P.text, fontFace: "Calibri" });
}

// ══════════════════════════════════════════════════════════════════════════
// SLIDE 3 — User Personas
// ══════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: P.lightBg };
  hdr(s, "Who We're Building For — User Personas", "Three stakeholders, three distinct needs");

  const personas = [
    {
      emoji: "🧑‍🍳", title: "Order-Taking Staff",
      role: "Counter / billing person",
      goal: "Take orders quickly and accurately; no manual math",
      need: "Guided step-by-step flow; automatic pricing, discount & GST",
      win: "No more slow phone orders or pricing mistakes"
    },
    {
      emoji: "🍕", title: "Customer",
      role: "Person ordering (18–35, within ~5 km)",
      goal: "Fast, transparent order with a clear, fair bill",
      need: "Quick ordering, itemised bill, consistent pricing",
      win: "No inconsistent quotes or billing disputes"
    },
    {
      emoji: "📊", title: "Owner / Admin",
      role: "Mr. Rajan Sharma — runs the outlet",
      goal: "Understand sales, margins & demand",
      need: "Structured record of every order for decisions",
      win: "No more operating blind on unit economics"
    }
  ];

  const cW = 2.95, cH = 3.95, startX = 0.43, gap = 0.17;
  personas.forEach((p, i) => {
    const x = startX + i * (cW + gap);
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 1.1, w: cW, h: cH, fill: { color: P.card }, rectRadius: 0.1, shadow: mkSh() });
    // Emoji
    s.addText(p.emoji, { x, y: 1.15, w: cW, h: 0.68, fontSize: 30, align: "center" });
    // Title band
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: x + 0.1, y: 1.9, w: cW - 0.2, h: 0.42, fill: { color: P.med }, rectRadius: 0.05 });
    s.addText(p.title, { x: x + 0.12, y: 1.92, w: cW - 0.24, h: 0.38, fontSize: 12, bold: true, color: P.card, fontFace: "Calibri", align: "center", valign: "middle", margin: 0 });
    // Fields
    const rows = [
      { label: "Role", val: p.role, y: 2.42 },
      { label: "Goal", val: p.goal, y: 2.85 },
      { label: "Needs", val: p.need, y: 3.35 },
    ];
    rows.forEach(r => {
      s.addText(r.label + ":", { x: x + 0.14, y: r.y, w: 0.55, h: 0.28, fontSize: 9, bold: true, color: P.med, fontFace: "Calibri", margin: 0 });
      s.addText(r.val, { x: x + 0.14, y: r.y + 0.26, w: cW - 0.28, h: 0.4, fontSize: 9, color: P.text, fontFace: "Calibri", margin: 0 });
    });
    // Win tag
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: x + 0.1, y: 4.22, w: cW - 0.2, h: 0.68, fill: { color: P.oliveC }, rectRadius: 0.05 });
    s.addText("✓  " + p.win, { x: x + 0.15, y: 4.25, w: cW - 0.3, h: 0.62, fontSize: 9, color: P.dark, fontFace: "Calibri", valign: "middle" });
  });
}

// ══════════════════════════════════════════════════════════════════════════
// SLIDE 4 — Scope: MVP vs Stage 3
// ══════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: P.lightBg };
  hdr(s, "Scope — MVP vs Stage 3", "Clear boundary: what we build now vs what comes next");

  const rows = [
    ["Capability", "MVP (Stage 2)", "Stage 3 (Full-Stack)"],
    ["Platform", "CLI / step-driven flow", "Web app (Vercel frontend + Supabase DB + Auth)"],
    ["Menu source", "3 .txt files at runtime", "Database tables — same data, served from Supabase"],
    ["Customer ordering", "Guided form: name → phone → selections → qty → pay", "Conversational chat ordering via LLM (OpenRouter)"],
    ["Validation & rules", "Full — name, phone, qty, selection, payment; discount + 18% GST", "Same rules enforced server-side"],
    ["Persistence", "Append to orders_log.txt (pipe-separated)", "Orders DB with IDs, transactions, backups, indexing"],
    ["Payment", "Mode selection + confirmation only", "Real payment gateway integration"],
    ["Admin / reporting", "Out of scope — raw log only", "Admin dashboard: login, order filters, revenue, CSV export"],
  ];

  const tblData = rows.map((row, ri) => {
    if (ri === 0) return row.map(cell => tblHdrCell(cell));
    const bg = ri % 2 === 0 ? P.oliveC : P.card;
    return [
      tblCell(row[0], { bold: true, color: P.dark, fill: { color: bg } }),
      tblCell(row[1], { color: P.text, fill: { color: bg } }),
      tblCell(row[2], { color: P.muted, italic: true, fill: { color: ri % 2 === 0 ? "F9F3E0" : "FEFDF5" } }),
    ];
  });

  s.addTable(tblData, {
    x: 0.45, y: 1.15, w: 9.1, h: 4.2,
    colW: [2.1, 3.3, 3.7],
    border: { pt: 0.5, color: "D5DEC5" },
    rowH: 0.5
  });
}

// ══════════════════════════════════════════════════════════════════════════
// SLIDE 5 — Functional Requirements
// ══════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: P.lightBg };
  hdr(s, "Functional Requirements", "8 requirement groups — precise enough to build from without ambiguity");

  const frs = [
    { id: "FR1", title: "Customer Intake", desc: "Name: alphabets+spaces, 2–40 chars\nPhone: 10 digits, starts with 6/7/8/9" },
    { id: "FR2", title: "Menu Loading", desc: "3 .txt files at startup; no hardcoded items; defensive line parsing" },
    { id: "FR3", title: "Item Selection", desc: "One Base + one Pizza + one Topping; by item number only" },
    { id: "FR4", title: "Quantity", desc: "Integer 1–10 only; 10% discount auto-applied at qty ≥ 5" },
    { id: "FR5", title: "Pricing Engine", desc: "Unit price → Subtotal → Discount → GST 18% → Total payable" },
    { id: "FR6", title: "Itemised Bill", desc: "Aligned table; discount + GST + final total clearly marked" },
    { id: "FR7", title: "Payment Modes", desc: "Cash / Card / UPI; confirmation per mode; invalid rejected" },
    { id: "FR8", title: "Order Persistence", desc: "Pipe-separated log; all fields; one block per order; appended" },
  ];

  const cW = 4.42, cH = 0.9, gX = 0.16, gY = 0.14;
  const startX = 0.45, startY = 1.18;

  frs.forEach((fr, i) => {
    const col = i % 2, row = Math.floor(i / 2);
    const x = startX + col * (cW + gX);
    const y = startY + row * (cH + gY);
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w: cW, h: cH, fill: { color: P.card }, rectRadius: 0.07, shadow: mkSh() });
    // ID badge
    s.addShape(pres.shapes.OVAL, { x: x + 0.12, y: y + 0.23, w: 0.42, h: 0.42, fill: { color: P.med } });
    s.addText(fr.id, { x: x + 0.12, y: y + 0.24, w: 0.42, h: 0.42, fontSize: 9, bold: true, color: P.card, fontFace: "Calibri", align: "center", valign: "middle", margin: 0 });
    s.addText(fr.title, { x: x + 0.64, y: y + 0.07, w: cW - 0.76, h: 0.32, fontSize: 13, bold: true, color: P.dark, fontFace: "Cambria", margin: 0 });
    s.addText(fr.desc, { x: x + 0.64, y: y + 0.42, w: cW - 0.76, h: 0.42, fontSize: 10, color: P.muted, fontFace: "Calibri", margin: 0 });
  });
}

// ══════════════════════════════════════════════════════════════════════════
// SLIDE 6 — Pricing Engine FR5
// ══════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: P.lightBg };
  hdr(s, "Pricing Engine — FR5", "Six deterministic steps — reproducible on every order; no manual calculation");

  const steps = [
    { n: 1, label: "Unit Price", formula: "Base + Pizza\n+ Topping" },
    { n: 2, label: "Subtotal", formula: "Unit Price\n× Quantity" },
    { n: 3, label: "Discount", formula: "10% if Qty ≥ 5\nelse ₹0" },
    { n: 4, label: "Taxable", formula: "Subtotal\n− Discount" },
    { n: 5, label: "GST", formula: "18% of\nTaxable" },
    { n: 6, label: "Total", formula: "Taxable\n+ GST" },
  ];

  const bW = 1.44, bH = 0.88, startX = 0.38, bY = 1.2;
  steps.forEach((st, i) => {
    const x = startX + i * (bW + 0.12);
    const isLast = i === 5;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: bY, w: bW, h: bH, fill: { color: isLast ? P.med : P.card }, rectRadius: 0.08, shadow: mkSh() });
    s.addShape(pres.shapes.OVAL, { x: x + bW / 2 - 0.19, y: bY - 0.21, w: 0.38, h: 0.38, fill: { color: isLast ? P.gold : P.dark } });
    s.addText(String(st.n), { x: x + bW / 2 - 0.19, y: bY - 0.21, w: 0.38, h: 0.38, fontSize: 11, bold: true, color: P.card, fontFace: "Calibri", align: "center", valign: "middle", margin: 0 });
    s.addText(st.label, { x, y: bY + 0.06, w: bW, h: 0.32, fontSize: 13, bold: true, color: isLast ? P.card : P.dark, fontFace: "Cambria", align: "center", margin: 0 });
    s.addText(st.formula, { x, y: bY + 0.42, w: bW, h: 0.4, fontSize: 9, color: isLast ? P.goldL : P.muted, fontFace: "Calibri", align: "center", margin: 0 });
    if (i < 5) {
      s.addShape(pres.shapes.LINE, { x: x + bW + 0.01, y: bY + bH / 2, w: 0.11, h: 0, line: { color: P.med, width: 1.5 } });
    }
  });

  // Worked example
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.38, y: 2.35, w: 9.24, h: 3.05, fill: { color: P.dark }, rectRadius: 0.1 });
  s.addText("Worked Example", { x: 0.65, y: 2.47, w: 4.0, h: 0.38, fontSize: 14, bold: true, color: P.goldL, fontFace: "Cambria", margin: 0 });

  const exRows = [
    [tblHdrCell("Component"), tblHdrCell("Calculation"), tblHdrCell("Amount (₹)")],
    ...[
      ["Base: Cheese Burst",    "—",                       "229.00"],
      ["Pizza: BBQ Chicken",    "—",                       "379.00"],
      ["Topping: Extra Cheese", "—",                       "69.00"],
      ["Unit price",            "229 + 379 + 69",          "677.00"],
      ["Subtotal (Qty 5)",      "677 × 5",                 "3,385.00"],
      ["Discount 10%",          "Qty ≥ 5  →  10% off",    "− 338.50"],
      ["Taxable amount",        "3,385 − 338.50",          "3,046.50"],
      ["GST @ 18%",             "18% × 3,046.50",          "548.37"],
      ["Total Payable",         "Taxable + GST",           "3,594.87"],
    ].map((r, ri) => {
      const isTotal = ri === 8, isDisc = ri === 5;
      const bg = isTotal ? P.med : (ri % 2 === 0 ? "394822" : "2D3B1A");
      return [
        tblCell(r[0], { bold: isTotal, color: isTotal ? P.goldL : "C5DBA0", fill: { color: bg } }),
        tblCell(r[1], { color: isTotal ? P.goldL : "A8C87A", italic: !isTotal, fill: { color: bg } }),
        tblCell(r[2], { bold: true, color: isDisc ? "E87E7E" : (isTotal ? P.goldL : P.goldL), align: "right", fill: { color: bg } }),
      ];
    })
  ];

  s.addTable(exRows, {
    x: 0.52, y: 2.9, w: 9.0, h: 2.35,
    colW: [2.7, 3.6, 2.7],
    border: { pt: 0.5, color: "4A6030" },
    rowH: 0.22
  });
}

// ══════════════════════════════════════════════════════════════════════════
// SLIDE 7 — Non-Functional Requirements & Edge Cases
// ══════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: P.lightBg };
  hdr(s, "Non-Functional Requirements & Edge Cases", "All 8 edge cases handled gracefully — zero unhandled exceptions, ever");

  const edges = [
    { n: 1, title: "Name only spaces",          fix: "Reject — not a valid name; re-prompt" },
    { n: 2, title: "Phone starting with 1",     fix: "Reject — require first digit 6/7/8/9" },
    { n: 3, title: "Qty = 0 or 11",             fix: "Reject — require integer 1–10" },
    { n: 4, title: "Item = 0 or > menu length", fix: "Reject — require in-range number" },
    { n: 5, title: "Price as item number",      fix: "Reject if out of range — invalid" },
    { n: 6, title: "Empty input at any step",   fix: "Reject — re-prompt with guidance" },
    { n: 7, title: "Non-integer qty (e.g. 2.5)", fix: "Reject — require strict integer" },
    { n: 8, title: "Missing price in file",     fix: "Skip line defensively — no crash" },
  ];

  const cW = 2.2, cH = 0.9, cols = 4, gX = 0.13, gY = 0.15, startX = 0.4, startY = 1.2;
  edges.forEach((ec, i) => {
    const col = i % cols, row = Math.floor(i / cols);
    const x = startX + col * (cW + gX), y = startY + row * (cH + gY);
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w: cW, h: cH, fill: { color: P.card }, rectRadius: 0.07, shadow: mkSh() });
    s.addShape(pres.shapes.OVAL, { x: x + 0.1, y: y + 0.08, w: 0.36, h: 0.36, fill: { color: P.gold } });
    s.addText(String(ec.n), { x: x + 0.1, y: y + 0.09, w: 0.36, h: 0.36, fontSize: 11, bold: true, color: P.dark, fontFace: "Calibri", align: "center", valign: "middle", margin: 0 });
    s.addText(ec.title, { x: x + 0.54, y: y + 0.08, w: cW - 0.64, h: 0.36, fontSize: 10, bold: true, color: P.dark, fontFace: "Calibri", margin: 0 });
    s.addText(ec.fix, { x: x + 0.12, y: y + 0.5, w: cW - 0.22, h: 0.34, fontSize: 9, color: P.muted, fontFace: "Calibri", margin: 0 });
  });

  // Footer bar
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.4, y: 4.6, w: 9.2, h: 0.75, fill: { color: P.oliveC }, rectRadius: 0.07 });
  s.addText([
    { text: "Defensive parsing  ", options: { bold: true } },
    { text: "Strip whitespace · Validate numeric price · Skip malformed lines      ", options: {} },
    { text: "Graceful exit  ", options: { bold: true } },
    { text: "Missing file = clear error + exit — never a stack trace", options: {} },
  ], { x: 0.6, y: 4.67, w: 9.0, h: 0.62, fontSize: 11, color: P.dark, fontFace: "Calibri", valign: "middle" });
}

// ══════════════════════════════════════════════════════════════════════════
// SLIDE 8 — User Flow
// ══════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: P.lightBg };
  hdr(s, "User Flow — Ordering Journey", "From launch to confirmed order — every step loops back on invalid input");

  const steps = [
    { label: "Launch &\nLoad Files", sub: "Missing file\n→ graceful exit", dark: true },
    { label: "Customer\nIntake", sub: "Name + Phone\nvalidation", dark: false },
    { label: "Menu\nSelection", sub: "Base → Pizza\n→ Topping", dark: false },
    { label: "Qty &\nBill", sub: "Validate qty\nCompute bill", dark: false },
    { label: "Payment\nMode", sub: "Cash / Card\n/ UPI", dark: false },
    { label: "Save &\nConfirm", sub: "Append log\nOrder confirmed", dark: true },
  ];

  const bW = 1.38, bH = 0.92, startX = 0.33, bY = 1.52, gap = 0.28;
  steps.forEach((st, i) => {
    const x = startX + i * (bW + gap);
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: bY, w: bW, h: bH, fill: { color: st.dark ? P.dark : P.card }, rectRadius: 0.1, shadow: mkSh() });
    s.addText(st.label, { x, y: bY + 0.06, w: bW, h: 0.44, fontSize: 11, bold: true, color: st.dark ? P.card : P.dark, fontFace: "Calibri", align: "center", margin: 0 });
    s.addText(st.sub, { x, y: bY + 0.5, w: bW, h: 0.38, fontSize: 8.5, color: st.dark ? P.goldL : P.muted, fontFace: "Calibri", align: "center", margin: 0 });
    if (i < 5) {
      s.addShape(pres.shapes.LINE, { x: x + bW + 0.02, y: bY + bH / 2, w: gap - 0.04, h: 0, line: { color: P.med, width: 1.5 } });
    }
    // Dashed error branch
    s.addShape(pres.shapes.LINE, { x: x + bW / 2, y: bY + bH, w: 0, h: 0.28, line: { color: "C0392B", width: 1, dashType: "dash" } });
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: x - 0.12, y: bY + bH + 0.28, w: bW + 0.24, h: 0.5, fill: { color: P.errFill }, rectRadius: 0.05 });
    s.addText("Error → Re-prompt", { x: x - 0.08, y: bY + bH + 0.31, w: bW + 0.16, h: 0.44, fontSize: 8.5, color: P.errText, fontFace: "Calibri", align: "center", margin: 0 });
  });

  s.addText("Every decision node loops back on invalid input — the system never crashes under any user input.", {
    x: 0.5, y: 5.25, w: 9.0, h: 0.28,
    fontSize: 10, color: P.muted, fontFace: "Calibri", align: "center", italic: true
  });
}

// ══════════════════════════════════════════════════════════════════════════
// SLIDE 9 — Drawbacks & Risk Analysis
// ══════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: P.lightBg };
  hdr(s, "Drawbacks & Risk Analysis", "Honest assessment of MVP limitations — and what Stage 3 resolves");

  s.addText("Architectural Limitations", { x: 0.4, y: 1.05, w: 4.3, h: 0.35, fontSize: 14, bold: true, color: P.med, fontFace: "Cambria", margin: 0 });
  s.addText([
    { text: "Flat-file storage doesn't scale past ~1,000 orders (no indexing, no concurrency control)", options: { bullet: true, breakLine: true } },
    { text: "Single-session: simultaneous writes can interleave and corrupt the log", options: { bullet: true, breakLine: true } },
    { text: "No menu version tracking in the log — past orders can't tie back to a price", options: { bullet: true, breakLine: true } },
    { text: "No true cart — one Base + Pizza + Topping × qty per order only", options: { bullet: true, breakLine: true } },
    { text: "Card/UPI: mode selection and confirmation only — no live payment gateway", options: { bullet: true } },
  ], { x: 0.4, y: 1.45, w: 4.35, h: 2.15, fontSize: 10.5, color: P.text, fontFace: "Calibri" });

  // Risk table
  s.addText("Risk Register", { x: 5.0, y: 1.05, w: 4.6, h: 0.35, fontSize: 14, bold: true, color: P.med, fontFace: "Cambria", margin: 0 });
  const risks = [
    ["R1", "Log corruption",      "Low",  "Append-only single-session design"],
    ["R2", "Malformed menu file", "Med",  "Defensive parsing → graceful exit"],
    ["R3", "Pricing error",       "Low",  "Single engine + worked-example test"],
    ["R4", "PII in plaintext",    "High", "Acknowledged → Stage 3 auth DB"],
    ["R5", "Data loss, no backup","Med",  "Interim file backup; DB in Stage 3"],
  ];
  const lColors = { Low: "27AE60", Med: "E67E22", High: "C0392B" };

  const riskTbl = [
    ["ID", "Risk", "Likelihood", "Mitigation"].map(t => tblHdrCell(t)),
    ...risks.map((r, ri) => {
      const bg = ri % 2 === 0 ? P.oliveC : P.card;
      return [
        tblCell(r[0], { bold: true, color: P.dark, fill: { color: bg } }),
        tblCell(r[1], { color: P.text, fill: { color: bg } }),
        tblCell(r[2], { bold: true, color: P.card, align: "center", fill: { color: lColors[r[2]] } }),
        tblCell(r[3], { color: P.muted, fill: { color: bg } }),
      ];
    })
  ];

  s.addTable(riskTbl, {
    x: 5.0, y: 1.45, w: 4.6, h: 2.2,
    colW: [0.42, 1.28, 0.82, 2.08],
    border: { pt: 0.5, color: "D5DEC5" },
    rowH: 0.37
  });

  // Resolution banner
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.4, y: 3.82, w: 9.2, h: 1.55, fill: { color: P.dark }, rectRadius: 0.1 });
  s.addText("Stage 3 Resolves All Architectural Risks", { x: 0.65, y: 3.92, w: 5.0, h: 0.36, fontSize: 13, bold: true, color: P.goldL, fontFace: "Cambria", margin: 0 });
  s.addText([
    { text: "PostgreSQL (Supabase)  ", options: { bold: true } },
    { text: "→ Indexed, concurrent-write-safe, queryable      " },
    { text: "Supabase Auth  ", options: { bold: true } },
    { text: "→ PII protected, authenticated dashboard      " },
    { text: "Managed backups  ", options: { bold: true } },
    { text: "→ No single point of data loss" },
  ], { x: 0.65, y: 4.33, w: 8.8, h: 0.85, fontSize: 11, color: "C5DBA0", fontFace: "Calibri", valign: "middle" });
}

// ══════════════════════════════════════════════════════════════════════════
// SLIDE 10 — Cost vs Value
// ══════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: P.lightBg };
  hdr(s, "Cost vs Value Analysis", "~21–28 hours of build effort produces capabilities the business currently has none of");

  // Effort table
  s.addText("Build Effort — MVP (Stage 2)", { x: 0.4, y: 1.05, w: 4.3, h: 0.35, fontSize: 14, bold: true, color: P.med, fontFace: "Cambria", margin: 0 });
  const effort = [
    ["Work Item", "Hrs"],
    ["Menu file loader + defensive parsing", "3–4"],
    ["Input validation (name, phone, qty, etc.)", "4–5"],
    ["Pricing engine (discount + GST + rounding)", "2–3"],
    ["Bill rendering (structured table)", "2–3"],
    ["Payment flow + confirmations", "1–2"],
    ["Order persistence (parseable log)", "2"],
    ["Edge-case hardening + testing", "4–5"],
    ["UI assembly / step-driven flow", "3–4"],
    ["TOTAL", "~21–28"],
  ];
  const effortTbl = effort.map((r, ri) => {
    const isH = ri === 0, isT = ri === effort.length - 1;
    const bg = isH ? P.dark : (isT ? P.goldL : (ri % 2 === 0 ? P.oliveC : P.card));
    return r.map((cell, ci) => tblCell(cell, {
      bold: isH || isT,
      color: isH ? P.card : (isT ? P.dark : P.text),
      align: ci === 1 ? "center" : "left",
      fill: { color: bg }
    }));
  });
  s.addTable(effortTbl, { x: 0.4, y: 1.45, w: 4.3, h: 3.85, colW: [3.3, 1.0], border: { pt: 0.5, color: "D5DEC5" }, rowH: 0.37 });

  // Value cards
  s.addText("Value Delivered", { x: 5.05, y: 1.05, w: 4.55, h: 0.35, fontSize: 14, bold: true, color: P.med, fontFace: "Cambria", margin: 0 });
  const vals = [
    { icon: "⚙️", label: "Operational", desc: "Eliminates manual billing errors; frees counter staff from phone ordering" },
    { icon: "📊", label: "Data", desc: "Every order captured → enables AOV, peak-hour, break-even tracking from Day 1" },
    { icon: "🍕", label: "Customer", desc: "Faster ordering, transparent itemised bill, consistent discount application" },
    { icon: "🚀", label: "Strategic", desc: "Order log is the foundation for Stage 3 dashboard and AI recommendation features" },
  ];
  vals.forEach((v, i) => {
    const y = 1.45 + i * 0.96;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 5.05, y, w: 4.55, h: 0.82, fill: { color: P.card }, rectRadius: 0.07, shadow: mkSh() });
    s.addText(v.icon + "  " + v.label, { x: 5.2, y: y + 0.07, w: 4.2, h: 0.28, fontSize: 12, bold: true, color: P.dark, fontFace: "Calibri", margin: 0 });
    s.addText(v.desc, { x: 5.2, y: y + 0.38, w: 4.2, h: 0.36, fontSize: 9.5, color: P.muted, fontFace: "Calibri", margin: 0 });
  });
}

// ══════════════════════════════════════════════════════════════════════════
// SLIDE 11 — Business Unit Economics
// ══════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: P.lightBg };
  hdr(s, "Business Unit Economics — Key Numbers", "Baseline at 60% capacity (47 orders/day) · All figures ex-GST");

  const stats = [
    { val: "₹847",   lbl: "Avg Order Value",     sub: "Weekday ₹792 · Weekend ₹940" },
    { val: "₹9.96L", lbl: "Monthly Revenue",      sub: "@ 60% capacity" },
    { val: "76%",    lbl: "Contribution Margin",  sub: "₹644 per order" },
    { val: "58.9%",  lbl: "Operating Margin",     sub: "EBITDA ₹7.0L/mo" },
  ];
  const sW = 2.2, sH = 1.08, sY = 1.12, sX = 0.4;
  stats.forEach((st, i) => {
    const x = sX + i * (sW + 0.13);
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: sY, w: sW, h: sH, fill: { color: P.dark }, rectRadius: 0.1 });
    s.addText(st.val, { x, y: sY + 0.08, w: sW, h: 0.52, fontSize: 28, bold: true, color: P.goldL, fontFace: "Cambria", align: "center", margin: 0 });
    s.addText(st.lbl, { x, y: sY + 0.6, w: sW, h: 0.26, fontSize: 10, bold: true, color: P.card, fontFace: "Calibri", align: "center", margin: 0 });
    s.addText(st.sub, { x, y: sY + 0.86, w: sW, h: 0.18, fontSize: 8, color: P.muted, fontFace: "Calibri", align: "center", margin: 0 });
  });

  // COGS table
  s.addText("COGS per Pizza", { x: 0.4, y: 2.42, w: 4.5, h: 0.35, fontSize: 13, bold: true, color: P.med, fontFace: "Cambria", margin: 0 });
  const cogsTbl = [
    ["Pizza Type", "COGS", "Sell Price", "GM %"].map(t => tblHdrCell(t)),
    ...([
      ["Margherita (Thin)",  "₹136", "₹397", "65.7%"],
      ["Farm House (Thick)", "₹163", "₹417", "60.9%"],
      ["Cheese Burst",       "₹219", "₹447", "51.0%"],
      ["Menu Average",       "₹170", "₹420", "59.5%"],
    ].map((r, ri) => {
      const bg = ri % 2 === 0 ? P.oliveC : P.card;
      return [
        tblCell(r[0], { bold: ri === 3, color: P.dark, fill: { color: bg } }),
        tblCell(r[1], { color: P.text, align: "center", fill: { color: bg } }),
        tblCell(r[2], { color: P.text, align: "center", fill: { color: bg } }),
        tblCell(r[3], { bold: true, color: "27AE60", align: "center", fill: { color: bg } }),
      ];
    }))
  ];
  s.addTable(cogsTbl, { x: 0.4, y: 2.82, w: 4.5, h: 2.45, colW: [1.9, 0.8, 1.0, 0.8], border: { pt: 0.5, color: "D5DEC5" }, rowH: 0.46 });

  // Fixed cost summary
  s.addText("Monthly Fixed Costs  ₹2,02,910", { x: 5.15, y: 2.42, w: 4.45, h: 0.35, fontSize: 13, bold: true, color: P.med, fontFace: "Cambria", margin: 0 });
  const fcItems = [
    ["Labour (all staff + 2 riders)", "₹94,500", "47%"],
    ["Kitchen Rent",                   "₹55,000", "27%"],
    ["Equipment EMI",                  "₹14,500",  "7%"],
    ["Utilities (electricity + gas)",  "₹18,150",  "9%"],
    ["Marketing + Tech + Misc",        "₹20,760", "10%"],
    ["TOTAL",                          "₹2,02,910","100%"],
  ];
  const fcTbl = [
    ["Item", "₹/mo", "%"].map(t => tblHdrCell(t)),
    ...fcItems.map((r, ri) => {
      const bg = ri === fcItems.length - 1 ? P.goldL : (ri % 2 === 0 ? P.oliveC : P.card);
      return r.map((cell, ci) => tblCell(cell, {
        bold: ri === fcItems.length - 1,
        color: ri === fcItems.length - 1 ? P.dark : P.text,
        align: ci === 0 ? "left" : "center",
        fill: { color: bg }
      }));
    })
  ];
  s.addTable(fcTbl, { x: 5.15, y: 2.82, w: 4.45, h: 2.45, colW: [2.6, 1.1, 0.75], border: { pt: 0.5, color: "D5DEC5" }, rowH: 0.38 });
}

// ══════════════════════════════════════════════════════════════════════════
// SLIDE 12 — Break-Even Analysis
// ══════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: P.lightBg };
  hdr(s, "Break-Even Analysis", "Fixed costs ÷ contribution margin — and the safety margin we operate with");

  const beNums = [
    { lbl: "Fixed Costs / Month",         val: "₹2,02,910",    key: false },
    { lbl: "Contribution Margin / Order", val: "₹644  (76%)",  key: false },
    { lbl: "Break-Even Orders / Month",   val: "315 orders",   key: false },
    { lbl: "Break-Even Orders / Day",     val: "11 orders/day", key: true  },
    { lbl: "Plan — 60% Capacity",         val: "47 orders/day", key: false },
    { lbl: "Safety Margin at Plan",       val: "4.3× break-even", key: true },
    { lbl: "Payback Period",              val: "~18 months",    key: false },
  ];
  beNums.forEach((n, i) => {
    const y = 1.1 + i * 0.55;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.4, y, w: 3.9, h: 0.46, fill: { color: n.key ? P.dark : P.card }, rectRadius: 0.06, shadow: n.key ? undefined : mkSh() });
    s.addText(n.lbl, { x: 0.55, y: y + 0.06, w: 2.15, h: 0.34, fontSize: 9.5, color: n.key ? P.goldL : P.muted, fontFace: "Calibri", valign: "middle", margin: 0 });
    s.addText(n.val, { x: 2.72, y: y + 0.06, w: 1.44, h: 0.34, fontSize: 12, bold: true, color: n.key ? P.goldL : P.dark, fontFace: "Calibri", align: "right", valign: "middle", margin: 0 });
  });
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.4, y: 5.08, w: 3.9, h: 0.32, fill: { color: P.oliveC }, rectRadius: 0.05 });
  s.addText("GST is a pass-through — customer pays, SliceMatic remits. P&L always ex-GST.", {
    x: 0.52, y: 5.1, w: 3.7, h: 0.28, fontSize: 8.5, color: P.muted, fontFace: "Calibri", italic: true
  });

  // Bar chart
  s.addChart(pres.charts.BAR, [
    { name: "Orders / Day", labels: ["Break-Even", "Plan (60% cap)", "Max Capacity"], values: [11, 47, 80] }
  ], {
    x: 4.5, y: 1.05, w: 5.1, h: 4.3,
    barDir: "col",
    chartColors: [P.gold, P.med, P.dark],
    chartArea: { fill: { color: P.lightBg }, roundedCorners: true },
    catAxisLabelColor: P.text,
    valAxisLabelColor: P.muted,
    valGridLine: { color: "D5DEC5", size: 0.5 },
    catGridLine: { style: "none" },
    showValue: true,
    dataLabelColor: P.dark,
    dataLabelFontSize: 12,
    showLegend: false,
    showTitle: true,
    title: "Daily Orders: Break-Even vs Plan vs Capacity",
    titleFontSize: 11,
    titleColor: P.med
  });
}

// ══════════════════════════════════════════════════════════════════════════
// SLIDE 13 — Business Economics: Cost & Order Breakdown
// ══════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: P.lightBg };
  hdr(s, "Business Economics — Cost & Order Breakdown", "Visualizing monthly fixed cost composition and per-order profit/cost split");

  // Chart 1: Monthly Fixed Costs Composition
  const dataFixedCosts = [
    {
      name: "Fixed Costs",
      labels: ["Rent", "Labour", "Utilities", "Equipment EMI", "Marketing", "Misc / contingency", "Packaging", "Tech"],
      values: [55000, 94500, 18150, 14500, 8000, 5760, 4200, 2800]
    }
  ];

  s.addChart(pres.charts.PIE, dataFixedCosts, {
    x: 0.5, y: 1.2, w: 4.3, h: 3.9,
    showLabel: true,
    showPercent: true,
    showValue: false,
    showLegend: true,
    legendPos: "b",
    legendFontSize: 8,
    chartColors: [P.dark, P.med, P.gold, P.muted, "8C9E68", P.goldL, "C5DBA0", "EBF0D9"],
    dataLabelColor: "FFFFFF",
    dataLabelFontSize: 9,
    showTitle: true,
    title: "Monthly Fixed Costs: ₹2,02,910",
    titleFontSize: 12,
    titleColor: P.dark
  });

  // Chart 2: Per-Order Economics
  const dataPerOrder = [
    {
      name: "Per-Order Economics",
      labels: ["Contribution Margin", "Ingredient COGS", "Delivery Variable", "Packaging", "Gateway Fee"],
      values: [644, 148, 22, 18, 15]
    }
  ];

  s.addChart(pres.charts.PIE, dataPerOrder, {
    x: 5.2, y: 1.2, w: 4.3, h: 3.9,
    showLabel: true,
    showPercent: true,
    showValue: false,
    showLegend: true,
    legendPos: "b",
    legendFontSize: 8,
    chartColors: [P.med, P.gold, P.dark, "8C9E68", "EBF0D9"],
    dataLabelColor: "FFFFFF",
    dataLabelFontSize: 9,
    showTitle: true,
    title: "Where each ₹847 order goes (AOV)",
    titleFontSize: 12,
    titleColor: P.dark
  });
}

// ══════════════════════════════════════════════════════════════════════════
// SLIDE 14 — Business Economics: Margins & Revenue
// ══════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: P.lightBg };
  hdr(s, "Business Economics — Margins & Revenue", "Analyzing gross margins by pizza type and weekday vs weekend revenue potential");

  // Chart 1: Gross Margin % by Pizza Type
  const dataMargins = [
    {
      name: "Gross Margin %",
      labels: ["Margherita (Thin)", "Farm House (Thick)", "Cheese Burst (Premium)"],
      values: [65.7, 60.9, 51.0]
    }
  ];

  s.addChart(pres.charts.BAR, dataMargins, {
    x: 0.5, y: 1.2, w: 4.3, h: 3.9,
    barDir: "col",
    chartColors: [P.med],
    showValue: true,
    dataLabelFontSize: 11,
    dataLabelColor: P.text,
    catAxisLabelColor: P.text,
    valAxisLabelColor: P.muted,
    valGridLine: { color: "D5DEC5", size: 0.5 },
    catGridLine: { style: "none" },
    showLegend: false,
    showTitle: true,
    title: "Gross Margin % by Pizza Type",
    titleFontSize: 12,
    titleColor: P.dark
  });

  // Chart 2: Daily Revenue Weekday vs Weekend
  const dataRevenue = [
    {
      name: "Daily Revenue (₹)",
      labels: ["Weekday", "Weekend / Holiday"],
      values: [30096, 63920]
    }
  ];

  s.addChart(pres.charts.BAR, dataRevenue, {
    x: 5.2, y: 1.2, w: 4.3, h: 3.9,
    barDir: "col",
    chartColors: [P.gold, P.dark],
    showValue: true,
    dataLabelFontSize: 11,
    dataLabelColor: P.card,
    catAxisLabelColor: P.text,
    valAxisLabelColor: P.muted,
    valGridLine: { color: "D5DEC5", size: 0.5 },
    catGridLine: { style: "none" },
    showLegend: false,
    showTitle: true,
    title: "Daily Revenue: Weekday vs Weekend (₹)",
    titleFontSize: 12,
    titleColor: P.dark
  });
}

// ══════════════════════════════════════════════════════════════════════════
// SLIDE 15 — Expected Outcomes & Success Metrics
// ══════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: P.lightBg };
  hdr(s, "Expected Outcomes & Success Metrics", "Measurable business and operational targets for the SliceMatic system");

  const metrics = [
    { id: "O-1", title: "Accurate Billing", desc: "100% correct bills; automatic discount (qty ≥ 5) & 18% GST; zero manual calculation errors." },
    { id: "O-2", title: "System Reliability", desc: "Zero unhandled crashes; complete coverage for all 8 edge cases and swapped menu files." },
    { id: "O-3", title: "Data Persistence", desc: "100% of completed orders written to the log in a parseable, consistent format." },
    { id: "O-4", title: "Dynamic Configuration", desc: "Zero code changes for menu updates; swap/edit menu files at runtime with instant loading." },
    { id: "O-5", title: "Operational Speed", desc: "Order completion under 2 mins; recovers staff time from manual phone billing." },
    { id: "O-6", title: "Analytics Enablement", desc: "Full visibility: AOV, peaks, margins, and break-even easily derived from order logs." }
  ];

  const cW = 4.4, cH = 1.1, gX = 0.3, gY = 0.18;
  const startX = 0.45, startY = 1.25;

  metrics.forEach((m, i) => {
    const col = i % 2, row = Math.floor(i / 2);
    const x = startX + col * (cW + gX);
    const y = startY + row * (cH + gY);
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w: cW, h: cH, fill: { color: P.card }, rectRadius: 0.07, shadow: mkSh() });
    
    // ID badge (Gold color for success metrics)
    s.addShape(pres.shapes.OVAL, { x: x + 0.12, y: y + 0.33, w: 0.44, h: 0.44, fill: { color: P.gold } });
    s.addText(m.id, { x: x + 0.12, y: y + 0.34, w: 0.44, h: 0.44, fontSize: 10, bold: true, color: P.card, fontFace: "Calibri", align: "center", valign: "middle", margin: 0 });
    
    s.addText(m.title, { x: x + 0.68, y: y + 0.08, w: cW - 0.8, h: 0.32, fontSize: 13, bold: true, color: P.dark, fontFace: "Cambria", margin: 0 });
    s.addText(m.desc, { x: x + 0.68, y: y + 0.44, w: cW - 0.8, h: 0.58, fontSize: 9.5, color: P.muted, fontFace: "Calibri", margin: 0 });
  });

  // Footer for Stage 3 future metrics
  s.addText("Note: Stage 3 targets include 80%+ digital adoption and natural-language extraction via conversational AI (OpenRouter).", {
    x: 0.5, y: 5.15, w: 9.0, h: 0.3,
    fontSize: 9, color: P.muted, fontFace: "Calibri", align: "center", italic: true
  });
}

// ══════════════════════════════════════════════════════════════════════════
// SLIDE 16 — Challenge These Numbers
// ══════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: P.lightBg };
  hdr(s, "Challenge These Numbers — Stress Tests", "Six scenarios stress-tested with reproducible calculations");

  const qs = [
    { n: "Q1", title: "Rent → ₹70,000/mo",            result: "Break-even: 12/day (+1 only)",      verdict: "Robust. Model only turns unviable at rent ~₹7.6L (13× current). Demand volume is the binding risk — not rent." },
    { n: "Q2", title: "40% orders via Aggregator (25% comm.)", result: "Blended CM ₹574; B/E: 12/day", verdict: "Viable channel — but every direct order is worth ₹175 more. Core case for the own-app." },
    { n: "Q3", title: "When to hire 3rd Rider?",       result: "Trigger at 55–60 orders/day",       verdict: "Financially trivial (25 extra orders pays ₹16k/mo cost). Real trigger: SLA breaks before finances do." },
    { n: "Q4", title: "10% Discount at Qty ≥ 5",       result: "Driver or leak — depends",          verdict: "+₹134 CM if it converts 4→5 pizzas. −₹331 if buyer orders 5+ anyway. Keep threshold configurable." },
    { n: "Q5", title: "COGS Inflation +12%",           result: "CM drops to ₹626/order",            verdict: "Only ~1.3 extra orders/day needed to hold EBITDA. Low severity — high absorbability." },
    { n: "Q6", title: "Top 3 BI Metrics from Order Log", result: "Feeds all Stage 3 features",      verdict: "(1) AOV + topping attach rate  (2) Demand heatmap by hour × day  (3) Item-level CM ranking" },
  ];

  const cW = 4.55, cH = 1.5, gX = 0.2, gY = 0.18, startX = 0.35, startY = 1.1;
  qs.forEach((q, i) => {
    const col = i % 2, row = Math.floor(i / 2);
    const x = startX + col * (cW + gX), y = startY + row * (cH + gY);
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w: cW, h: cH, fill: { color: P.card }, rectRadius: 0.08, shadow: mkSh() });
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: x + 0.1, y: y + 0.1, w: 0.46, h: 0.44, fill: { color: P.med }, rectRadius: 0.05 });
    s.addText(q.n, { x: x + 0.1, y: y + 0.11, w: 0.46, h: 0.44, fontSize: 11, bold: true, color: P.card, fontFace: "Calibri", align: "center", valign: "middle", margin: 0 });
    s.addText(q.title, { x: x + 0.65, y: y + 0.1, w: cW - 0.78, h: 0.38, fontSize: 11, bold: true, color: P.dark, fontFace: "Cambria", margin: 0 });
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: x + 0.65, y: y + 0.52, w: cW - 0.78, h: 0.26, fill: { color: P.oliveC }, rectRadius: 0.04 });
    s.addText("→  " + q.result, { x: x + 0.68, y: y + 0.54, w: cW - 0.84, h: 0.22, fontSize: 9.5, bold: true, color: P.dark, fontFace: "Calibri", margin: 0 });
    s.addText(q.verdict, { x: x + 0.12, y: y + 0.86, w: cW - 0.24, h: 0.56, fontSize: 9, color: P.muted, fontFace: "Calibri", margin: 0 });
  });
}

// ══════════════════════════════════════════════════════════════════════════
// SLIDE 17 — Product Roadmap
// ══════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: P.dark };
  s.addShape(pres.shapes.OVAL, { x: 8.2, y: -0.6, w: 3.2, h: 3.2, fill: { color: P.med, transparency: 70 } });
  s.addShape(pres.shapes.OVAL, { x: -0.6, y: 3.3, w: 2.8, h: 2.8, fill: { color: P.gold, transparency: 80 } });

  s.addText("Product Roadmap", { x: 0.5, y: 0.2, w: 9.0, h: 0.6, fontSize: 28, bold: true, color: P.card, fontFace: "Cambria", align: "left", margin: 0 });
  s.addText("Each phase builds on the order data captured from Phase 1", { x: 0.5, y: 0.83, w: 9.0, h: 0.26, fontSize: 11, color: P.goldL, fontFace: "Calibri", margin: 0 });

  const phases = [
    { n: "1", phase: "Stage 2 MVP",    theme: "Validated File-Based Ordering", status: "In Build  ✅", active: true,
      items: ["CLI step-driven flow", "Full input validation", "Pricing engine + discount + GST", "Parseable orders_log.txt", "All 8 edge cases hardened"] },
    { n: "2", phase: "Stage 3 — Web",  theme: "Full-Stack Production App",   status: "Planned",     active: false,
      items: ["Next.js / React on Vercel", "Supabase PostgreSQL + Auth", "Admin dashboard + filters", "Revenue summary + metrics", "CSV export"] },
    { n: "3", phase: "Stage 3 — AI",   theme: "Conversational Ordering",     status: "Planned",     active: false,
      items: ["LLM via OpenRouter (Option B)", "Natural-language ordering", "Menu-grounded extraction", "Deterministic pricing kept", "Graceful fallback to form"] },
    { n: "4", phase: "Beyond",         theme: "Growth & Intelligence",       status: "Directional", active: false,
      items: ["Aggregator integration", "Loyalty / coupon codes", "Demand forecasting", "AI recommendations", "Multi-outlet support"] },
  ];

  const pW = 2.25, pH = 3.6, pY = 1.38, pX = 0.35, pGap = 0.1;
  phases.forEach((ph, i) => {
    const x = pX + i * (pW + pGap);
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: pY, w: pW, h: pH, fill: { color: ph.active ? P.med : "374E20" }, rectRadius: 0.1 });
    s.addShape(pres.shapes.OVAL, { x: x + pW / 2 - 0.3, y: pY + 0.1, w: 0.6, h: 0.6, fill: { color: ph.active ? P.gold : P.med } });
    s.addText(ph.n, { x: x + pW / 2 - 0.3, y: pY + 0.11, w: 0.6, h: 0.6, fontSize: 16, bold: true, color: P.card, fontFace: "Cambria", align: "center", valign: "middle", margin: 0 });
    s.addText(ph.phase, { x: x + 0.1, y: pY + 0.8, w: pW - 0.2, h: 0.38, fontSize: 11, bold: true, color: ph.active ? P.goldL : P.card, fontFace: "Cambria", align: "center", margin: 0 });
    s.addText(ph.theme, { x: x + 0.1, y: pY + 1.18, w: pW - 0.2, h: 0.32, fontSize: 8.5, color: "A8C87A", fontFace: "Calibri", align: "center", margin: 0 });
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: x + (pW - 1.5) / 2, y: pY + 1.55, w: 1.5, h: 0.24, fill: { color: ph.active ? P.gold : "4A6030" }, rectRadius: 0.04 });
    s.addText(ph.status, { x: x + (pW - 1.5) / 2, y: pY + 1.56, w: 1.5, h: 0.22, fontSize: 8, bold: true, color: P.card, fontFace: "Calibri", align: "center", margin: 0 });
    ph.items.forEach((item, j) => {
      s.addText("·  " + item, { x: x + 0.12, y: pY + 1.9 + j * 0.31, w: pW - 0.24, h: 0.27, fontSize: 8.5, color: "C5DBA0", fontFace: "Calibri", margin: 0 });
    });
  });
}

// ─── Write & rezip ────────────────────────────────────────────────────────
pres.writeFile({ fileName: "ppt/SliceMatic_PRD.pptx" })
  .then(() => console.log("DONE"))
  .catch(e => { console.error(e); process.exit(1); });