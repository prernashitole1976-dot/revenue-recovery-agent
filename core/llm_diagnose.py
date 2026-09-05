import os

DECLINE_REASONS = [
    "insufficient_funds", "expired_card", "invalid_cvv", "bank_declined_generic",
    "do_not_honor", "exceeds_withdrawal_limit", "technical_timeout",
    "otp_abandoned", "risk_flagged_by_bank", "mandate_not_approved", "card_blocked",
]


def llm_diagnose_stub(raw_description: str) -> str:
    """Keyword fallback -- works with zero setup, useful while building/testing."""
    msg = raw_description.lower()
    checks = [
        ("insufficient", "insufficient_funds"), ("expired", "expired_card"),
        ("cvv", "invalid_cvv"), ("timed out", "technical_timeout"),
        ("timeout", "technical_timeout"),
        ("honour", "do_not_honor"), ("honor", "do_not_honor"),  # card-network spelling varies
        ("blocked", "card_blocked"), ("otp", "otp_abandoned"),
        ("mandate", "mandate_not_approved"), ("risk", "risk_flagged_by_bank"),
        ("flagged", "risk_flagged_by_bank"), ("limit", "exceeds_withdrawal_limit"),
    ]
    for keyword, reason in checks:
        if keyword in msg:
            return reason
    return "bank_declined_generic"


def llm_diagnose(raw_description: str) -> str:
    """Real LLM call -- requires `pip install anthropic` and ANTHROPIC_API_KEY set."""
    from anthropic import Anthropic

    client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    prompt = (
        "You are a payments diagnosis assistant. Classify this Razorpay gateway "
        f"error description into exactly one of: {', '.join(DECLINE_REASONS)}.\n\n"
        f'Error description: "{raw_description}"\n\n'
        "Respond with ONLY the matching decline reason, nothing else."
    )
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=20,
        messages=[{"role": "user", "content": prompt}],
    )
    reason = response.content[0].text.strip()
    return reason if reason in DECLINE_REASONS else "bank_declined_generic"


def get_diagnose_fn():
    """Use the real LLM if a key is configured, otherwise fall back to the
    offline stub -- so the project runs with zero setup for anyone grading it."""
    if os.environ.get("ANTHROPIC_API_KEY"):
        return llm_diagnose
    return llm_diagnose_stub