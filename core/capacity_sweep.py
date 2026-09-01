# core/capacity_sweep.py
import random, sys, os
sys.path.append(os.path.dirname(__file__))
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "simulator"))
from allocator import allocate_batch, EVENTS
from constraints import DAILY_CAPACITY
from outcome_simulator import simulate_outcome

SEEDS = [1, 2, 3, 7, 13, 21, 42, 99, 100, 256]
SCALES = [1.0, 0.75, 0.5, 0.25]
total_amount = sum(e["amount"] for e in EVENTS)

print(f"{'Capacity':>10} {'Served':>8} {'Mean Recovered %':>18}")
for scale in SCALES:
    scaled_capacity = {k: max(1, round(v * scale)) for k, v in DAILY_CAPACITY.items()}
    decisions, _ = allocate_batch(EVENTS, capacity=scaled_capacity)
    served = sum(1 for d in decisions if d["decision"] != "skip")

    results = []
    for seed in SEEDS:
        rng = random.Random(seed)
        recovered = 0.0
        for d in decisions:
            if d["decision"] == "skip":
                continue
            r = simulate_outcome(d["transaction_id"], d["decision"], attempt_number=1, rng=rng)
            if r["success"]:
                recovered += r["amount_recovered"]
        results.append(recovered / total_amount * 100)

    mean = sum(results) / len(results)
    print(f"{int(scale*100):>9}% {served:>8} {mean:>17.1f}%")