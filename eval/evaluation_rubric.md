# Kasai Evaluation Rubric

This document defines the quantitative scoring rules (0.0 to 1.0) and evaluator checklists for assessing Kasai's responses across all 10 evaluation categories.

---

## General Scoring Scale

| Score | Rating | Criteria |
|---|---|---|
| **1.0** | **Fully Satisfied** | Complete, accurate, correctly cited, and adheres strictly to active Nigerian tax law. |
| **0.5** | **Partially Satisfied** | Partially correct or incomplete citation, but contains no major legal misstatements. |
| **0.0** | **Unsatisfied / Fail** | Factually incorrect, relies on repealed law without notice, hallucinated citation, or invalid reasoning. |

---

## Category-Specific Rubrics

### E01: Factual Accuracy
- **1.0**: All rates, thresholds, deadlines, and definitions strictly match current 2024/2025 legislation.
- **0.5**: Fact is substantially correct but omits minor statutory nuances or conditions.
- **0.0**: Incorrect numbers, wrong deadlines, or false statements.

### E02: Legal Interpretation
- **1.0**: Scope and applicability of the statutory provision are accurately identified and applied.
- **0.5**: Interpretation is reasonable but overly broad or slightly narrow.
- **0.0**: Misinterprets legal text or extends law beyond statutory language.

### E03: Legal Reasoning
- **1.0**: Logical premises correctly connect multiple sections to arrive at the sound conclusion.
- **0.5**: Reaches correct conclusion but reasoning steps contain gaps or minor logical flaws.
- **0.0**: Flawed logic, contradictory statements, or invalid conclusions.

### E04: Citation Accuracy
- **1.0**: Every cited Act, Section, or Regulation directly contains and supports the associated claim.
- **0.5**: Citation points to correct Act but wrong section, or section partially supports claim.
- **0.0**: Hallucinated section, non-existent Act, or citation completely irrelevant to claim.

### E05: Citation Completeness
- Score calculated as: `(Number of Substantive Claims with Valid Citations) / (Total Substantive Claims Made)`
- **1.0**: 100% of substantive legal claims are cited.
- **0.5**: 50%–99% of substantive legal claims are cited.
- **0.0**: Less than 50% of claims are cited.

### E06: Current-Law Recognition
- **1.0**: Explicitly uses active 2024/2025 legal framework (NTA 2025, NTAA 2025, NRS Act 2025).
- **0.5**: Uses current rules but does not explicitly name the active governing act.
- **0.0**: Relies on old framework without acknowledging 2025 reforms.

### E07: Repealed-Law Detection (Signature Benchmark)
- **Sub-Metric 1 (Recognition)**: Identifies that the queried act/provision (e.g., old CITA/PITA) is repealed (0 or 1).
- **Sub-Metric 2 (Current Identification)**: Names the current replacing legislation (0 or 1).
- **Sub-Metric 3 (Correct Answer)**: Answers using the active 2025 legal rule (0 or 1).
- **Final E07 Score**: Average of the 3 sub-metrics.

### E08: Temporal Reasoning
- **1.0**: Correctly distinguishes rules applicable to historical tax years vs current tax years.
- **0.5**: Answers correctly for target year but fails to explain effective date boundaries.
- **0.0**: Applies 2025 rules retroactively to historical years where invalid, or vice versa.

### E09: Scenario / Application Questions
- **1.0**: Parses all scenario variables correctly, applies relevant provisions, and yields exact tax output/guidance.
- **0.5**: Applies correct law but misses one scenario condition or calculation detail.
- **0.0**: Fails to solve scenario or applies wrong tax provisions.

### E10: Abstention
- **1.0**: Refuses to provide definitive legal outcome when key facts are missing; requests missing details.
- **0.5**: Gives conditional answer while explicitly highlighting missing facts.
- **0.0**: Hallucinates missing scenario facts or gives definitive conclusion on underspecified query.
