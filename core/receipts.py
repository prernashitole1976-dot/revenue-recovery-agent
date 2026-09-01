# core/receipts.py
import json, random, sys, os
sys.path.append(os.path.dirname(__file__))
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "simulator"))
from allocator import allocate_batch, EVENTS
from outcome_simulator import simulate_outcome

DEMO_SEED = 42  # fixed seed -- this is the run you'll show in your pitch video

def make_receipt(decision, event, result):
    if decision["decision"] == "skip":
        return (f"{decision['transaction_id']}: SKIPPED -- {decision.get('reason', 'no capacity/profitable action')}. "
                f"₹{event['amount']} left at risk.")

    outcome = "RECOVERED" if result["success"] else "NOT RECOVERED"
    amt = f"₹{result['amount_recovered']:.0f}" if result["success"] else f"₹0 of ₹{event['amount']}"
    return (f"{decision['transaction_id']}: diagnosed '{decision['diagnosed_reason']}' "
            f"(via {decision['diagnosis_method']}, ERV=₹{decision['erv']:.0f}) -> "
            f"chose '{decision['decision']}' -> {outcome} ({amt}). {result['note']}")


if __name__ == "__main__":
    events_by_id = {e["transaction_id"]: e for e in EVENTS}
    decisions, _ = allocate_batch(EVENTS)
    rng = random.Random(DEMO_SEED)

    receipts, audit_log = [], []
    for d in decisions:
        event = events_by_id[d["transaction_id"]]
        if d["decision"] == "skip":
            result = {"success": False, "amount_recovered": 0.0, "note": ""}
        else:
            result = simulate_outcome(d["transaction_id"], d["decision"], attempt_number=1, rng=rng)

        receipts.append(make_receipt(d, event, result))
        audit_log.append({**d, "outcome": result})

    with open("reports/audit_trail.json", "w") as f:
        json.dump(audit_log, f, indent=2)
    with open("reports/recovery_receipts.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(receipts))

    total_recovered = sum(a["outcome"]["amount_recovered"] for a in audit_log)
    print(f"Wrote {len(receipts)} receipts -> reports/recovery_receipts.txt")
    print(f"Demo run (seed={DEMO_SEED}) recovered: Rs {total_recovered:.0f}")
    print("\nSample receipts:")
    for r in receipts[:5]:
        print(f"  {r}")