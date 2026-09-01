import json, sys

with open("reports/workflow_state.json", encoding="utf-8") as f:
    state = json.load(f)


def trace(txn_id):
    s = state[txn_id]
    print(f"Transaction {txn_id} -- final status: {s['status']}")
    print(f"  Amount at stake: Rs {s['event']['amount']}, true decline reason: {s['event']['decline_code']}")
    for h in s["history"]:
        line = f"  Day {h['day']}: attempt {h['attempt']} -> action '{h['action']}' -> {h['outcome']}"
        if h.get("amount_recovered"):
            line += f" (Rs {h['amount_recovered']:.0f})"
        print(line)


if __name__ == "__main__":
    txn_id = sys.argv[1] if len(sys.argv) > 1 else None
    if txn_id:
        trace(txn_id)
    else:
        multi_attempt = [tid for tid, s in state.items() if len(s["history"]) >= 2]
        if multi_attempt:
            trace(multi_attempt[0])
        else:
            print("No multi-attempt transactions found -- pass a transaction_id as an argument.")