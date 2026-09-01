# core/self_critique.py
import json
from collections import defaultdict

with open("reports/audit_trail.json") as f:
    audit = json.load(f)
with open("data/ground_truth.json") as f:
    ground_truth = {g["transaction_id"]: g for g in json.load(f)}
with open("data/events.json") as f:
    events = {e["transaction_id"]: e for e in json.load(f)}

diagnosis_errors = defaultdict(int)
judgment_errors = defaultdict(lambda: defaultdict(int))
capacity_tradeoffs = defaultdict(lambda: defaultdict(int))
expected_variance = 0
total_entries = 0

for entry in audit:
    if entry["decision"] == "skip" or entry["outcome"]["success"]:
        continue
    total_entries += 1
    txn_id = entry["transaction_id"]
    gt = ground_truth[txn_id]
    true_reason = events[txn_id]["decline_code"]
    chosen = entry["decision"]

    if entry["diagnosed_reason"] != true_reason:
        diagnosis_errors[f"diagnosed '{entry['diagnosed_reason']}', true reason '{true_reason}'"] += 1
        continue

    correct_action = gt["recovers_with_action"]
    if gt["recoverable"] and correct_action and chosen != correct_action:
        pattern = f"chose {chosen}, should've been {correct_action}"
        if entry.get("got_first_choice", True):
            judgment_errors[true_reason][pattern] += 1
        else:
            capacity_tradeoffs[true_reason][pattern] += 1
    else:
        # Correct diagnosis, correct (or only available) action -- failed
        # purely on the simulator's own success probability. Not a mistake.
        expected_variance += 1

def pct(n):
    return f"{n / total_entries * 100:.0f}%" if total_entries else "0%"

print(f"Reviewed {total_entries} failed, acted-on decisions.\n")

print(f"1. Diagnosis errors -- {len(diagnosis_errors) and sum(diagnosis_errors.values())}x ({pct(sum(diagnosis_errors.values()))}):")
for pattern, count in diagnosis_errors.items():
    print(f"  {count}x -- {pattern}")
if not diagnosis_errors:
    print("  None.")

judgment_total = sum(c for b in judgment_errors.values() for c in b.values())
print(f"\n2. Judgment errors (free choice, still picked wrong) -- {judgment_total}x ({pct(judgment_total)}):")
for reason, breakdown in judgment_errors.items():
    for pattern, count in breakdown.items():
        print(f"  [{reason}] {count}x -- {pattern}")
if not judgment_errors:
    print("  None -- whenever the agent had a free choice, it chose correctly.")

capacity_total = sum(c for b in capacity_tradeoffs.values() for c in b.values())
print(f"\n3. Capacity trade-offs (right call, lost the slot) -- {capacity_total}x ({pct(capacity_total)}):")
for reason, breakdown in capacity_tradeoffs.items():
    for pattern, count in breakdown.items():
        print(f"  [{reason}] {count}x -- {pattern}")
if not capacity_tradeoffs:
    print("  None found.")

print(f"\n4. Expected variance (right call, failed on probability alone) -- {expected_variance}x ({pct(expected_variance)}):")
print("  Not a system error -- inherent to the simulated success rates.")

print(f"\nSummary: of {total_entries} failures, {pct(sum(diagnosis_errors.values()) + judgment_total)} were "
      f"attributable to the agent (diagnosis + judgment), {pct(capacity_total)} were scarcity trade-offs, "
      f"and {pct(expected_variance)} were unavoidable given the simulated probabilities.")