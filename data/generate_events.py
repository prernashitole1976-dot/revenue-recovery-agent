import json
import random
import string
from datetime import datetime, timedelta
from faker import Faker

fake = Faker("en_IN")
random.seed(42)

N_EVENTS = 100

DECLINE_REASONS = [
    ("insufficient_funds", 0.28),
    ("technical_timeout", 0.15),
    ("expired_card", 0.15),
    ("bank_declined_generic", 0.12),
    ("do_not_honor", 0.08),
    ("invalid_cvv", 0.05),
    ("exceeds_withdrawal_limit", 0.05),
    ("otp_abandoned", 0.04),
    ("risk_flagged_by_bank", 0.03),
    ("mandate_not_approved", 0.03),
    ("card_blocked", 0.02),
]

PAYMENT_METHODS = ["card", "upi", "netbanking", "wallet", "upi_autopay"]
AMOUNTS = [199, 299, 499, 999, 1499, 2999, 4999, 9999]

# Modeled on Razorpay's real payment error schema: errors return as
# {code, description, source, step, reason, metadata}, split between
# BAD_REQUEST_ERROR (customer/business at fault) and GATEWAY_ERROR
# (bank/gateway/network at fault). source tells you literally who needs
# to act next -- this maps almost directly onto our action-selection logic.
RAZORPAY_ERROR_MAPPING = {
    "insufficient_funds": {
        "code": "BAD_REQUEST_ERROR",
        "description": "Payment failed due to insufficient funds in the customer's account",
        "source": "customer",
        "step": "payment_authorization",
        "reason": "insufficient_funds",
    },
    "expired_card": {
        "code": "BAD_REQUEST_ERROR",
        "description": "The card used for this payment has expired",
        "source": "customer",
        "step": "payment_authentication",
        "reason": "expired_card",
    },
    "invalid_cvv": {
        "code": "BAD_REQUEST_ERROR",
        "description": "The CVV entered for the card is incorrect",
        "source": "customer",
        "step": "payment_authentication",
        "reason": "incorrect_cvv",
    },
    "bank_declined_generic": {
        "code": "GATEWAY_ERROR",
        "description": "The payment was declined by the customer's issuing bank",
        "source": "bank",
        "step": "payment_authorization",
        "reason": "payment_declined",
    },
    "do_not_honor": {
        "code": "GATEWAY_ERROR",
        "description": "The issuing bank declined the transaction with a do-not-honour response",
        "source": "bank",
        "step": "payment_authorization",
        "reason": "do_not_honour",
    },
    "exceeds_withdrawal_limit": {
        "code": "BAD_REQUEST_ERROR",
        "description": "The transaction exceeds the customer's daily transaction limit",
        "source": "customer",
        "step": "payment_authorization",
        "reason": "exceeds_withdrawal_limit",
    },
    "technical_timeout": {
        "code": "GATEWAY_ERROR",
        "description": "The payment request timed out before the gateway could process it",
        "source": "gateway",
        "step": "payment_authorization",
        "reason": "gateway_timeout",
    },
    "otp_abandoned": {
        "code": "BAD_REQUEST_ERROR",
        "description": "The customer cancelled the payment before completing OTP verification",
        "source": "customer",
        "step": "payment_authentication",
        "reason": "payment_cancelled",
    },
    "risk_flagged_by_bank": {
        "code": "GATEWAY_ERROR",
        "description": "The transaction was flagged during the issuing bank's risk review",
        "source": "bank",
        "step": "payment_authorization",
        "reason": "risk_check_failed",
    },
    "mandate_not_approved": {
        "code": "BAD_REQUEST_ERROR",
        "description": "The customer did not approve the UPI Autopay mandate request",
        "source": "customer",
        "step": "payment_authentication",
        "reason": "mandate_rejected",
    },
    "card_blocked": {
        "code": "GATEWAY_ERROR",
        "description": "The card has been blocked by the issuing bank",
        "source": "bank",
        "step": "payment_authorization",
        "reason": "card_blocked",
    },
}

GROUND_TRUTH_RULES = {
    "insufficient_funds":       (True,  "retry",    0.60),
    "technical_timeout":        (True,  "retry",    0.75),
    "expired_card":             (True,  "nudge",    0.45),
    "bank_declined_generic":    (True,  "retry",    0.35),
    "do_not_honor":             (False, "escalate", 0.10),
    "invalid_cvv":              (True,  "nudge",    0.30),
    "exceeds_withdrawal_limit": (True,  "retry",    0.50),
    "otp_abandoned":            (True,  "nudge",    0.60),
    "risk_flagged_by_bank":     (False, "escalate", 0.15),
    "mandate_not_approved":     (True,  "nudge",    0.40),
    "card_blocked":             (False, "escalate", 0.05),
}

ID_CHARS = string.ascii_letters + string.digits

def gen_id(length=14):
    return "".join(random.choice(ID_CHARS) for _ in range(length))

def weighted_choice(pairs):
    reasons, weights = zip(*pairs)
    return random.choices(reasons, weights=weights, k=1)[0]


# Everything below only runs when this file is executed directly -- NOT when
# another module imports RAZORPAY_ERROR_MAPPING from it. Without this guard,
# every script that imports the mapping (the diagnosis router, and later the
# webhook handler) would silently regenerate and overwrite your dataset on
# every single call.
if __name__ == "__main__":
    events, ground_truth = [], []
    start_date = datetime(2026, 7, 1)

    for i in range(1, N_EVENTS + 1):
        txn_id = f"txn_{i:05d}"
        decline_code = weighted_choice(DECLINE_REASONS)
        tenure = random.randint(1, 36)

        is_messy = random.random() < 0.08
        if is_messy:
            other_key = random.choice([r for r in RAZORPAY_ERROR_MAPPING if r != decline_code])
            gateway_error = dict(RAZORPAY_ERROR_MAPPING[other_key])
        else:
            gateway_error = dict(RAZORPAY_ERROR_MAPPING[decline_code])

        gateway_error["metadata"] = {
            "payment_id": f"pay_{gen_id()}",
            "order_id": f"order_{gen_id()}",
        }

        events.append({
            "transaction_id": txn_id,
            "subscription_id": f"sub_{1000 + i}",
            "customer_id": f"cust_{2000 + i}",
            "amount": random.choice(AMOUNTS),
            "currency": "INR",
            "payment_method": random.choice(PAYMENT_METHODS),
            "decline_code": decline_code,
            "gateway_error": gateway_error,
            "attempt_number": 1,
            "timestamp": (start_date + timedelta(days=random.randint(0, 55))).isoformat() + "Z",
            "customer_tenure_months": tenure,
            "prior_successful_payments": max(0, tenure - random.randint(0, 3)),
            "prior_failed_payments": random.randint(0, 3),
            "customer_email": fake.email(),
            "customer_phone": fake.msisdn()[:10],
        })

        recoverable, best_action, base_prob = GROUND_TRUTH_RULES[decline_code]
        ground_truth.append({
            "transaction_id": txn_id,
            "recoverable": recoverable,
            "recovers_with_action": best_action if recoverable else None,
            "base_success_probability": base_prob if recoverable else 0.0,
            "is_messy_case": is_messy,
        })

    with open("data/events.json", "w", encoding="utf-8") as f:
        json.dump(events, f, indent=2)
    with open("data/ground_truth.json", "w", encoding="utf-8") as f:
        json.dump(ground_truth, f, indent=2)

    print(f"Generated {N_EVENTS} events (Razorpay-shaped errors) -> data/events.json")
    print(f"Generated {N_EVENTS} ground truth rows -> data/ground_truth.json")