# Corpus Data Directory

## Target Corpus (12 Documents)

| Document Type | Count | `doc_id` Format |
|---------------|-------|-----------------|
| `rental_agreement` | 4 | `rent_01` .. `rent_04` |
| `terms_of_service` | 4 | `tos_01` .. `tos_04` |
| `government_notice` | 4 | `gov_01` .. `gov_04` |

## Collection Rules

- **Public sources only:** Every document must come from an official public portal, public template repository, or openly published terms page. Record the URL and license/terms note in [manifest.csv](manifest.csv).
- **No personal data:** Do not collect or upload documents containing private PII (names, phone numbers, Aadhaar/PAN, bank details, home addresses of private individuals). Redact or pick public blank/official specimens.
- **Gitignore policy:** Place raw source files (`.pdf`, `.docx`, `.txt`) in `data/raw/` named `<doc_id>.<ext>` (for example, `data/raw/rent_01.pdf`). The `data/raw/` and `data/processed/` directories are gitignored so raw binaries are not pushed to GitHub.
- **What is committed:** Only `data/manifest.csv`, `data/README.md`, and gold annotation files under `data/gold/` (`*.clauses.json`, `*.qa.json`, `*.summary.txt`) are committed.

## Annotation Workflow

1. Place collected documents in `data/raw/` using the `doc_id` naming convention (`rent_01.pdf`, `tos_01.txt`, `gov_01.pdf`, etc.) and update `data/manifest.csv`.
2. Generate annotation templates:
   ```powershell
   conda run -n NLP_Project --no-capture-output python -m scripts.prepare_annotation
   ```
3. Open `tools/annotate.html` locally in a browser, load `data/gold/<doc_id>.clauses.json`, tag clauses, and save back to `data/gold/<doc_id>.clauses.json`.
4. Fill in `data/gold/<doc_id>.summary.txt` and `data/gold/<doc_id>.qa.json` following `docs/annotation_guidelines.md`.
5. Check corpus coverage and flag unannotated documents:
   ```powershell
   conda run -n NLP_Project --no-capture-output python -m scripts.corpus_stats
   ```
