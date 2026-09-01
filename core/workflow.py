import json, random, sys, os
sys.path.append(os.path.dirname(__file__))
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "simulator"))
from allocator import allocate_batch
from constraints import DAILY_CAPACITY
from outcome_simulator import simulate_outcome

COOLDOWN_DAYS = {"retry": 2, "switch_method": 2, "nudge": 1}
MAX_DAYS = 10
DEMO_SEED = 42

with open("data/events.json") as f:
    RAW_EVENTS = json.load(f)


def run_workflow(events, seed=DEMO_SEED, max_days=MAX_DAYS):
    rng = random.Random(seed)

    state = {}
    for e in events:
        state[e["transaction_id"]] = {
            "event": dict(e),
            "status": "open",  # open -> recovered | escalated | unresolved_timeout
            "last_action_day": None,
            "last_action": None,
            "history": [],
        }

    daily_log = []

    for day in range(1, max_days + 1):
        # who's eligible today: open, and past cooldown from their last action
        eligible_events = []
        for txn_id, s in state.items():
            if s["status"] != "open":
                continue
            if s["last_action_day"] is None:
                eligible_events.append(s["event"])
                continue
            cooldown = COOLDOWN_DAYS.get(s["last_action"], 0)
            if day - s["last_action_day"] >= cooldown:
                eligible_events.append(s["event"])

        if not eligible_events:
            continue

        decisions, _ = allocate_batch(eligible_events, capacity=DAILY_CAPACITY)

        day_recovered = 0.0
        day_actions = 0
        for d in decisions:
            txn_id = d["transaction_id"]
            s = state[txn_id]
            if d["decision"] == "skip":
                continue  # capacity exhausted today -- stays open, tries again next eligible day

            day_actions += 1
            action = d["decision"]
            attempt = s["event"]["attempt_number"]

            if action == "escalate":
                s["status"] = "escalated"
                s["history"].append({"day": day, "action": action, "attempt": attempt, "outcome": "escalated"})
                continue

            result = simulate_outcome(txn_id, action, attempt_number=attempt, rng=rng)
            s["history"].append({
                "day": day, "action": action, "attempt": attempt,
                "outcome": "recovered" if result["success"] else "not_recovered",
                "amount_recovered": result["amount_recovered"],
            })

            if result["success"]:
                s["status"] = "recovered"
                day_recovered += result["amount_recovered"]
            else:
                s["event"]["attempt_number"] += 1
                s["last_action_day"] = day
                s["last_action"] = action

        daily_log.append({"day": day, "actions_taken": day_actions, "recovered_today": day_recovered})

        if all(s["status"] != "open" for s in state.values()):
            break  # everything resolved -- no need to keep simulating empty days

    for s in state.values():
        if s["status"] == "open":
            s["status"] = "unresolved_timeout"

    return state, daily_log


if __name__ == "__main__":
    state, daily_log = run_workflow(RAW_EVENTS)

    total_amount = sum(e["amount"] for e in RAW_EVENTS)

    status_amounts = {}
    for s in state.values():
        amt = s["event"]["amount"]
        bucket = status_amounts.setdefault(s["status"], [0, 0.0])
        bucket[0] += 1
        bucket[1] += amt

    recovered_by_attempt = {}
    recovered_amount = 0.0
    for s in state.values():
        for h in s["history"]:
            if h["outcome"] == "recovered":
                recovered_by_attempt[h["attempt"]] = recovered_by_attempt.get(h["attempt"], 0.0) + h["amount_recovered"]
                recovered_amount += h["amount_recovered"]

    print(f"Workflow complete over {len(daily_log)} active days\n")
    print(f"Recovered: Rs {recovered_amount:.0f} / Rs {total_amount:.0f} ({recovered_amount/total_amount*100:.1f}%)\n")

    print("Final status breakdown:")
    for status, (count, amt) in status_amounts.items():
        print(f"  {status:<20} {count:>3} txns, Rs {amt:.0f} at stake")

    print("\nRecovered revenue by attempt number:")
    for attempt in sorted(recovered_by_attempt):
        amt = recovered_by_attempt[attempt]
        print(f"  Attempt {attempt}: Rs {amt:.0f} ({amt/recovered_amount*100:.1f}% of recovered revenue)")

    print("\nDaily activity:")
    for d in daily_log:
        print(f"  Day {d['day']:>2}: {d['actions_taken']:>3} actions, Rs {d['recovered_today']:.0f} recovered")

    with open("reports/workflow_state.json", "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)
    print("\nFull state written -> reports/workflow_state.json")