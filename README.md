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
full-stack app). This repository includes the **Stage 2 Gradio MVP**.

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

## Running the App Locally

The application uses `uv` for lightning-fast dependency management and virtual environments.

1. Install `uv` if you haven't already.
2. From the repository root, install dependencies and start the Gradio app:
   ```bash
   uv run python app.py
   ```
3. Open your browser and navigate to `http://127.0.0.1:7860` to view the application.

## Stage 2 — Gradio MVP

The Stage 2 MVP is the working pizza-ordering app required by the assignment brief.

What it covers:

- Customer intake with strict name and Indian mobile-number validation.
- Runtime menu loading from `ID;Name;Price` text files.
- Defensive menu parsing for swapped or malformed files.
- Quantity validation from 1 to 10.
- 10% discount when quantity is at least 5.
- GST at 18% on the post-discount amount.
- Mock payment flow: `1 Cash`, `2 Card`, `3 UPI`.
- Parseable order logging in `database/orders_log.txt`.
- Admin menu management with default menu fallback and custom menu updates.

Useful Stage 2 files:

- `STAGE2_RUN.md` — concise run and smoke-test guide.
- `app.py` — Gradio app mounted on FastAPI.
- `core/` — validation, menu parsing, pricing, and persistence logic.
- `menu_data/` — SliceMatic default menu.
- `database/menu/` — saved custom menu files after admin upload.
- `database/orders_log.txt` — completed order log.

Run the judge-friendly smoke test:

```bash
uv run python scripts/stage2_smoke_test.py
```

Or on Windows without `uv`:

```powershell
.\.venv\Scripts\python.exe scripts\stage2_smoke_test.py
```

The smoke test starts the app on a test port, loads swapped menu files, places one order, verifies pricing, and writes a judge-demo log to `database/smoke_test_data/smoke_orders_log.txt`.

## CI/CD Pipeline & Deployment

This project uses GitHub Actions for automated testing and deployment to Hugging Face Spaces.

### 1. When a Pull Request is Raised
When a Pull Request is opened against the `master` branch, the **PR Checks** workflow automatically runs. It spins up an isolated environment, installs all dependencies, and runs the `pytest` suite. 
- **If tests pass:** The PR is marked green and safe to merge.
- **If tests fail:** The PR is blocked from being merged until the code is fixed.

### 2. When a Pull Request is Merged
When code is successfully merged into the `master` branch, the **Sync to Hugging Face Hub** workflow is triggered. 
- It authenticates securely with Hugging Face.
- It pushes the latest `master` codebase to the Hugging Face Space using the `hf upload` CLI.
- Large binary files (like `.pdf` and `.pptx`) are explicitly excluded to prevent deployment rejections.
- The Hugging Face Space automatically rebuilds the Docker container and goes live!
