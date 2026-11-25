# project.md — Single Source of Truth
<!-- Any mention of PROGRESS.md or PROJECT_CONTEXT.md in a prompt means this file. -->

---

## 1 · SPEC

### Goal
Simplify legal / government documents (rental agreements, terms of service,
government notices) into plain language. Highlight **obligations, rights,
deadlines, penalties**. Answer questions grounded in the user's own document.
Languages: **English, Hindi, Punjabi**. Every output carries a disclaimer:

> *"This is for general understanding only and does not constitute legal advice."*

### Modules

| ID | Module | Detail |
|----|--------|--------|
| M1 | Extraction + Cleaning | PDF / DOCX / plain-text ingestion; OCR fallback; normalisation |
| M2 | Clause Segmentation + Doc-Type Detection | Rule + ML hybrid segmenter; doc-type classifier |
| M3 | Clause Tagging | Fine-tuned XLM-R, multi-label (obligation / right / deadline / penalty); LLM field extraction (party / date / amount) |
| M4 | Clause-Structured Summary + Highlighting | Abstractive clause-level summaries; colour-coded highlights |
| M5 | Hybrid RAG Q&A | BM25 + multilingual dense (FAISS), top-k retrieval, clause citations; abstain when unsupported |
| M6 | Language Layer + Disclaimer | Translate / generate in Hindi & Punjabi; append disclaimer |

### Model Ladder (compare)

| Task | Baseline 1 | Baseline 2 | Baseline 3 | Proposed |
|------|-----------|-----------|-----------|----------|
| Tagging | TF-IDF + LR | BiLSTM | Zero-shot LLM | Fine-tuned XLM-R |
| Summarisation | TextRank | Flan-T5 | Prompt-only LLM | Clause-structured (proposed) |
| Q&A | TF-IDF / BM25 top clause | SQuAD2 reader | Full-context LLM | Hybrid RAG (proposed) |

### Hardware Constraints
- **GPU:** NVIDIA RTX 3050 6 GB
- **RAM:** 16 GB
- Strategy: fp16, small batches, gradient accumulation, 4-bit LoRA where needed

---

## 2 · WORKING RULES

1. Python 3.11 in conda env `NLP_Project`.
2. Run every command via `conda run -n NLP_Project --no-capture-output <cmd>`.
3. Always quote paths (the project folder has a space).
4. Type hints, docstrings, small testable functions.
5. No secrets in code — use `.env` / `config.py`.
6. Never fabricate data or results.
7. Any mention of *PROGRESS.md* or *PROJECT_CONTEXT.md* means **this file** (`project.md`).
8. **End of every step:**
   - Run `pytest` until green.
   - Update this file: tick the checklist, add a dated LOG entry (what was built, how to run it, known limitations, next step).
   - `git add -A && git commit -m "Step N: <summary>" && git push`

---

## 3 · PROGRESS CHECKLIST

- [x] **Step 0** — Scaffold + conda env + repo
- [x] **Step 1** — Extraction / cleaning / segmentation / doc-type
- [ ] **Step 2** — Corpus manifest + annotation tool
- [ ] **Step 3** — Classical baselines (TF-IDF+LR, TextRank, BM25)
- [ ] **Step 4** — BiLSTM + XLM-R tagging (grouped CV)
- [ ] **Step 5** — Gemini layer (field extraction + summaries)
- [ ] **Step 6** — Hybrid RAG Q&A
- [ ] **Step 7** — Hindi / Punjabi + disclaimers
- [ ] **Step 8** — FastAPI + frontend
- [ ] **Step 9** — Evaluation scripts
- [ ] **Step 10** — Docs + demo

---

## 4 · LOG

### 2026-11-25 — Step 1: Extraction, cleaning, segmentation, doc-type (M1 & M2)

**What was built:**
- `src/legalassist/ingestion/extract.py`: `extract_pages(data, filename)` supporting `.pdf` (`pdfplumber`), `.docx` (`python-docx`, preserving paragraphs and deduplicated table cell rows in document order), and `.txt` (`utf-8-sig` with `latin-1` fallback); raises `UnsupportedFileTypeError` or `EmptyDocumentError` (subclassing `ExtractionError`).
- `src/legalassist/ingestion/clean.py`: `clean_pages(pages)` removing lines repeating on >50% of pages (when `len(pages) >= 2`), stripping standalone page numbers (`Page 3 of 10`, `- 3 -`, etc.), de-hyphenating line-break words, and normalizing unicode quotes/dashes and whitespace while preserving clause numbering.
- `src/legalassist/segmentation/segment.py`: `Clause` dataclass, `segment_clauses(text)` detecting `1.`, `1.1`, `1.1.1`, `(a)`, `(i)`, `Clause/Section/Article N`, and ALL-CAPS headings with hierarchical parent numbers (e.g. `4.2(a)`), sentence-boundary splitting above 1200 chars, paragraph-splitting fallback, and `llm_segment_fallback(text)` stub (`NotImplementedError` for Step 5).
- `src/legalassist/segmentation/doctype.py`: `DOC_TYPE_KEYWORDS` dict and `detect_doc_type(text)` returning `(doc_type, confidence)` over `rental_agreement`, `terms_of_service`, `government_notice`, `unknown`.
- `scripts/analyze.py`: CLI (`python -m scripts.analyze <file>`) outputting doc type, confidence, clause count, and segmented clauses as JSON.
- `tests/fixtures/`: three 15-clause synthetic fixtures (`rental_agreement.txt`, `terms_of_service.txt`, `government_notice.txt`) plus `tests/conftest.py`, `tests/test_ingestion.py`, and `tests/test_segmentation.py` (16 total tests passing).

**How to run:**
```powershell
& "C:\ProgramData\miniconda3\condabin\conda.bat" run -n NLP_Project --no-capture-output pytest "tests" -v
& "C:\ProgramData\miniconda3\condabin\conda.bat" run -n NLP_Project --no-capture-output python -m scripts.analyze "tests/fixtures/rental_agreement.txt"
```

**Known limitations:**
- Scanned/image-only PDFs raise `EmptyDocumentError` (OCR is out of scope).
- Unnumbered documents with implicit clause breaks use paragraph splitting until `llm_segment_fallback` is implemented in Step 5.
- Doc-type detection is purely English keyword/phrase weighted; Hindi/Punjabi documents and ML classifiers are not added yet.
- Soft PDF line wraps within a paragraph are kept as `\n` (except hyphenated breaks) so key-value lines and table rows stay separated; may be refined when processing real corpus PDFs in Step 2.

**Next step:**
- Step 2: Corpus manifest + annotation tool.

### 2026-11-25 — Step 0: Scaffold, conda env, repo

**What was built:**
- Conda environment `NLP_Project` (Python 3.11) with PyTorch (`2.14.1+cu126`, CUDA available: `True`),
  core deps (FastAPI, pdfplumber, scikit-learn, etc.), and ML deps
  (transformers, sentence-transformers, faiss-cpu, google-genai, etc.).
  - *Env note:* Used the `cu126` PyTorch index (`https://download.pytorch.org/whl/cu126`) instead of
    `cu121` because `cu121` caps at `torch 2.5.1` while `accelerate` (`1.16.0`) requires `torch>=2.6.0`.
    All packages installed cleanly on Windows with no dependency conflicts (`pip check` passed; Windows
    Smart App Control was temporarily disabled by the user to allow loading unsigned Python extension DLLs).
- Full repo skeleton under `src/legalassist/` with 8 subpackages + `config.py`.
- `tests/test_smoke.py` — imports all packages and verifies config paths.
- `.gitignore`, `.env.example`, `requirements-core.txt`, `requirements-ml.txt`,
  `environment.yml`, `scripts/setup_env.ps1`, `README.md`, `project.md`.
- Public GitHub repo created and pushed.

**How to run:**
```powershell
conda run -n NLP_Project --no-capture-output pytest tests/ -v
```

**Known limitations:**
- No feature code yet — just the scaffold.
- `C:\ProgramData\miniconda3\condabin\conda.bat` and `C:\Program Files\GitHub CLI\gh.exe` are used explicitly when not on default shell `PATH`.

**Next step:**
- Step 1: PDF/DOCX ingestion, text cleaning, clause segmentation, doc-type detection.
