# core/test_agent.py
import json
import random
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "simulator"))
from outcome_simulator import simulate_outcome, EVENTS

with open("reports/decisions.json") as f:
    decisions = {d["transaction_id"]: d for d in json.load(f)}

rng = random.Random(7)  # same seed as Step 4, for a fair comparison
total_amount = sum(e["amount"] for e in EVENTS.values())
recovered, recovered_count, skipped = 0.0, 0, 0

for txn_id, d in decisions.items():
    if d["decision"] == "skip":
        skipped += 1
        continue
    result = simulate_outcome(txn_id, d["decision"], attempt_number=1, rng=rng)
    if result["success"]:
        recovered += result["amount_recovered"]
        recovered_count += 1

print("[Your Agent: rules+LLM diagnosis, ERV-gated actions]")
print(f"  Recovered: Rs {recovered:.0f} / Rs {total_amount:.0f} ({recovered/total_amount*100:.1f}%)")
print(f"  Transactions recovered: {recovered_count} / {len(decisions)}")
print(f"  Skipped (negative ERV): {skipped}")