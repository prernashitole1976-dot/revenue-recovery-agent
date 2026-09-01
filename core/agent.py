# core/agent.py
import json
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "simulator"))
from erv import compute_erv
from diagnosis_router import diagnose
from llm_diagnose import llm_diagnose_stub  # swap to llm_diagnose once your API key is set

ACTIONS = ["retry", "switch_method", "nudge", "escalate"]

with open("data/events.json") as f:
    EVENTS = json.load(f)


def decide(event):
    reason, method, confidence = diagnose(event, llm_diagnose_stub)

    scored = {
        action: compute_erv({**event, "decline_code": reason}, action)
        for action in ACTIONS
    }
    best_action = max(scored, key=scored.get)
    decision = best_action if scored[best_action] > 0 else "skip"

    return {
        "transaction_id": event["transaction_id"],
        "diagnosed_reason": reason,
        "diagnosis_method": method,
        "erv_scores": scored,
        "decision": decision,
    }


if __name__ == "__main__":
    decisions = [decide(e) for e in EVENTS]

    with open("reports/decisions.json", "w") as f:
        json.dump(decisions, f, indent=2)

    rule_n = sum(1 for d in decisions if d["diagnosis_method"] == "rule")
    llm_n = sum(1 for d in decisions if d["diagnosis_method"] == "llm")
    skip_n = sum(1 for d in decisions if d["decision"] == "skip")

    print(f"Made {len(decisions)} decisions -> reports/decisions.json")
    print(f"  Rule-based diagnosis: {rule_n}, LLM diagnosis: {llm_n}")
    print(f"  Skipped (ERV <= 0, not worth acting on): {skip_n}")