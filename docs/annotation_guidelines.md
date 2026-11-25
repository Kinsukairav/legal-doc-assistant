# Annotation Guidelines

This guide defines the gold-standard annotation schema for **clause tagging**, **plain-language summaries**, and **document-grounded Q&A** in LegalAssist.

---

## 1. Clause Tagging (Multi-Label)

Each clause in `data/gold/<doc_id>.clauses.json` may receive **zero, one, or multiple** tags from the four categories below (`tags: list[str]`). Use `[]` for purely definitional, heading-only, or introductory clauses that carry none of the four signals.

### 1.1 `obligation`
**Definition:** A party *must*, *shall*, *is required to*, or *agrees to* do or refrain from doing something (includes affirmative duties and explicit prohibitions).

**Examples:**
1. *"The Tenant shall pay the monthly rent on or before the 5th day of each calendar month."* → `obligation` (also `deadline`)
2. *"You agree not to reverse engineer, decompile, or scrape data from the platform."* → `obligation`

### 1.2 `right`
**Definition:** A party *may*, *is entitled to*, *has the option to*, *retains ownership of*, or is explicitly *protected* from liability/interference.

**Examples:**
1. *"You retain full ownership of all content you upload to your user account."* → `right`
2. *"Either party may terminate the lease after the lock-in period by giving written notice."* → `right`

### 1.3 `deadline`
**Definition:** A specific calendar date, time limit, duration, notice period, or grace window tied to performing or responding to an action.

**Examples:**
1. *"All corrective works must be completed within 30 days from publication of this notice."* → `deadline` (also `obligation`)
2. *"An aggrieved owner may file an appeal before the Appellate Authority within 15 days."* → `deadline` (also `right`)

### 1.4 `penalty`
**Definition:** A fine, forfeiture of deposit, late fee, interest charge, account suspension, disconnection, eviction, or other adverse consequence of breach or non-compliance.

**Examples:**
1. *"Late payment beyond the 10th day attracts a late fee of Rs. 500 per day."* → `penalty` (also `deadline`)
2. *"Failure to comply within the stipulated period shall attract a statutory penalty of Rs. 10,000 and disconnection of water supply."* → `penalty`

### 1.5 Multi-Label Boundary Rules
- **Apply all tags that hold directly in the clause text.** For example, *"Tenant shall vacate within 15 days or forfeit the security deposit"* gets `["obligation", "deadline", "penalty"]`.
- **Condition vs. consequence:** Do not tag a clause as `penalty` merely because it mentions a payment (`"monthly rent of Rs. 20,000"`); `penalty` requires a consequence of breach, default, or non-compliance.
- **Pure definitions / boilerplate:** Clauses like *"In this agreement, 'Premises' means Flat 4B"* get `[]`.

---

## 2. Plain-Language Reference Summary (`<doc_id>.summary.txt`)

Write one plain-English reference summary per document in `data/gold/<doc_id>.summary.txt`:

- **Length:** **150–250 words** (strictly within this window so ROUGE/BERTScore baselines are comparable).
- **Readability:** Target **grade-8 English** — short sentences (12–18 words), active voice, concrete everyday words (replace *"hereinafter referred to as"* / *"indemnify"* with plain equivalents).
- **Structure:** Cover in order:
  1. What the document is and who the parties/authority are.
  2. Key **obligations** (what the reader must / must not do).
  3. Key **rights** (what the reader is allowed or protected to do).
  4. Key **deadlines** and **penalties** (dates, fees, consequences).
- **Grounding:** Include only facts explicitly stated in the document. Do **not** add external legal advice.

---

## 3. Question Answering Pairs (`<doc_id>.qa.json`)

Write **7 questions per document**: **5 answerable** + **2 unanswerable**.

```json
{
  "questions": [
    {
      "q": "How much is the late fee if rent is paid after the 10th day?",
      "answerable": true,
      "evidence_clause_ids": ["c9"],
      "gold_answer": "Rs. 500 per day after the 10th day."
    },
    {
      "q": "Does the landlord allow pets in the apartment?",
      "answerable": false,
      "evidence_clause_ids": [],
      "gold_answer": "The document does not mention whether pets are allowed."
    }
  ]
}
```

### Rules
- **5 Answerable (`"answerable": true`):**
  - Phrase natural citizen/user questions (avoid copying exact clause wording verbatim).
  - Include at least one question each covering an obligation/right, a deadline/amount, and a penalty.
  - List the exact supporting `id` string(s) from `<doc_id>.clauses.json` in `evidence_clause_ids` (e.g., `["c8", "c9"]`).
  - Keep `gold_answer` factual, concise (1–2 sentences), and strictly supported by the cited clauses.
- **2 Unanswerable (`"answerable": false`):**
  - Ask plausible, in-domain questions whose answer is genuinely missing from the document (e.g., pet policy in a lease that omits pets, arbitration city in a notice with none, refund timeline in a ToS without one).
  - Set `evidence_clause_ids` to `[]` and state clearly in `gold_answer` what is not specified in the document.
