# core/llm_diagnose.py
import os

DECLINE_REASONS = [
    "insufficient_funds", "expired_card", "invalid_cvv", "bank_declined_generic",
    "do_not_honor", "exceeds_withdrawal_limit", "technical_timeout",
    "otp_abandoned", "risk_flagged_by_bank", "mandate_not_approved", "card_blocked",
]


def llm_diagnose_stub(raw_gateway_message: str) -> str:
    """Keyword fallback -- works with zero setup, useful while building/testing."""
    msg = raw_gateway_message.lower()
    checks = [
        ("insufficient", "insufficient_funds"), ("expired", "expired_card"),
        ("cvv", "invalid_cvv"), ("timed out", "technical_timeout"),
        ("timeout", "technical_timeout"), ("do not honor", "do_not_honor"),
        ("blocked", "card_blocked"), ("otp", "otp_abandoned"),
        ("mandate", "mandate_not_approved"), ("risk", "risk_flagged_by_bank"),
        ("flagged", "risk_flagged_by_bank"), ("limit", "exceeds_withdrawal_limit"),
    ]
    for keyword, reason in checks:
        if keyword in msg:
            return reason
    return "bank_declined_generic"


def llm_diagnose(raw_gateway_message: str) -> str:
    """Real LLM call -- requires `pip install anthropic` and ANTHROPIC_API_KEY set."""
    from anthropic import Anthropic

    client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    prompt = (
        "You are a payments diagnosis assistant. Classify this gateway message "
        f"into exactly one of: {', '.join(DECLINE_REASONS)}.\n\n"
        f'Gateway message: "{raw_gateway_message}"\n\n'
        "Respond with ONLY the matching decline reason, nothing else."
    )
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",  # fast + cheap, right-sized for a classification call
        max_tokens=20,
        messages=[{"role": "user", "content": prompt}],
    )
    reason = response.content[0].text.strip()
    return reason if reason in DECLINE_REASONS else "bank_declined_generic"