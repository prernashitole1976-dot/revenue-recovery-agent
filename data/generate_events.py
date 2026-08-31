import json
import random
from datetime import datetime, timedelta
from faker import Faker

fake = Faker("en_IN")
random.seed(42)  # keep results reproducible for your demo

N_EVENTS = 100

# (decline_code, relative frequency weight)
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

GATEWAY_MESSAGES = {
    "insufficient_funds": "Your card has insufficient funds",
    "technical_timeout": "Gateway request timed out, please retry",
    "expired_card": "Your card has expired",
    "bank_declined_generic": "Transaction declined by issuing bank",
    "do_not_honor": "Do not honor - contact your bank",
    "invalid_cvv": "Invalid CVV entered",
    "exceeds_withdrawal_limit": "Transaction exceeds withdrawal limit",
    "otp_abandoned": "OTP verification not completed",
    "risk_flagged_by_bank": "Transaction flagged for risk review",
    "mandate_not_approved": "UPI mandate not approved by customer",
    "card_blocked": "Card has been blocked",
}

# decline_code -> (recoverable, best_action, base_success_probability)
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

def weighted_choice(pairs):
    reasons, weights = zip(*pairs)
    return random.choices(reasons, weights=weights, k=1)[0]

events, ground_truth = [], []
start_date = datetime(2026, 7, 1)

for i in range(1, N_EVENTS + 1):
    txn_id = f"txn_{i:05d}"
    decline_code = weighted_choice(DECLINE_REASONS)
    tenure = random.randint(1, 36)

    gateway_message = GATEWAY_MESSAGES[decline_code]
    # inject messy/ambiguous rows ~8% of the time -- real gateway data is noisy,
    # and these become your Day 4 "exceptions we couldn't cleanly resolve" cases
    is_messy = random.random() < 0.08
    if is_messy:
        other = random.choice([r for r in GATEWAY_MESSAGES if r != decline_code])
        gateway_message = GATEWAY_MESSAGES[other]

    events.append({
        "transaction_id": txn_id,
        "subscription_id": f"sub_{1000 + i}",
        "customer_id": f"cust_{2000 + i}",
        "amount": random.choice(AMOUNTS),
        "currency": "INR",
        "payment_method": random.choice(PAYMENT_METHODS),
        "decline_code": decline_code,
        "gateway_message": gateway_message,
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

with open("data/events.json", "w") as f:
    json.dump(events, f, indent=2)
with open("data/ground_truth.json", "w") as f:
    json.dump(ground_truth, f, indent=2)

print(f"Generated {N_EVENTS} events -> data/events.json")
print(f"Generated {N_EVENTS} ground truth rows -> data/ground_truth.json")