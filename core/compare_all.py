# core/compare_all.py
import random, json, sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "simulator"))
from outcome_simulator import simulate_outcome, EVENTS, GROUND_TRUTH

with open("reports/decisions.json") as f:
    AGENT_DECISIONS = {d["transaction_id"]: d["decision"] for d in json.load(f)}

total_amount = sum(e["amount"] for e in EVENTS.values())
SEEDS = [1, 2, 3, 7, 13, 21, 42, 99, 100, 256]

def run(action_fn, seed):
    rng = random.Random(seed)
    recovered = 0.0
    for txn_id in EVENTS:
        action = action_fn(txn_id)
        if action == "skip":
            continue
        r = simulate_outcome(txn_id, action, attempt_number=1, rng=rng)
        if r["success"]:
            recovered += r["amount_recovered"]
    return recovered / total_amount * 100

strategies = {
    "Baseline (always retry)": lambda txn_id: "retry",
    "Your Agent (rules+LLM, ERV-gated)": lambda txn_id: AGENT_DECISIONS[txn_id],
    "Oracle (perfect hidden knowledge)": lambda txn_id: GROUND_TRUTH[txn_id]["recovers_with_action"] or "escalate",
}

print(f"{'Strategy':<38} {'Mean %':>8} {'Range':>16}")
for name, fn in strategies.items():
    results = [run(fn, seed) for seed in SEEDS]
    mean = sum(results) / len(results)
    print(f"{name:<38} {mean:>7.1f}% {min(results):>6.1f}-{max(results):<6.1f}%")