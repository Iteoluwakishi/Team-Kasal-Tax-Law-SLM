import json
import re
from pathlib import Path

# Paths are relative to this script's location in the repo:
# team-kasai-tax-slm/training/sft_dataset/build_sft_dataset.py
# Source is the 78-row Q&A dataset from data/qa_pairs/ (adjust if your repo
# layout differs — see training/sft_dataset/README.md for where this came from).
SRC = Path(__file__).parent.parent.parent / "data" / "qa_pairs" / "training_candidates.jsonl"
OUT_DIR = Path(__file__).parent
OUT_DIR.mkdir(parents=True, exist_ok=True)

CITATION_PATTERN = re.compile(r"^which (section|provision|part|schedule)", re.IGNORECASE)

# ============================================================
# 1. Load existing 78 rows and map each to one of the 8 required
#    SFT categories, using its existing question_type/difficulty.
# ============================================================

CATEGORY_NAMES = {
    1: "factual",
    2: "tax_calculation_scenario",
    3: "legal_interpretation",
    4: "legal_reasoning",
    5: "citation",
    6: "current_law_recognition",
    7: "repealed_law_detection",
    8: "abstention_uncertainty",
}

def map_category(rec):
    qtype = rec["metadata"]["question_type"]
    difficulty = rec["metadata"]["difficulty"]
    question = rec["instruction"]

    if qtype == "current_vs_repealed":
        return 7
    if qtype == "legal_interpretation":
        if CITATION_PATTERN.match(question.strip()):
            return 5
        return 3
    if qtype == "scenario":
        return 2
    if qtype == "contextual" and difficulty in ("hard", "expert"):
        return 4
    # basic, and easier contextual questions -> straightforward factual recall
    return 1

converted = []
with open(SRC, encoding="utf-8") as f:
    for line in f:
        rec = json.loads(line)
        cat = map_category(rec)
        converted.append({
            "messages": [
                {"role": "user", "content": rec["instruction"]},
                {"role": "assistant", "content": rec["output"]},
            ],
            "metadata": {
                "id": rec["id"],
                "sft_category": CATEGORY_NAMES[cat],
                "act": rec["metadata"]["act"],
                "status": rec["metadata"]["status"],
                "citation": rec["metadata"]["citation"],
                "confidence": rec["metadata"]["confidence"],
                "reviewed": False,
                "approved": None,
            },
        })

# ============================================================
# 2. New hand-written examples for categories the existing 78
#    rows don't cover well: current-law recognition (6) and
#    abstention/uncertainty (8) — both were entirely absent.
# ============================================================

new_examples = [
    # --- Category 6: current-law recognition (affirmative contrast pair
    #     to the repealed-law detection examples) ---
    {
        "id": "q_new_currentlaw_1",
        "user": "Is the Nigeria Tax Act currently in force?",
        "assistant": "Yes. The Nigeria Tax Act took effect on 1 January 2026 and is the current legislation governing income tax, VAT, capital gains, and related taxes in Nigeria.",
        "act": "Nigeria Tax Act (NTA) 2025", "status": "current",
        "citation": "Nigeria Tax Act (NTA) 2025",
    },
    {
        "id": "q_new_currentlaw_2",
        "user": "Is 7.5% the current applicable VAT rate in Nigeria?",
        "assistant": "Yes, 7.5% is the current VAT rate, charged under section 147 of the Nigeria Tax Act, effective from 1 January 2026.",
        "act": "Nigeria Tax Act (NTA) 2025", "status": "current",
        "citation": "Nigeria Tax Act (NTA) 2025, Section 147",
    },
    {
        "id": "q_new_currentlaw_3",
        "user": "Is the Nigeria Revenue Service the current federal tax authority in Nigeria?",
        "assistant": "Yes. The Nigeria Revenue Service (NRS), established under the Nigeria Revenue Service (Establishment) Act 2025, is the current federal tax authority, having replaced the Federal Inland Revenue Service (FIRS) from 1 January 2026.",
        "act": "Nigeria Revenue Service (Establishment) Act (NRSEA) 2025", "status": "current",
        "citation": "Nigeria Revenue Service (Establishment) Act (NRSEA) 2025",
    },
    {
        "id": "q_new_currentlaw_4",
        "user": "Is the Joint Revenue Board of Nigeria currently the body that coordinates between federal and state tax authorities?",
        "assistant": "Yes. The Joint Revenue Board of Nigeria, established under the Joint Revenue Board of Nigeria (Establishment) Act 2025 (effective 26 June 2025), currently performs this coordinating role, having taken over from the former Joint Tax Board.",
        "act": "Joint Revenue Board of Nigeria (Establishment) Act (JRBA) 2025", "status": "current",
        "citation": "Joint Revenue Board of Nigeria (Establishment) Act (JRBA) 2025",
    },
    {
        "id": "q_new_currentlaw_5",
        "user": "Does the Nigeria Tax Administration Act currently govern how and when PAYE returns must be filed?",
        "assistant": "Yes. Section 14 of the Nigeria Tax Administration Act currently governs employer PAYE returns, requiring filing by 31 January each year, effective from 1 January 2026.",
        "act": "Nigeria Tax Administration Act (NTAA) 2025", "status": "current",
        "citation": "Nigeria Tax Administration Act (NTAA) 2025, Section 14",
    },
    {
        "id": "q_new_currentlaw_6",
        "user": "Is the 4% development levy currently applicable to companies in Nigeria?",
        "assistant": "Yes, the 4% development levy under section 59 of the Nigeria Tax Act is currently applicable to companies, other than small companies and non-resident companies, which are excluded.",
        "act": "Nigeria Tax Act (NTA) 2025", "status": "current",
        "citation": "Nigeria Tax Act (NTA) 2025, Section 59",
    },

    # --- Category 8: abstention/uncertainty — questions the reviewed
    #     source material does NOT answer; correct behaviour is to say
    #     so rather than fabricate a confident-sounding answer. ---
    {
        "id": "q_new_abstain_1",
        "user": "How is income from cryptocurrency trading taxed under Nigerian tax law?",
        "assistant": "The materials I have reviewed do not specifically address cryptocurrency or digital asset taxation. I can't give a confident answer on this from the current source documents — please consult the Nigeria Revenue Service's published guidance or a qualified tax practitioner for this specific area.",
        "act": "N/A — outside reviewed source material", "status": "current",
        "citation": "N/A",
    },
    {
        "id": "q_new_abstain_2",
        "user": "What VAT rate will apply in Nigeria from 2030 onward?",
        "assistant": "I don't have information confirming any future VAT rate change. The current rate is 7.5% under section 147 of the Nigeria Tax Act, but the material I've reviewed doesn't specify or predict any change beyond the present rate.",
        "act": "Nigeria Tax Act (NTA) 2025", "status": "current",
        "citation": "Nigeria Tax Act (NTA) 2025, Section 147",
    },
    {
        "id": "q_new_abstain_3",
        "user": "On what exact date will the companies income tax rate reduce from 30% to 25%?",
        "assistant": "The Nigeria Tax Act does not specify an exact date — it only provides that the rate reduces to 25% from a date the President may set on the advice of the National Economic Council. I don't have information on whether that date has been fixed or announced.",
        "act": "Nigeria Tax Act (NTA) 2025", "status": "current",
        "citation": "Nigeria Tax Act (NTA) 2025, Section 56",
    },
    {
        "id": "q_new_abstain_4",
        "user": "What stamp duty rate applies to a divorce settlement deed under the Nigeria Tax Act?",
        "assistant": "The Ninth Schedule provisions I've reviewed don't specifically enumerate a rate for divorce settlement deeds. I can't confidently state a specific rate for this instrument type without checking the full Schedule directly — this would need confirmation from the complete Ninth Schedule text or a tax practitioner.",
        "act": "Nigeria Tax Act (NTA) 2025", "status": "current",
        "citation": "Nigeria Tax Act (NTA) 2025, Section 123",
    },
    {
        "id": "q_new_abstain_5",
        "user": "Can a foreign remote worker with no physical presence in Nigeria be taxed on income earned while working for a Nigerian company?",
        "assistant": "This depends on residency and source-of-income rules that require case-specific analysis I can't fully resolve from the material reviewed so far. I'd want to check the Act's specific residency and non-resident taxation provisions in detail before giving a definitive answer — this isn't something I can confidently confirm generally.",
        "act": "N/A — requires deeper review of NTA residency provisions", "status": "current",
        "citation": "N/A",
    },
    {
        "id": "q_new_abstain_6",
        "user": "Does the fiscalisation system penalty under the Nigeria Tax Administration Act apply retroactively to transactions that occurred before the Act's 2026 effective date?",
        "assistant": "The material I've reviewed doesn't address retroactive application of this penalty. Tax penalty provisions are generally not applied retroactively as a matter of legal principle, but I don't have a specific provision from the Act confirming this for section 104 — this would need direct confirmation from the Act's commencement/transitional provisions or legal advice.",
        "act": "Nigeria Tax Administration Act (NTAA) 2025", "status": "current",
        "citation": "N/A — not confirmed in reviewed material",
    },
    {
        "id": "q_new_abstain_7",
        "user": "Is there a minor-error exception that waives the filing penalty for mistakes under N10,000 in value?",
        "assistant": "I don't see a de minimis or minor-error exception in the filing-penalty provisions I've reviewed (section 101 of the Nigeria Tax Administration Act). I can't confirm one exists — if this matters for a real filing situation, it should be checked directly against the full Act text or confirmed with the tax authority rather than relying on my answer.",
        "act": "Nigeria Tax Administration Act (NTAA) 2025", "status": "current",
        "citation": "Nigeria Tax Administration Act (NTAA) 2025, Section 101",
    },
    {
        "id": "q_new_abstain_8",
        "user": "What specific VAT treatment applies to the sale of NFTs (non-fungible tokens) in Nigeria?",
        "assistant": "The VAT exempt and zero-rated supply lists I've reviewed don't mention NFTs or digital assets specifically. I can't confidently classify their VAT treatment from the material available — this looks like an area not explicitly addressed by the reviewed provisions, so it would need direct confirmation from NRS guidance rather than an inferred answer.",
        "act": "Nigeria Tax Act (NTA) 2025", "status": "current",
        "citation": "N/A — not addressed in reviewed material",
    },
]

reasoning_examples = [
    {
        "id": "q_new_reasoning_1",
        "user": "A company qualifies as a 'small company' for companies income tax purposes. Does that mean it's also automatically exempt from the development levy?",
        "assistant": "Yes, in this case — though for a related but distinct reason. Under section 56, small companies pay 0% companies income tax. Separately, under section 59, the development levy explicitly excludes small companies (and non-resident companies) from its 4% charge. So a small company is exempt from both, but each exemption comes from its own specific provision rather than one implying the other automatically — a company should confirm it meets the 'small company' definition for both purposes rather than assume one exemption covers the other.",
        "act": "Nigeria Tax Act (NTA) 2025", "status": "current",
        "citation": "Nigeria Tax Act (NTA) 2025, Sections 56 and 59",
    },
    {
        "id": "q_new_reasoning_2",
        "user": "If a supply is zero-rated for VAT rather than exempt, does the supplier still need to register for tax and file returns?",
        "assistant": "Yes. Zero-rating (section 186) only affects the VAT rate applied to that supply — it's still a taxable supply, just charged at 0% — unlike an exempt supply (section 185), which falls outside the VAT system. Since the supplier is still making taxable supplies, the general registration obligation under NTAA section 4 and the return-filing obligations under NTAA sections 11 and beyond still apply, regardless of the 0% rate on this specific supply.",
        "act": "Nigeria Tax Act (NTA) 2025 / Nigeria Tax Administration Act (NTAA) 2025", "status": "current",
        "citation": "NTA Section 186; NTAA Sections 4, 11",
    },
    {
        "id": "q_new_reasoning_3",
        "user": "A business honestly miscalculates its VAT refund claim by overstating it due to an accounting error, with no intent to deceive. Does the 100% penalty for a false or fictitious VAT refund claim under NTAA section 122 apply?",
        "assistant": "Based on the wording, likely not directly — section 122's penalty targets claims obtained through a 'false or fictitious' claim, which suggests an element of dishonesty or fabrication rather than a genuine accounting mistake. That said, the material I've reviewed doesn't spell out exactly how 'false or fictitious' is distinguished from honest error in practice, so this is a reasoned interpretation rather than a certainty — a business in this position should still expect to repay the overstated amount, and should get a definitive answer from a tax practitioner rather than rely solely on this distinction.",
        "act": "Nigeria Tax Administration Act (NTAA) 2025", "status": "current",
        "citation": "Nigeria Tax Administration Act (NTAA) 2025, Section 122",
    },
    {
        "id": "q_new_reasoning_4",
        "user": "Under the old law, a capital gain was taxed at a flat 10% regardless of who earned it. Does an individual now pay a different effective rate on the same kind of gain under the Nigeria Tax Act?",
        "assistant": "Likely yes, and the direction depends on the individual's income level. Since chargeable gains are now folded into total income and taxed under the Fourth Schedule's progressive bands (0% up to N800,000, rising to 25% above N50,000,000) rather than a flat 10%, an individual with modest total income could now pay less than 10% on a gain, while a higher earner could pay more (up to 25%) — a change from the old CGTA's flat rate to a progressive, income-dependent outcome.",
        "act": "Nigeria Tax Act (NTA) 2025", "status": "current",
        "citation": "Nigeria Tax Act (NTA) 2025, Part VIII of Chapter Two; Fourth Schedule",
    },
]

for ex in new_examples + reasoning_examples:
    if ex["id"].startswith("q_new_currentlaw"):
        cat = 6
    elif ex["id"].startswith("q_new_reasoning"):
        cat = 4
    else:
        cat = 8
    converted.append({
        "messages": [
            {"role": "user", "content": ex["user"]},
            {"role": "assistant", "content": ex["assistant"]},
        ],
        "metadata": {
            "id": ex["id"],
            "sft_category": CATEGORY_NAMES[cat],
            "act": ex["act"],
            "status": ex["status"],
            "citation": ex["citation"],
            "confidence": "high" if cat == 6 else "n/a (abstention example)",
            "reviewed": False,
            "approved": None,
        },
    })

# ============================================================
# 3. Write output + a category-count summary
# ============================================================

out_path = OUT_DIR / "kasai_sft_dataset.jsonl"
with open(out_path, "w", encoding="utf-8") as f:
    for rec in converted:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

from collections import Counter
counts = Counter(r["metadata"]["sft_category"] for r in converted)

print(f"Total examples: {len(converted)}")
for name in CATEGORY_NAMES.values():
    print(f"  {name}: {counts.get(name, 0)}")
