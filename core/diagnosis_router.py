# core/diagnosis_router.py

CANONICAL_MESSAGES = {
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


def diagnose(event, llm_diagnose_fn):
    """
    Returns (decline_reason, method, confidence).
    method is 'rule' when the structured code and free-text message agree
    (fast, free, fully explainable). method is 'llm' when they disagree --
    a real-world signal that the structured code may not be trustworthy,
    so we defer to the LLM to read the raw message instead.
    """
    expected_message = CANONICAL_MESSAGES.get(event["decline_code"])
    if event["gateway_message"] == expected_message:
        return event["decline_code"], "rule", 1.0

    reason = llm_diagnose_fn(event["gateway_message"])
    return reason, "llm", 0.7