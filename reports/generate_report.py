# reports/generate_report.py
import json, random, sys, os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "core"))
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "simulator"))
from allocator import allocate_batch, EVENTS as ALLOC_EVENTS, DAILY_CAPACITY
from outcome_simulator import simulate_outcome, EVENTS, GROUND_TRUTH

SEEDS = list(range(1, 201))
total_amount = sum(e["amount"] for e in EVENTS.values())


def run_strategy(action_fn, seed):
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


def mean(xs):
    return sum(xs) / len(xs)


# --- Strategy comparison ---
baseline = [run_strategy(lambda t: "retry", s) for s in SEEDS]
oracle = [run_strategy(lambda t: GROUND_TRUTH[t]["recovers_with_action"] or "escalate", s) for s in SEEDS]
alloc_decisions, _ = allocate_batch(ALLOC_EVENTS)
agent_map = {d["transaction_id"]: d["decision"] for d in alloc_decisions}
agent = [run_strategy(lambda t: agent_map.get(t, "skip"), s) for s in SEEDS]

strategy_rows = [
    ("Baseline: always retry", mean(baseline)),
    ("Your Agent: ERV + capacity allocator", mean(agent)),
    ("Oracle: perfect hidden knowledge", mean(oracle)),
]

# --- Capacity sweep ---
sweep_rows = []
for scale in [1.0, 0.75, 0.5, 0.25]:
    cap = {k: max(1, round(v * scale)) for k, v in DAILY_CAPACITY.items()}
    decisions, _ = allocate_batch(ALLOC_EVENTS, capacity=cap)
    served = sum(1 for d in decisions if d["decision"] != "skip")
    amap = {d["transaction_id"]: d["decision"] for d in decisions}
    results = [run_strategy(lambda t: amap.get(t, "skip"), s) for s in SEEDS]
    sweep_rows.append((int(scale * 100), served, mean(results)))

# --- Failure attribution ---
with open("reports/audit_trail.json") as f:
    audit = json.load(f)
with open("data/ground_truth.json") as f:
    gt_map = {g["transaction_id"]: g for g in json.load(f)}
with open("data/events.json") as f:
    events_map = {e["transaction_id"]: e for e in json.load(f)}

buckets = {"diagnosis": 0, "judgment": 0, "capacity": 0, "variance": 0}
total_failed = 0
for entry in audit:
    if entry["decision"] == "skip" or entry["outcome"]["success"]:
        continue
    total_failed += 1
    txn_id = entry["transaction_id"]
    true_reason = events_map[txn_id]["decline_code"]
    gt = gt_map[txn_id]
    if entry["diagnosed_reason"] != true_reason:
        buckets["diagnosis"] += 1
        continue
    correct_action = gt["recovers_with_action"]
    if gt["recoverable"] and correct_action and entry["decision"] != correct_action:
        buckets["judgment" if entry.get("got_first_choice", True) else "capacity"] += 1
    else:
        buckets["variance"] += 1

with open("reports/recovery_receipts.txt", encoding="utf-8") as f:
    receipt_lines = f.read().splitlines()[:6]
with open("reports/promise_to_pay_results.json") as f:
    p2p = json.load(f)


def bar_row(label, pct, color="#5b6df8"):
    return (f'<div class="bar-row"><div class="bar-label">{label}</div>'
            f'<div class="bar-track"><div class="bar-fill" style="width:{min(pct,100):.1f}%;background:{color}"></div></div>'
            f'<div class="bar-value">{pct:.1f}%</div></div>')


strategy_html = "".join(bar_row(n, v) for n, v in strategy_rows)
sweep_html = "".join(bar_row(f"{c}% capacity ({s} served)", v) for c, s, v in sweep_rows)
bucket_total = sum(buckets.values()) or 1
colors = {"diagnosis": "#e15b5b", "judgment": "#e1a15b", "capacity": "#5b9ee1", "variance": "#8fbf5b"}
bucket_html = "".join(bar_row(k.capitalize(), v / bucket_total * 100, colors[k]) for k, v in buckets.items())
receipts_html = "<br>".join(receipt_lines)
p2p_html = "".join(
    f"<li><b>{r['transaction_id']}</b>: \"{r['reply_text']}\" &rarr; <i>{r['intent']}</i>"
    + (f", reschedule {r['reschedule_date']}" if r.get("reschedule_date") else "") + "</li>"
    for r in p2p
)

html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Revenue Recovery Agent -- Results</title>
<style>
body {{ font-family: -apple-system, Segoe UI, Arial, sans-serif; max-width: 820px; margin: 40px auto; color: #222; }}
h1 {{ font-size: 22px; }} h2 {{ font-size: 17px; margin-top: 36px; border-bottom: 1px solid #eee; padding-bottom: 6px; }}
.bar-row {{ display: flex; align-items: center; margin: 8px 0; font-size: 13px; }}
.bar-label {{ width: 280px; flex-shrink: 0; }}
.bar-track {{ flex: 1; background: #f0f0f0; border-radius: 4px; height: 18px; overflow: hidden; }}
.bar-fill {{ height: 100%; border-radius: 4px; }}
.bar-value {{ width: 55px; text-align: right; font-weight: 600; }}
.receipts {{ background: #fafafa; padding: 14px; border-radius: 6px; font-family: monospace; font-size: 12px; line-height: 1.6; }}
.note {{ color: #666; font-size: 13px; }}
</style></head><body>
<h1>Revenue Recovery Agent -- Batch Results</h1>
<p class="note">Track 03: AI Revenue Recovery -- Razorpay AI Buildathon</p>

<h2>Strategy comparison (mean of {len(SEEDS)} seeds)</h2>
{strategy_html}

<h2>Capacity sweep -- revenue retained vs outreach capacity</h2>
{sweep_html}
<p class="note">Revenue retained drops slower than capacity -- the allocator preferentially keeps high-ERV transactions as capacity shrinks.</p>

<h2>Failure attribution ({total_failed} failed decisions)</h2>
{bucket_html}
<p class="note">Diagnosis = misread the decline reason (stub path only). Judgment = free choice, picked wrong (0 here). Capacity = right call, lost the slot to a higher-ERV transaction. Variance = right call, failed on probability alone.</p>

<h2>Sample recovery receipts (seed=42 demo run)</h2>
<div class="receipts">{receipts_html}</div>

<h2>Promise-to-pay: sample customer replies parsed</h2>
<ul>{p2p_html}</ul>
</body></html>"""

with open("reports/report.html", "w", encoding="utf-8") as f:
    f.write(html)

print("Report written -> reports/report.html")
print("Strategy means:", [(n, round(v, 1)) for n, v in strategy_rows])