# Revenue Recovery Agent — Razorpay AI Buildathon (Track 03)

## Problem
When a customer's recurring subscription charge fails, the merchant loses
recurring revenue silently — most failures get one blind retry at best,
with no diagnosis of why it failed and no tailored response. This agent
detects a failed subscription charge, diagnoses the decline reason, chooses
one of four bounded actions (retry, switch payment method, nudge the
customer, or escalate to a human queue), and reports the rupee value of
failed charges recovered across a batch, with a full audit trail.

## What this does NOT do
Checkout abandonment recovery, B2B receivables, voice-based recovery,
mandate sequencing — out of scope for this build.

## Architecture
- data/generate_events.py -- synthetic dataset generator; errors shaped
  like Razorpay's real payload (code/description/source/step/reason)
- core/erv.py -- Expected Recovery Value scoring per (transaction, action)
- core/diagnosis_router.py -- routes to rule-based or LLM diagnosis
  depending on whether the structured code matches the raw error
- core/llm_diagnose.py -- offline stub + real Claude API diagnosis,
  auto-selected based on whether ANTHROPIC_API_KEY is set
- core/constraints.py -- compliance guardrails and daily capacity
- core/allocator.py -- budget-constrained batch allocation (greedy,
  highest-ERV-first)
- core/workflow.py -- multi-day retry sequencing with cooldowns and
  attempt caps
- core/self_critique.py -- four-bucket failure attribution (diagnosis /
  judgment / capacity / expected variance)
- core/evaluate_diagnosis.py -- measures diagnosis text-reading accuracy
  on ambiguous cases
- api/webhook_server.py + core/webhook_logic.py -- live FastAPI endpoint
  simulating a real Razorpay payment.failed webhook
- reports/generate_report.py -- unified HTML results report

## How to run
python data\generate_events.py
python core\allocator.py
python core\workflow.py
python core\receipts.py
python core\self_critique.py
python reports\generate_report.py

Open reports\report.html for the full results dashboard.

For the live webhook demo:
python -m uvicorn api.webhook_server:app --port 8000
Then visit http://127.0.0.1:8000/docs

## Results (mean of 200 seeds)
Baseline (always retry):            38.9% recovered
Our Agent (ERV + capacity allocator): 44.9% recovered
Oracle (perfect hidden knowledge):   47.4% recovered

Multi-day retry workflow (10-day horizon): 57-68% recovered depending on
dataset, since failed transactions get multiple attempts over time instead
of one shot. 0% judgment errors in self-critique across every dataset
version tested -- whenever the agent had a free choice, it chose correctly.

## Known limitations
- Diagnosis on ambiguous cases (~8% of the batch) uses Claude Haiku when
  ANTHROPIC_API_KEY is configured, falling back to an offline keyword
  matcher otherwise. Measured text-reading accuracy: 4/4 on this dataset
  (see core/evaluate_diagnosis.py) -- this measures whether the raw error
  text was read correctly, which is different from whether it matched the
  transaction's original structured code (see next point).
- The self-critique "diagnosis error" bucket reflects cases where a
  corrupted structured field caused a correct read of a genuinely
  different failure category than the transaction's true one -- not a
  text-reading mistake.
- Success probabilities are synthetic, calibrated by hand to reflect
  plausible real-world recovery rates -- not derived from real Razorpay
  data.
- Capacity limits (retry/nudge/escalate daily quotas) are illustrative,
  not sourced from real rate limits.
- The webhook's daily capacity counter is in-memory and resets on server
  restart -- a real deployment would back this with persistent storage.
- Our first capacity-sweep run (10 seeds) showed a non-monotonic result;
  increasing to 200 seeds confirmed the expected monotonic trend, since a
  single high-value transaction flipping outcome could swing the aggregate
  by roughly 4 percentage points at low seed counts.
