import json, os, sys
from datetime import datetime

sys.path.append(os.path.dirname(__file__))
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "data"))
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "simulator"))

from erv import compute_erv
from diagnosis_router import diagnose
from llm_diagnose import get_diagnose_fn
from constraints import DAILY_CAPACITY, passes_compliance
from generate_events import RAZORPAY_ERROR_MAPPING
from outcome_simulator import simulate_outcome

REASON_TO_KEY = {v["reason"]: k for k, v in RAZORPAY_ERROR_MAPPING.items()}
ACTIONS = ["retry", "switch_method", "nudge", "escalate"]
AUDIT_LOG_PATH = "reports/webhook_audit_log.jsonl"

try:
    with open("data/ground_truth.json") as f:
        KNOWN_GROUND_TRUTH = {g["transaction_id"]: g for g in json.load(f)}
except FileNotFoundError:
    KNOWN_GROUND_TRUTH = {}


def process_payment_failed(payment_entity, customer_tenure_months=6,
                            transaction_id_override=None, remaining_capacity=None):
    """
    Core decision logic for one incoming payment.failed event, shaped like a
    real Razorpay webhook payload (amount in paise; error_code/description/
    source/step/reason live directly on the payment entity). Framework-
    agnostic on purpose -- the FastAPI layer is a thin wrapper around this,
    so the decision logic is testable without a running server.
    """
    if remaining_capacity is None:
        remaining_capacity = dict(DAILY_CAPACITY)

    error_reason = payment_entity["error_reason"]
    decline_code = REASON_TO_KEY.get(error_reason)
    if decline_code is None:
        return {"error": f"Unrecognized error_reason '{error_reason}'"}, remaining_capacity

    txn_id = transaction_id_override or payment_entity["id"]

    event = {
        "transaction_id": txn_id,
        "amount": payment_entity["amount"] / 100,  # paise -> rupees, like real Razorpay amounts
        "currency": payment_entity.get("currency", "INR"),
        "payment_method": payment_entity.get("method", "card"),
        "decline_code": decline_code,
        "gateway_error": {
            "code": payment_entity["error_code"],
            "description": payment_entity["error_description"],
            "source": payment_entity["error_source"],
            "step": payment_entity["error_step"],
            "reason": payment_entity["error_reason"],
            "metadata": {"payment_id": payment_entity["id"], "order_id": payment_entity.get("order_id")},
        },
        "attempt_number": 1,
        "customer_tenure_months": customer_tenure_months,
    }

    diagnose_fn = get_diagnose_fn()
    diagnosed_reason, method, confidence = diagnose(event, diagnose_fn)

    scored = {}
    for action in ACTIONS:
        ok, block_reason = passes_compliance(event, diagnosed_reason, action)
        if not ok:
            scored[action] = {"erv": None, "blocked_reason": block_reason}
            continue
        erv = compute_erv({**event, "decline_code": diagnosed_reason}, action)
        scored[action] = {"erv": erv, "blocked_reason": None}

    legal_actions = {a: s["erv"] for a, s in scored.items() if s["erv"] is not None and s["erv"] > 0}

    decision = "skip"
    capacity_note = None
    if legal_actions:
        ranked = sorted(legal_actions, key=legal_actions.get, reverse=True)
        assigned = False
        for candidate in ranked:
            if remaining_capacity.get(candidate, 0) > 0:
                decision = candidate
                remaining_capacity[candidate] -= 1
                assigned = True
                break
            elif capacity_note is None:
                capacity_note = f"'{candidate}' had the best ERV but no capacity remained today"
        if not assigned:
            decision = "skip"

    response = {
        "transaction_id": txn_id,
        "diagnosed_reason": diagnosed_reason,
        "diagnosis_method": method,
        "erv_scores": scored,
        "decision": decision,
        "capacity_note": capacity_note,
        "remaining_capacity_today": dict(remaining_capacity),
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }

    if txn_id in KNOWN_GROUND_TRUTH and decision not in ("skip", "escalate"):
        result = simulate_outcome(txn_id, decision, attempt_number=1)
        response["simulated_outcome"] = result
        response["outcome_note"] = "Demo-only: ground truth exists for this pre-generated transaction_id."
    else:
        response["simulated_outcome"] = None
        response["outcome_note"] = (
            "No ground truth available for this transaction -- in production, "
            "the real outcome would be confirmed by the next gateway callback."
        )

    os.makedirs("reports", exist_ok=True)
    with open(AUDIT_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(response) + "\n")

    return response, remaining_capacity