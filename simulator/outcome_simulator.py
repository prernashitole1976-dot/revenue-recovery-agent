import json
import random

with open("data/ground_truth.json") as f:
    GROUND_TRUTH = {row["transaction_id"]: row for row in json.load(f)}

with open("data/events.json") as f:
    EVENTS = {row["transaction_id"]: row for row in json.load(f)}

ACTIONS = ["retry", "switch_method", "nudge", "escalate"]


def simulate_outcome(transaction_id, action, attempt_number=1, rng=None):
    """
    Simulate whether a recovery action succeeds for a given transaction.

    Returns:
        success (bool)
        amount_recovered (float) -- 0 if not successful
        note (str) -- short explanation, feeds the audit trail later
    """
    rng = rng or random
    gt = GROUND_TRUTH[transaction_id]
    event = EVENTS[transaction_id]

    if action == "escalate":
        # Escalation hands off to a human -- it's a deliberate stop, not an
        # auto-recovery. Scored separately, not counted as agent-recovered revenue.
        return {
            "success": False,
            "amount_recovered": 0.0,
            "note": "Escalated to human queue -- not counted as auto-recovered",
        }

    if not gt["recoverable"]:
        return {
            "success": False,
            "amount_recovered": 0.0,
            "note": f"Not recoverable regardless of action ({event['decline_code']})",
        }

    correct_action = gt["recovers_with_action"]
    base_prob = gt["base_success_probability"]

    if action == correct_action:
        prob = base_prob
    else:
        # wrong action for this decline reason -- meaningfully worse odds.
        # this is what rewards good diagnosis over blind retrying
        prob = base_prob * 0.35

    # diminishing returns on repeated attempts against the same transaction
    prob = prob * (0.7 ** (attempt_number - 1))
    prob = max(0.0, min(prob, 0.95))

    success = rng.random() < prob
    return {
        "success": success,
        "amount_recovered": event["amount"] if success else 0.0,
        "note": (
            f"Action '{action}' vs correct '{correct_action}', "
            f"attempt {attempt_number}, p={prob:.2f} -> "
            f"{'recovered' if success else 'not recovered'}"
        ),
    }