# AI-Powered Legal Document Simplification & Public Q&A Assistant

> **CSE472 – Deep Learning for NLP (B.Tech)**

Simplify legal/government documents (rental agreements, terms of service,
government notices) into plain language. Highlight obligations, rights,
deadlines, and penalties. Answer questions grounded in the user's own
document – in English, Hindi, and Punjabi.

> ⚠️ **Disclaimer** – All outputs are for general understanding only and do
> **not** constitute legal advice.

---

## Quick Start

```powershell
# 1 — Create the conda environment (one time)
.\scripts\setup_env.ps1

# 2 — Copy .env.example → .env and fill in your GEMINI_API_KEY

# 3 — Run the test suite
conda run -n NLP_Project --no-capture-output pytest tests/ -v

# 4 — Launch the API (coming in Step 8)
# conda run -n NLP_Project --no-capture-output uvicorn app.main:app --reload
```

## Project Layout

```
src/legalassist/      Core library
  ingestion/          PDF/DOCX extraction & cleaning
  segmentation/       Clause segmentation & doc-type detection
  tagging/            Multi-label clause tagging (XLM-R, baselines)
  summarization/      Clause-structured summaries & highlights
  qa/                 Hybrid RAG Q&A (BM25 + dense retrieval)
  llm/                Gemini API integration
  i18n/               Hindi / Punjabi / English + disclaimers
  evaluation/         Metrics (ROUGE, BERTScore, accuracy)
  config.py           Central settings (.env loader)
app/                  FastAPI backend
frontend/             Web UI
tests/                Pytest suite
data/                 raw / gold / processed
docs/                 Write-up, diagrams
scripts/              Automation helpers
```

## Status

See [project.md](project.md) for the full spec, checklist, and log.

| Step | Description | Status |
|------|-------------|--------|
| 0 | Scaffold + env + repo | ✅ |
| 1 | Extraction / cleaning / segmentation | ⬜ |
| 2 | Corpus manifest + annotation tool | ⬜ |
| 3 | Classical baselines | ⬜ |
| 4 | BiLSTM + XLM-R tagging | ⬜ |
| 5 | Gemini layer (fields + summaries) | ⬜ |
| 6 | Hybrid RAG Q&A | ⬜ |
| 7 | Hindi / Punjabi + disclaimers | ⬜ |
| 8 | FastAPI + frontend | ⬜ |
| 9 | Evaluation scripts | ⬜ |
| 10 | Docs + demo | ⬜ |
