# Kasai Signature Repealed-Law Benchmark Suite (Step 3)

This directory contains Kasai's signature **Adversarial Repealed-Law Benchmark Suite**, specifically designed to test whether Kasai can distinguish active 2024/2025 Nigerian tax legislation from obsolete laws that are no longer in force.

---

## 🎯 Benchmark Objective

The benchmark evaluates 7 critical capabilities:
1. **Recognize Repealed Laws**: Detect when a law (e.g. CITA, PITA, PPTA, legacy FIRS Act) has been repealed or superseded.
2. **Reject Obsolete Premise**: Avoid treating repealed statutes as active governing authority for current tax queries.
3. **Identify Replacing Legislation**: Point to active 2025 replacement acts (Nigeria Tax Act 2025, Nigeria Tax Administration Act 2025, NRS Act 2025).
4. **Correct User Premise**: Explicitly correct false premises in user questions.
5. **Apply Current Rules**: Provide the answer derived from current legal provisions.
6. **Cite Current Authority**: Cite valid current sections/acts.
7. **Handle Historical Context**: Accurately answer historical questions using old law *when the user explicitly asks about past tax periods*.

---

## 🎭 10 Adversarial Trap Categories (A – J)

| Category ID | Category Name | Description |
|---|---|---|
| **Cat-A** | Direct Current-Law Trap | User explicitly asks about current tax rules citing a repealed act name. |
| **Cat-B** | Implicit Repealed-Law Trap | Question contains obsolete terminology without mentioning the law is repealed. |
| **Cat-C** | Old Rate vs Current Rate | Question embeds an old tax rate and asks for current application. |
| **Cat-D** | Old Provision vs New Provision | Maps an old section (e.g., CITA Sec 19) to its modern 2025 counterpart. |
| **Cat-E** | Historical Question (Control) | User asks about historical law prior to 2026. Model MUST answer using old law. |
| **Cat-F** | Date-Based Trap | Tests dates (e.g. tax obligations in 2024 vs 2026). |
| **Cat-G** | False Premise Question | Premise asserts old law is still active ("Since CITA is the primary CIT act..."). |
| **Cat-H** | Conflicting Sources | Presents conflicting old vs new statutory text for 2026 application. |
| **Cat-I** | Outdated Internet Info | User quotes outdated online article text and asks if it remains valid. |
| **Cat-J** | Mixed Current + Repealed | Question compares CITA Section X to NTA Section Y for a 2026 transaction. |

---

## ⚠️ Severity Classification of Failures

- **Critical**: Model confidently presents a repealed law as current governing law.
- **Major**: Model identifies current law but cites the repealed act.
- **Moderate**: Model recognizes transition but gives an incomplete answer.
- **Minor**: Model gives correct law but explanation has minor omissions.

---

## 📂 Directory Layout

```text
benchmark/
└── repealed_law/
    ├── README.md                       # Benchmark documentation & severity scale
    ├── repealed_laws.json              # Statutory mapping registry of repealed acts
    ├── benchmark_schema.json           # JSON Schema validator
    ├── generate_repealed_suite.py      # Benchmark generator & validator script
    └── repealed_law_benchmark.jsonl    # 200-item adversarial benchmark dataset
```
