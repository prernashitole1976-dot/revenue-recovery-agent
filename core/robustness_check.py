# core/robustness_check.py
import random
import sys, os, json
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "simulator"))
from outcome_simulator import simulate_outcome, EVENTS

with open("reports/decisions.json") as f:
    decisions = {d["transaction_id"]: d for d in json.load(f)}

total_amount = sum(e["amount"] for e in EVENTS.values())
SEEDS = [1, 2, 3, 7, 13, 21, 42, 99, 100, 256]

results = []
for seed in SEEDS:
    rng = random.Random(seed)
    recovered = 0.0
    for txn_id, d in decisions.items():
        if d["decision"] == "skip":
            continue
        r = simulate_outcome(txn_id, d["decision"], attempt_number=1, rng=rng)
        if r["success"]:
            recovered += r["amount_recovered"]
    results.append(recovered / total_amount * 100)

mean_pct = sum(results) / len(results)
spread = max(results) - min(results)

print(f"Across {len(SEEDS)} runs:")
print(f"  Mean recovery rate: {mean_pct:.1f}%")
print(f"  Range: {min(results):.1f}% - {max(results):.1f}%")
print(f"  All runs: {[round(r,1) for r in results]}")