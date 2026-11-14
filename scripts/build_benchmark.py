"""Materialize the source-based benchmark; does not run retrieval or tune models."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Evidence boundaries are copied from inspected normalized PDF pages.
SPECS = [
    (65, "direct", "What is the law of demand, and what must be held constant?", "Price and quantity demanded move inversely, holding all other variables affecting demand constant.", "Economists call this inverse relationship", "are held constant.", None),
    (66, "paraphrase", "How does demand differ from quantity demanded?", "Demand is the whole curve or schedule; quantity demanded is one particular point or quantity on it.", "When economists talk about demand,", "point on the curve.", None),
    (67, "direct", "How does supply differ from quantity supplied?", "Supply describes the relationship across prices; quantity supplied is a specific point on the curve or schedule.", "When economists refer to supply,", "point on the curve.", None),
    (68, "direct", "In the gasoline example, what are the equilibrium price and quantity, including the quantity unit?", "$1.40 per gallon and 600 million gallons.", "FIGURE 3.4 Demand and Supply for Gasoline", "TABLE 3.3 Price, Quantity Demanded, and Quantity Supplied", None),
    (70, "direct", "What does the ceteris paribus assumption require when using a demand or supply curve?", "All relevant economic factors other than the product's own price must remain unchanged.", "The assumption behind a demand curve", "are changing.", None),
    (71, "paraphrase", "In the car example, what happens to demand when incomes rise while the price remains $20,000?", "Quantity demanded increases to 20 million cars and the demand curve shifts right to D1.", "Return to Figure 3.5.", "original one.", None),
    (72, "direct", "What is a normal good?", "A product whose demand rises when income rises and falls when income falls.", "A product whose demand rises", "a normal good.", None),
    (73, "condition", "For an inferior good, how does an increase in income affect demand and the demand curve?", "Demand falls and the demand curve shifts left.", "A product whose", "shifts to the left.", None),
    (75, "paraphrase", "Does a change in a good's own price shift its demand curve? Explain the change instead.", "It causes movement along the existing demand curve and changes quantity demanded; it does not shift the curve.", "Notice that a change", "does not shift the demand curve.", None),
    (86, "condition", "In Chapter 3, when drought reduces wheat supply, does the resulting price rise shift the demand curve?", "No. Drought shifts supply back, reducing equilibrium quantity and raising price; this moves along the original demand curve.", "Answer: Lee", "from E0 to E1.", {"chapter": 3}),
    (103, "direct", "In the nurses example for Minneapolis-St. Paul-Bloomington, what are the equilibrium salary and number of nurses?", "$85,000 per year and 41,000 nurses.", "FIGURE 4.2 Labor Market Example", "41,000 nurses.", None),
    (104, "paraphrase", "In Chapter 4, why is the demand for labor described as derived demand?", "It depends on demand for the goods or services the labor produces; greater automobile demand, for example, requires more workers.", "One key reason is", "Here are some examples", {"chapter": 4}),
    (110, "direct", "Who supplies financial capital and who demands it?", "Savers or financial investors supply capital; borrowers demand it.", "Those who save money", "demand side of the financial market.", None),
    (111, "direct", "What does the horizontal axis show in the financial market for credit card borrowing?", "The quantity of money loaned or borrowed.", "The horizontal axis of the", "borrowed in this market.", None),
    (112, "condition", "In Chapter 4's credit card example, what happens to funds demanded and supplied if the interest rate is 13%, below equilibrium?", "Demand is $700 billion and supply is $510 billion, creating a shortage and pressure for interest rates to rise.", "If the interest rate is below the equilibrium,", "toward the equilibrium level.", {"chapter": 4}),
    (88, "condition", "In the rent-control example, with rent capped at $500 after demand increases, what are quantities supplied and demanded and the resulting shortage?", "Supply is 15,000 units and demand is 19,000 units, so the shortage is 4,000 rental units.", "Suppose that a city government", "shortage of rental housing.", None),
    (90, "direct", "How is consumer surplus defined?", "The amount people would have been willing to pay minus the amount they actually paid.", "The amount that individuals", "called consumer surplus.", None),
    (116, "condition", "According to Chapter 4, when does a relatively high interest-rate ceiling have no practical effect?", "When it is nonbinding: equilibrium remains below the ceiling. It has no practical effect unless equilibrium exceeds the ceiling.", "A price ceiling that is set", "exceed the price ceiling.", {"chapter": 4}),
    (117, "paraphrase", "Why can an oat farmer respond to a higher oat price without knowing exactly why it rose?", "The price itself signals that expanding production will be profitable; the farmer need not know the underlying causes.", "The oat farmer does not", "production as a result.", None),
    (118, "condition", "If demand for nurses increases while their supply decreases, what can be concluded about salaries and the number of nurses?", "Salaries rise, but the change in the number of nurses is uncertain and depends on the relative shifts.", "Suppose that as the demand for nurses increases,", "and demand.", None),
]


def main() -> None:
    pages = {p["page"]: p for p in (json.loads(line) for line in (ROOT / "data/processed/pages.jsonl").read_text(encoding="utf-8").splitlines())}
    questions = []
    for index, (page, kind, question, answer, start, end, filters) in enumerate(SPECS, 1):
        source = pages[page]
        text = source["text"]
        offset = text.index(start)
        stop = text.index(end, offset) + len(end)
        evidence = text[offset:stop]
        questions.append({
            "id": f"q{index:02}", "split": "dev" if index <= 15 else "test",
            "type": kind, "question": question, "expected_answer": answer,
            "gold_source_id": source["document_id"], "gold_page": page,
            "evidence_quote": evidence, "filter": filters,
            "filter_origin": "Chapter explicitly supplied in the question before retrieval." if filters else None,
            "evidence_verification": "Matched against normalized local PDF text; source passage read during benchmark authoring. Human student review pending.",
        })
    alternate_text = pages[104]["text"]
    alternate_start = alternate_text.index("The equilibrium quantity of nurses")
    alternate_end = alternate_text.index("per year.", alternate_start) + len("per year.")
    questions[10]["alternative_gold"] = [{
        "gold_source_id": pages[104]["document_id"], "gold_page": 104,
        "evidence_quote": alternate_text[alternate_start:alternate_end],
    }]
    target = ROOT / "benchmark"
    target.mkdir(exist_ok=True)
    (target / "questions.jsonl").write_text("".join(json.dumps(q, ensure_ascii=False) + "\n" for q in questions), encoding="utf-8")
    print(f"Wrote {len(questions)} questions (15 dev / 5 test); retrieval not run.")


if __name__ == "__main__":
    main()
