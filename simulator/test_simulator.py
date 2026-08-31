import random
from outcome_simulator import EVENTS, GROUND_TRUTH, simulate_outcome


def run_batch(strategy_name, action_fn, rng):
    total_amount = sum(e["amount"] for e in EVENTS.values())
    recovered = 0.0
    recovered_count = 0

    for txn_id in EVENTS:
        action = action_fn(txn_id)
        result = simulate_outcome(txn_id, action, attempt_number=1, rng=rng)
        if result["success"]:
            recovered += result["amount_recovered"]
            recovered_count += 1

    print(f"\n[{strategy_name}]")
    print(f"  Recovered: Rs {recovered:.0f} / Rs {total_amount:.0f} "
          f"({recovered / total_amount * 100:.1f}%)")
    print(f"  Transactions recovered: {recovered_count} / {len(EVENTS)}")


if __name__ == "__main__":
    rng = random.Random(7)

    run_batch("Baseline: always retry", lambda txn_id: "retry", rng)

    run_batch(
        "Oracle: correct action per decline reason",
        lambda txn_id: GROUND_TRUTH[txn_id]["recovers_with_action"] or "escalate",
        rng,
    )