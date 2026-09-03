# Kasai Evaluation Categories

This document defines the 10 core evaluation categories for **Kasai**, an ethically guided, RAG-powered Small Language Model (SLM) delivering accurate, transparent, and plain-language legal answers regarding Nigerian tax laws.

---

## Evaluation Framework Overview

| Category ID | Category Name | Core Objective / Primary Question |
|---|---|---|
| **E01** | Factual Accuracy | Is the underlying legal fact (rates, thresholds, definitions) correct? |
| **E02** | Legal Interpretation | Did Kasai correctly interpret the scope and applicability of statutory provisions? |
| **E03** | Legal Reasoning | Can Kasai connect multiple statutory provisions to logically derive an answer? |
| **E04** | Citation Accuracy | Does the cited statutory provision directly support the claim made? |
| **E05** | Citation Completeness | Are all key legal claims in the response backed by appropriate citations? |
| **E06** | Current-Law Recognition | Does Kasai correctly identify and apply current in-force legislation (2024/2025 reforms)? |
| **E07** | Repealed-Law Detection | Can Kasai detect obsolete/repealed acts (e.g., old CITA/PITA) and reject traps? |
| **E08** | Temporal Reasoning | Does Kasai adapt its answer based on the date/tax year in question? |
| **E09** | Scenario / Application | Can Kasai accurately apply complex tax laws to realistic SME business scenarios? |
| **E10** | Abstention | Does Kasai appropriately decline to answer when facts or laws are underspecified? |

---

## 1. E01 — Factual Accuracy

### Objective
Measure whether Kasai provides factually correct information according to current Nigerian tax legislation (e.g., Nigeria Tax Act 2025, Nigeria Tax Administration Act 2025, NRS Act 2025, WHT Regulations 2024).

### Key Test Points
- Tax rates and statutory thresholds (e.g., VAT rates, small business thresholds, withholding rates).
- Statutory deadlines and filing windows.
- Definitions of terms (e.g., "Taxable Person", "Small Business", "Resident Individual").

### Example
- **Question:** What is the small business threshold for exemption from certain company income tax requirements under the Nigeria Tax Act 2025?
- **Expected Output:** State the precise statutory threshold and reference the Nigeria Tax Act 2025.
- **Incorrect Trap:** Citing pre-2025 CITA thresholds or incorrect monetary figures.

---

## 2. E02 — Legal Interpretation

### Objective
Measure whether Kasai accurately interprets the scope, intent, and boundaries of specific statutory provisions.

### Key Test Points
- Determining whether a provision applies to a specific taxpayer classification.
- Distinguishing exempt vs. taxable goods/services.
- Determining statutory obligations vs. options.

### Example
- **Question:** Under the Nigeria Tax Act 2025, does a non-resident digital services provider with no physical office in Nigeria fall under the scope of taxable income?
- **Expected Output:** Correctly identify statutory nexus/Significant Economic Presence rules without expanding scope beyond the legislation.

---

## 3. E03 — Legal Reasoning

### Objective
Evaluate Kasai's ability to chain multiple statutory provisions logically to reach a sound conclusion.

### Key Test Points
- Combining general rules with statutory exceptions.
- Resolving interactions between the Nigeria Tax Act 2025 and the Tax Administration Act 2025.

### Example
- **Question:** An SME qualifies as a small business under Section X, but earns passive investment income under Section Y. How do these provisions interact to determine tax liability?
- **Expected Output:** Step-by-step logical reasoning connecting Section X and Section Y to derive the net tax treatment.

---

## 4. E04 — Citation Accuracy

### Objective
Verify that every cited section, act, or regulation directly supports the exact legal statement made in the response.

### Key Test Points
- Verifying Section numbers match the quoted legal rule.
- Eliminating fabricated/hallucinated section citations.

### Example
- **Claim:** Deductions for Withholding Tax must be remitted within 21 days following the end of the month.
- **Citation:** *Deduction of Tax at Source (Withholding) Regulations 2024, Regulation 4*.
- **Evaluation:** Pass if Regulation 4 explicitly establishes the 21-day remittance window; fail if it references an unrelated subject.

---

## 5. E05 — Citation Completeness

### Objective
Measure whether all substantive legal assertions in an answer are accompanied by corresponding statutory citations.

### Key Test Points
- Calculating ratio of cited substantive claims to total substantive claims made.
- Flagging ungrounded legal assertions.

---

## 6. E06 — Current-Law Recognition

### Objective
Ensure Kasai prioritizes current, active 2024/2025 Nigerian tax legislation over legacy laws.

### Key Test Points
- Confirming active status of Nigeria Tax Act 2025 (NTA) and Nigeria Tax Administration Act 2025 (NTAA).
- Prioritizing current statutory authorities (Nigeria Revenue Service - NRS) over legacy bodies where applicable.

---

## 7. E07 — Repealed-Law Detection (Signature Benchmark)

### Objective
Test Kasai's resilience against questions framed around obsolete/repealed legislation (e.g., CITA Cap C21 LFN 2004, PITA Cap P8 LFN 2004, old VAT Act).

### Key Test Points
- Recognizing when a user explicitly asks about a repealed statute.
- Correctly informing the user that the law has been replaced or repealed.
- Providing the correct current rule under the 2025 Tax Acts.

### Example
- **Question:** According to the Companies Income Tax Act (CITA), what is the tax rate for technology startups?
- **Expected Answer:** Explicitly state that CITA has been repealed/superseded by the Nigeria Tax Act 2025, then provide the applicable 2025 rule.

---

## 8. E08 — Temporal Reasoning

### Objective
Assess whether Kasai correctly answers questions where legal rules differ depending on the target tax year or date.

### Key Test Points
- Differentiating between tax obligations prior to 2025 vs. post-2025 effective dates.
- Handling transitional provisions in the 2025 tax reform acts.

---

## 9. E09 — Scenario / Application Questions

### Objective
Test Kasai on multi-fact, real-world business scenarios representative of SME queries.

### Key Test Points
- Parsing complex scenarios (taxpayer type, turnover, income streams, expenses).
- Applying multi-step legal calculations and statutory rules accurately.

---

## 10. E10 — Abstention

### Objective
Ensure Kasai refrains from hallucinating or delivering definitive legal conclusions when critical facts are missing or statutory guidance is underspecified.

### Key Test Points
- Abstaining or requesting clarification when required facts (e.g., turnover, residence, entity type) are absent.
- Disclaiming non-legal tax advice appropriately.
