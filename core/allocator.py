# core/allocator.py
import json
import sys, os
sys.path.append(os.path.dirname(__file__))
from erv import compute_erv
from diagnosis_router import diagnose
from llm_diagnose import get_diagnose_fn
from constraints import DAILY_CAPACITY, passes_compliance

ACTIONS = ["retry", "switch_method", "nudge", "escalate"]

with open("data/events.json") as f:
    EVENTS = json.load(f)

def allocate_batch(events, capacity=None):
    capacity = capacity or DAILY_CAPACITY

    # Step 1: diagnose + score every transaction against every legal action
    diagnose_fn = get_diagnose_fn()  # decide once per batch, not per transaction
    per_txn_options = {}
    candidates = []
    for event in events:
        reason, method, confidence = diagnose(event, diagnose_fn)
        options = []
        for action in ACTIONS:
            ok, block_reason = passes_compliance(event, reason, action)
            if not ok:
                continue
            erv = compute_erv({**event, "decline_code": reason}, action)
            if erv <= 0:
                continue
            options.append({
                "transaction_id": event["transaction_id"],
                "amount": event["amount"],
                "diagnosed_reason": reason,
                "diagnosis_method": method,
                "action": action,
                "erv": erv,
            })
        options.sort(key=lambda c: c["erv"], reverse=True)
        per_txn_options[event["transaction_id"]] = options
        candidates.extend(options)

    # Step 2: greedily allocate capacity to the highest-ERV opportunities first
    candidates.sort(key=lambda c: c["erv"], reverse=True)
    remaining_capacity = dict(capacity)
    assigned_txns = set()
    decisions = []

    for c in candidates:
        if c["transaction_id"] in assigned_txns:
            continue
        if remaining_capacity[c["action"]] <= 0:
            continue
        remaining_capacity[c["action"]] -= 1
        assigned_txns.add(c["transaction_id"])
        wanted = per_txn_options[c["transaction_id"]][0]
        decisions.append({
            **c,
            "decision": c["action"],
            "wanted_action": wanted["action"],
            "got_first_choice": c["action"] == wanted["action"],
        })

    for event in events:
        if event["transaction_id"] not in assigned_txns:
            decisions.append({
                "transaction_id": event["transaction_id"],
                "amount": event["amount"],
                "decision": "skip",
                "reason": "no remaining capacity or no compliant/profitable action",
            })

    return decisions, remaining_capacity


if __name__ == "__main__":
    decisions, leftover_capacity = allocate_batch(EVENTS)

    with open("reports/allocated_decisions.json", "w") as f:
        json.dump(decisions, f, indent=2)

    skipped = sum(1 for d in decisions if d["decision"] == "skip")
    by_action = {}
    for d in decisions:
        if d["decision"] != "skip":
            by_action[d["decision"]] = by_action.get(d["decision"], 0) + 1

    print(f"Allocated {len(decisions) - skipped} / {len(decisions)} transactions")
    print(f"  By action: {by_action}")
    print(f"  Skipped (capacity exhausted): {skipped}")
    print(f"  Unused capacity remaining: {leftover_capacity}")