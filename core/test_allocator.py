import random, json, sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "simulator"))
from outcome_simulator import simulate_outcome, EVENTS

with open("reports/allocated_decisions.json") as f:
    decisions = {d["transaction_id"]: d["decision"] for d in json.load(f)}

total_amount = sum(e["amount"] for e in EVENTS.values())
SEEDS = [1, 2, 3, 7, 13, 21, 42, 99, 100, 256]

results = []
for seed in SEEDS:
    rng = random.Random(seed)
    recovered = 0.0
    for txn_id, action in decisions.items():
        if action == "skip":
            continue
        r = simulate_outcome(txn_id, action, attempt_number=1, rng=rng)
        if r["success"]:
            recovered += r["amount_recovered"]
    results.append(recovered / total_amount * 100)

mean = sum(results) / len(results)
print(f"Allocator (capacity-constrained): mean {mean:.1f}%, range {min(results):.1f}-{max(results):.1f}%")