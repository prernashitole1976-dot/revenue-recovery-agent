# core/erv.py
#
# This is the agent's own domain knowledge -- reasonable assumptions about
# how likely each action is to succeed for each decline reason. It is NOT
# the same as data/ground_truth.json, which the agent never reads. The gap
# between this table's guesses and the real ground truth is what makes the
# agent's performance meaningfully different from (and a bit worse than)
# the oracle -- which is realistic and fine to show in your metrics.

BASE_SUCCESS_PROBS = {
    ("insufficient_funds", "retry"): 0.55,
    ("insufficient_funds", "nudge"): 0.25,
    ("insufficient_funds", "switch_method"): 0.10,
    ("technical_timeout", "retry"): 0.70,
    ("technical_timeout", "switch_method"): 0.40,
    ("expired_card", "nudge"): 0.40,
    ("expired_card", "switch_method"): 0.30,
    ("expired_card", "retry"): 0.02,
    ("bank_declined_generic", "retry"): 0.30,
    ("bank_declined_generic", "switch_method"): 0.25,
    ("do_not_honor", "retry"): 0.05,
    ("invalid_cvv", "nudge"): 0.35,
    ("invalid_cvv", "retry"): 0.05,
    ("exceeds_withdrawal_limit", "retry"): 0.45,
    ("otp_abandoned", "nudge"): 0.55,
    ("risk_flagged_by_bank", "escalate"): 0.20,
    ("mandate_not_approved", "nudge"): 0.35,
    ("card_blocked", "escalate"): 0.10,
}

ACTION_COSTS = {"retry": 1.0, "switch_method": 2.0, "nudge": 0.5, "escalate": 5.0}


def estimate_success_probability(decline_reason, action, customer_tenure_months):
    base = BASE_SUCCESS_PROBS.get((decline_reason, action), 0.05)
    loyalty_boost = min(1.3, 1.0 + customer_tenure_months / 60)
    return min(0.95, base * loyalty_boost)


def compute_erv(event, action):
    """Expected Recovery Value = (amount x P(success)) - cost of taking the action."""
    p = estimate_success_probability(
        event["decline_code"], action, event["customer_tenure_months"]
    )
    cost = ACTION_COSTS[action]
    return round(event["amount"] * p - cost, 2)