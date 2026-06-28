---
title: PizzaFlow
emoji: 🍕
colorFrom: green
colorTo: purple
sdk: docker
app_port: 7860
---

# SliceMatic — PizzaFlow Applied Project

FDE Academy Programme · PizzaFlow Applied Project · **Group 3**

A full-stack AI pizza-ordering system for **SliceMatic**, a single-outlet pizza delivery brand
in New Ashok Nagar, Delhi. Delivered across three stages (PRD + economics → Gradio MVP →
full-stack app). This repository currently holds the **Stage 1** deliverables.

## Team — Group 3

- Mouli Murakambattu
- Shaik Mohammed Pasha
- Aman Sharma
- Saurabh Sekhar
- Sushant Kumar

## Repository structure

```
pizzaflow/
├── docs/                                  Stage 1 deliverables
│   ├── Stage1_PartA_PRD.md                Product Requirements Document
│   ├── Stage1_PartB_BusinessEconomics.md  Business Unit Economics + stress tests
│   └── SliceMatic_Stage1_Submission.pdf   Combined, submission-ready PDF
├── reference/                             Source / supporting material
│   ├── PizzaFlow_Assignment_Brief_FDE.pdf
│   ├── SliceMatic_Business_Economics.pdf          (provided baseline model)
│   └── SliceMatic_Business_Economics_Explained.pdf (plain-language study guide)
├── menu_data/                             Menu files (ID;Name;Price)
│   ├── Types_of_Base.txt
│   ├── Types_of_Pizza.txt
│   └── Types_of_Toppings.txt
├── calculator/
│   └── SliceMatic_Calculator.xlsx         Live plug-and-play unit-economics model
└── scripts/                              Generators (reproduce the artifacts)
    ├── make_submission_pdf.py             docs/*.md  ->  submission PDF
    ├── make_calculator.py                 ->  calculator/SliceMatic_Calculator.xlsx
    └── make_guide_pdf.py                  ->  reference/..._Explained.pdf
```

## Stage 1 — what's inside

- **Part A — PRD:** product vision, functional & non-functional requirements (tabulated),
  user-flow diagrams (customer + admin), the Stage 3 conversational-ordering AI feature,
  drawbacks, cost-vs-value, expected outcomes, open client questions, and out-of-scope.
- **Part B — Business Unit Economics:** fixed costs, COGS by pizza, gross/contribution margins,
  revenue model, break-even, delivery-radius economics, GST treatment, and six stress tests
  (rent shock, aggregator commission, 3rd rider, discount impact, COGS inflation, BI metrics).
- **Calculator:** an Excel workbook where editing the yellow input cells recalculates every
  metric (dashboard, COGS/margin, bill, and all six scenarios).

## Regenerating the artifacts

From the repository root (requires Python with `fpdf2`, `openpyxl`, `pillow`):

```bash
python scripts/make_submission_pdf.py     # rebuilds docs/SliceMatic_Stage1_Submission.pdf
python scripts/make_calculator.py         # rebuilds calculator/SliceMatic_Calculator.xlsx
python scripts/make_guide_pdf.py          # rebuilds reference/..._Explained.pdf
```
