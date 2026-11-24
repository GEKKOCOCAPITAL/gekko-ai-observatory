// Builds docs/workshop/GEKKO-AI_Final_Expert_Review_Report.docx (ready-to-sign expert review pack).
// Usage: node docs/workshop/build_expert_pack.js   (run from the repository root)
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, ImageRun, AlignmentType,
  WidthType, ShadingType, BorderStyle, HeadingLevel, LevelFormat, PageBreak, Footer, PageNumber,
  ExternalHyperlink,
} = require("docx");

const ROOT = path.resolve(__dirname, "..", "..");
const FONT = "Arial";
const GOLD = "9C8660";
const W = 9638; // A4 text width with 2 cm margins (DXA)

const scen = JSON.parse(fs.readFileSync(path.join(ROOT, "outputs/dashboard_data.json"))).scenario_total
  .filter((r) => r.year === 2030 && r.subsector === "TOTAL");
const manifest = JSON.parse(fs.readFileSync(path.join(ROOT, "outputs/run_manifest.json")));
const get = (s, m) => scen.find((r) => r.scenario === s && r.metric === m);

const border = { style: BorderStyle.SINGLE, size: 4, color: "BFBFBF" };
const borders = { top: border, bottom: border, left: border, right: border };
const p = (text, opts = {}) => new Paragraph({ spacing: { after: 120 }, ...opts, children: [new TextRun({ text, font: FONT, size: 22, ...(opts.run || {}) })] });
const runs = (parts, opts = {}) => new Paragraph({ spacing: { after: 120 }, ...opts, children: parts.map((t) => typeof t === "string" ? new TextRun({ text: t, font: FONT, size: 22 }) : t) });
const b = (text) => new TextRun({ text, font: FONT, size: 22, bold: true });
const h1 = (text) => new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun(text)] });
const h2 = (text) => new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun(text)] });
const bullet = (text) => new Paragraph({ numbering: { reference: "bullets", level: 0 }, spacing: { after: 60 }, children: [new TextRun({ text, font: FONT, size: 22 })] });
const link = (text, url) => new ExternalHyperlink({ link: url, children: [new TextRun({ text, font: FONT, size: 22, style: "Hyperlink" })] });

function cell(text, width, { head = false, fill, minH } = {}) {
  const lines = String(text).split("\n");
  return new TableCell({
    width: { size: width, type: WidthType.DXA }, borders,
    shading: head ? { fill: "EFEAE0", type: ShadingType.CLEAR, color: "auto" } : fill ? { fill, type: ShadingType.CLEAR, color: "auto" } : undefined,
    margins: { top: 60, bottom: 60, left: 100, right: 100 },
    children: lines.map((l) => new Paragraph({ children: [new TextRun({ text: l, font: FONT, size: 19, bold: head })] })),
  });
}
function table(widths, rows, { header = true, rowHeight } = {}) {
  return new Table({
    width: { size: widths.reduce((a, c) => a + c, 0), type: WidthType.DXA }, columnWidths: widths,
    rows: rows.map((r, i) => new TableRow({
      tableHeader: header && i === 0, cantSplit: true,
      height: rowHeight && !(header && i === 0) ? { value: rowHeight, rule: "atLeast" } : undefined,
      children: r.map((t, j) => cell(t, widths[j], { head: header && i === 0 })),
    })),
  });
}
const gap = () => new Paragraph({ spacing: { after: 60 }, children: [] });
const box = "☐";

// ---------------------------------------------------------------- content
const pct = (x) => (x * 100).toFixed(1) + "%";
const num = (x) => Math.round(x).toLocaleString("en-US");
const scenRows = [["Scenario (2030)", "Labour productivity\np05 / median / p95", "Employment (jobs)\np05 / median / p95", "Value added (EUR m)\np05 / median / p95"]];
for (const [k, lab] of [["cautious", "S1 Cautious"], ["central", "S2 Central"], ["accelerated", "S3 Accelerated"]]) {
  const lp = get(k, "dLP"), j = get(k, "jobs"), g = get(k, "gva_eur_m");
  scenRows.push([lab, `+${pct(lp.p05)} / +${pct(lp.p50)} / +${pct(lp.p95)}`, `${num(j.p05)} / ${num(j.p50)} / ${num(j.p95)}`, `+${num(g.p05)} / +${num(g.p50)} / +${num(g.p95)}`]);
}

const items = [
  ["A1", "O4", "Are the 11 risk categories complete for AI use in Luxembourg financial institutions? Anything missing?"],
  ["A2", "O4", "Is each category correctly mapped to the EU AI Act, DORA and the FSB (2024) AI vulnerabilities?"],
  ["A3", "O4", "Do the attribute weights produce a sensible ranking of the 13 use-case archetypes?"],
  ["A4", "O4", "Are the default control-coverage figures (CSSF/BCL 2025 survey plus stated assumptions) realistic?"],
  ["A5", "O4", "Is the indicative AI Act classification of the 13 archetypes correct (incl. Digital Omnibus dates)?"],
  ["B1", "O3", "Are the 2030 scenario ranges (adoption ceiling, depth of use, time savings, reinstatement) plausible?"],
  ["B2", "O3", "Are the sub-sector exposure scores and task ratings credible for Luxembourg roles?"],
  ["B3", "O3", "Are the results communicated with enough uncertainty and caveats?"],
  ["C1", "O5", "Could you use the toolkit / dashboard without assistance? (score 1-5)"],
  ["C2", "O5", "Which outputs would you use in practice? Which are missing?"],
];
const ratingCell = `${box} Agree\n${box} Partly agree\n${box} Disagree`;
const assessRows = [["Item", "Question", "Rating", "Comments / requested changes", "Severity"]]
  .concat(items.map(([id, o, q]) => [`${id}\n(${o})`, q, id === "C1" ? "Score: ___ / 5" : id === "C2" ? "-" : ratingCell, "", `${box} none\n${box} minor\n${box} major\n${box} critical`]));

const logo = fs.readFileSync(path.join(ROOT, "docs/assets/gekko_logo_cover.png"));

const children = [
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 600, after: 400 }, children: [new ImageRun({ type: "png", data: logo, transformation: { width: 357, height: 105 } })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 120 }, children: [new TextRun({ text: "Final Expert Review Report", font: FONT, size: 44, bold: true })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 360 }, children: [new TextRun({ text: "GEKKO-AI Observatory - Milestone M3 (objectives O3, O4, O5)", font: FONT, size: 26, color: GOLD })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 120 }, children: [new TextRun({ text: "Artificial Intelligence and the Transformation of Luxembourg's Financial Sector: Impacts, Opportunities and Risks", font: FONT, size: 22, italics: true })] }),
  gap(),
  table([3200, 6438], [
    ["Applicant", "Gekko & Co. Capital SCSp (General Partner and Manager: RM MANAGEMENT SPF)"],
    ["Project leader", "Rafael Mendes (ORCID 0009-0008-5585-0631)"],
    ["Toolkit version reviewed", `${manifest.toolkit_version} (results hash ${manifest.results_hash_central}, seed ${manifest.seed}, ${manifest.n_draws.toLocaleString("en-US")} draws)`],
    ["Archives", "Toolkit DOI 10.5281/zenodo.24511514 · Research report DOI 10.5281/zenodo.24512015"],
    ["Pack prepared", "25 November 2026, by the project team"],
    ["Status", "TO BE COMPLETED AND SIGNED BY THE EXPERT REVIEWER"],
  ], { header: false }),
  gap(),
  p("Sections 1-4 were prepared by the project team and describe what is being reviewed. Sections 5-9 are completed by the expert. The findings, conclusion and signature are the expert's own; the project team does not edit them.", { run: { size: 20, italics: true } }),
  new Paragraph({ children: [new PageBreak()] }),

  h1("1. Purpose and scope"),
  p("This report records an independent expert review of the GEKKO-AI Observatory prototype delivered at milestone M3: the impact-scenario module (O3), the AI risk taxonomy and scoring module (O4) and the integrated, validated toolkit and dashboard (O5). It provides the external validation required by check V23, which the automated validation suite cannot perform itself."),
  p("Acceptance criteria (M3): every comment is logged with a decision; all comments rated critical are resolved or explicitly deferred with a justification; where two or more experts review, agreement on Part A reaches Fleiss' kappa of 0.40 or more."),
  p("Participation is voluntary and unpaid; no project budget is transferred to the reviewer (application section 7.3.4). No personal data beyond name, role and organisation is recorded."),

  h1("2. Materials reviewed"),
  runs([b("Live dashboard: "), link("gekkococapital-gekko-ai-observatory.hf.space", "https://gekkococapital-gekko-ai-observatory.hf.space")]),
  runs([b("Source code and data: "), link("github.com/GEKKOCOCAPITAL/gekko-ai-observatory", "https://github.com/GEKKOCOCAPITAL/gekko-ai-observatory"), " (Apache-2.0)"]),
  runs([b("M3 Results and Validation Report: "), "docs/GEKKO-AI_M3_Results_and_Validation_Report.pdf"]),
  runs([b("Research report (2026): "), link("doi.org/10.5281/zenodo.24512015", "https://doi.org/10.5281/zenodo.24512015")]),
  runs([b("Methodology: "), "docs/methodology.md · risk taxonomy data/risk_taxonomy.yaml · task ratings data/tasks.csv"]),

  h1("3. Results under review"),
  h2("3.1 Coverage and exposure"),
  p("57,229 employees in 8 CSSF/CAA-registered sub-sectors; employment-weighted AI exposure index 0.51 (task level, E0/E1/E2 rubric; ratings v0.1 are LLM-assisted and pending human validation)."),
  h2("3.2 Impact scenarios to 2030 (O3, toolkit model)"),
  p("Effects relative to a no-AI baseline; Monte-Carlo, 10,000 draws per scenario; adoption calibrated on the CSSF/BCL surveys (30% to 43%)."),
  table([2100, 2513, 2513, 2512], scenRows),
  gap(),
  p("Note for the reviewer: the research report uses a separate scenario model (four LFF segments, 20,000 draws), whose central case is about +5.7% productivity and about -1,500 jobs. The toolkit models eight sub-sectors and adds demand and new-task effects. Both are conditional scenarios, not forecasts, and one is not a check on the other.", { run: { size: 20, italics: true } }),
  h2("3.3 AI risk taxonomy and scoring (O4)"),
  bullet("11 risk categories; 9 of 11 mapped to the EU AI Act, 6 of 11 to DORA; all 5 FSB (2024) AI vulnerabilities covered."),
  bullet("13 use-case archetypes scored on likelihood x impact (1-25), inherent and residual after controls."),
  bullet("Indicative AI Act classification: 13 of 13 test vignettes correct; employment-weighted share of AI use classified high-risk 6.6%."),
  h2("3.4 Automated validation (O5)"),
  p(`${manifest.validation_summary.PASS} checks PASS, ${manifest.validation_summary.INFO} INFO, ${manifest.validation_summary.PENDING} PENDING. The pending check is V23, this expert review. Results are reproducible: re-running with the same seed gives the same hash (${manifest.results_hash_central}).`),

  h1("4. How to complete this report"),
  bullet("Open the dashboard and, if useful, the M3 report and the repository."),
  bullet("Fill in section 5 (your details) and sign the independence declaration in section 6."),
  bullet("Rate each item in section 7 and add comments; list any requested changes in section 8."),
  bullet("Tick one overall conclusion in section 9, sign and date, and return the document to the project leader."),
  new Paragraph({ children: [new PageBreak()] }),

  h1("5. Reviewer details (completed by the expert)"),
  table([3200, 6438], [
    ["Full name", ""], ["Position / role", ""], ["Organisation", ""],
    ["Area of expertise", `${box} Risk / compliance   ${box} Fund industry   ${box} Banking\n${box} Insurance   ${box} Supervisor / public body   ${box} Academic   ${box} Other: ________`],
    ["Contact (optional)", ""], ["Date(s) of review", ""],
  ], { header: false, rowHeight: 480 }),

  h1("6. Declaration of independence"),
  p(`${box} I am not employed by, and have no financial interest in, Gekko & Co. Capital SCSp or RM MANAGEMENT SPF, and I did not take part in developing the toolkit.`),
  p(`${box} I have the following relationship with the applicant, which I declare: _______________________________________________`),
  p(`${box} I received no payment for this review.`),

  h1("7. Assessment"),
  table([800, 3000, 1450, 3088, 1300], assessRows, { rowHeight: 900 }),
  new Paragraph({ children: [new PageBreak()] }),

  h1("8. Comments and requested changes"),
  p("Severity: minor = wording or presentation; major = affects interpretation of a result; critical = a result should not be used until fixed.", { run: { size: 20, italics: true } }),
  table([700, 1300, 4838, 1500, 1300], [["No.", "Module / item", "Comment and requested change", "Severity", "Project decision*"]]
    .concat([1, 2, 3, 4, 5, 6].map((n) => [String(n), "", "", "", ""])), { rowHeight: 700 }),
  p("* Completed afterwards by the project team and logged in docs/workshop/feedback_log.csv.", { run: { size: 18, italics: true } }),

  h1("9. Overall conclusion (completed by the expert)"),
  p(`${box} Validated: the M3 prototype is fit for its stated purpose without changes.`),
  p(`${box} Validated subject to the changes listed in section 8.`),
  p(`${box} Not validated at this stage (reasons in section 8).`),
  p("Summary opinion:"),
  table([W], [[""]], { header: false, rowHeight: 2200 }),
  gap(),
  table([3200, 6438], [["Signature", ""], ["Name", ""], ["Place and date", ""]], { header: false, rowHeight: 560 }),
];

const doc = new Document({
  creator: "Gekko & Co. Capital SCSp",
  title: "GEKKO-AI Observatory - Final Expert Review Report (M3)",
  styles: {
    default: { document: { run: { font: FONT, size: 22 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: FONT, size: 30, bold: true, color: "1F1F1F" }, paragraph: { spacing: { before: 300, after: 140 }, keepNext: true, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: FONT, size: 24, bold: true, color: GOLD }, paragraph: { spacing: { before: 200, after: 100 }, keepNext: true, outlineLevel: 1 } },
    ],
  },
  numbering: { config: [{ reference: "bullets", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 270 } } } }] }] },
  sections: [{
    properties: { page: { size: { width: 11906, height: 16838 }, margin: { top: 1134, bottom: 1134, left: 1134, right: 1134 } } },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [
      new TextRun({ text: "GEKKO-AI Observatory - Final Expert Review Report (M3) - page ", font: FONT, size: 16, color: "808080" }),
      new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 16, color: "808080" })] })] }) },
    children,
  }],
});

Packer.toBuffer(doc).then((buf) => {
  const out = path.join(ROOT, "docs/workshop/GEKKO-AI_Final_Expert_Review_Report.docx");
  fs.writeFileSync(out, buf);
  console.log("wrote", out);
});
