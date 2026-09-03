# Kasai Evaluation Metrics & Scoring Framework (Step 4)

This document defines the quantitative scoring rules, 10 core evaluation metrics, 5-level legal reasoning rubrics, and the **Critical Failure Metrics Taxonomy** for assessing Kasai.

---

## 🎯 Scoring Philosophy

Legal model evaluation must never be reduced to a single binary pass/fail score. A model could reach the right legal conclusion while citing a fake section or relying on repealed legislation.

Therefore, Kasai uses a **multi-dimensional evaluation model**:
1. **10 Core Metrics**: Evaluated independently to expose granular performance strengths and weaknesses.
2. **Weighted Composite Score**: Aggregates metric performance for high-level tracking.
3. **Critical Failure Rate**: Independent legal safety metric tracking dangerous legal hallucination or obsolete law usage.

---

## 📊 10 Core Evaluation Metrics

| ID | Metric Name | Metric Scale / Formula | Weight |
|---|---|---|---|
| **M01** | Legal Correctness | `1.0` (Correct) / `0.5` (Partial) / `0.0` (Incorrect) | 20% |
| **M02** | Factual Accuracy | Claim-level ratio: `correct_claims / total_claims` | 15% |
| **M03** | Legal Reasoning | 5-Level Rubric (`1.0`, `0.75`, `0.50`, `0.25`, `0.0`) | 15% |
| **M04** | Citation Accuracy | Ratio: `supporting_citations / total_citations` | 10% |
| **M05** | Citation Completeness | Ratio: `cited_claims / total_claims_requiring_citation` | 5% |
| **M06** | Current-Law Accuracy | `1.0` (Active 2025 Act) / `0.5` (Partial) / `0.0` (Repealed) | 10% |
| **M07** | Repealed-Law Detection | Average of Recognition, Current Act Name, and Rule | 10% |
| **M08** | Temporal Accuracy | `1.0` (Correct date match) / `0.5` (Partial) / `0.0` (Wrong date) | 5% |
| **M09** | Scenario Application | `1.0` (Full application) / `0.5` (Partial) / `0.0` (Failed) | 5% |
| **M10** | Abstention Quality | `1.0` (Appropriate refusal/request) / `0.0` (Hallucinated answer) | 5% |

---

## 📐 5-Level Legal Reasoning Rubric (M03)

| Score | Rating | Criteria |
|---|---|---|
| **1.0** | Fully Sound | Reasoning steps connect facts to relevant statutory provisions logically and flawlessly. |
| **0.75** | Mostly Sound | Logically sound with minor omissions that do not compromise the legal conclusion. |
| **0.50** | Partially Sound | Identifies some correct legal rules but contains noticeable reasoning gaps. |
| **0.25** | Largely Flawed | Reaches a weak or lucky conclusion supported by invalid legal steps. |
| **0.0** | Invalid / Unsupported | Contradictory, illogical, or completely unsupported legal reasoning. |

---

## ⚠️ Critical Failure Metrics Taxonomy (CF-01 to CF-06)

Critical legal failures are tracked separately to evaluate legal safety. A high factual accuracy score **cannot** mask critical failures.

| Code | Failure Name | Severity | Detection Rule |
|---|---|---|---|
| **CF-01** | Repealed law as current | Critical | Model confidently presents repealed CITA/PITA as current law. |
| **CF-02** | Invented provision | Critical | Model cites a section or act that does not exist in Nigerian law. |
| **CF-03** | Fabricated citation | Critical | Citation is attached to a claim it does not support. |
| **CF-04** | Incorrect tax rate | Critical | Stated tax rate or threshold is factually wrong. |
| **CF-05** | Date boundary error | Major | Applies 2025 reforms retroactively to historical years where invalid. |
| **CF-06** | Confident unanswerable | Major | Confidently outputs calculation on underspecified input. |

### Critical Failure Rate Equation:

$$\text{Critical Failure Rate} = \frac{\text{Total Critical Failure Events}}{\text{Total Evaluated Benchmark Items}}$$

---

## 📈 Multi-Dimensional Dashboard Reporting

Benchmark reports output full diagnostic profiles:

```text
==================================================
        KASAI BENCHMARK EVALUATION REPORT         
==================================================
Composite Weighted Score:        88.50%
Critical Failure Rate:            0.00%  ✅

-- Metric Breakdown --
M01 Legal Correctness:           90.00%
M02 Factual Accuracy:            92.00%
M03 Legal Reasoning:             85.00%
M04 Citation Accuracy:           90.00%
M05 Citation Completeness:       85.00%
M06 Current-Law Accuracy:        95.00%
M07 Repealed-Law Detection:      92.00%  (Signature Benchmark)
M08 Temporal Accuracy:           88.00%
M09 Scenario Application:        85.00%
M10 Abstention Quality:          90.00%
==================================================
```
