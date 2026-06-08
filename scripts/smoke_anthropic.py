"""Smoke test: one real Claude call returns parseable GeneratedContent.

Run:
    python -m scripts.smoke_anthropic

Sends a tiny experience blob + tiny JD through AnthropicAdapter.generate(),
asserts the result parses into the GeneratedContent contract (company / role
populated), and prints the audit dict so the JSON shape can be eyeballed.

This is intentionally a one-shot — no container, no Drive write, no Sheet
append. Phase 3 chains the full pipeline.
"""
from __future__ import annotations

from dataclasses import asdict

from app.adapters.anthropic_llm import AnthropicAdapter
from app.config import get_settings
from app.domain.models import JobDescription

EXPERIENCE_DOCS = """# === career.md ===
Pat Example — staff backend engineer.
- 7y Python (FastAPI, asyncio); 4y Go (gRPC, Kafka consumers).
- Led migration of an event pipeline from Kinesis to MSK; mentored 4 engineers.
- Production Kubernetes (EKS), Terraform, Datadog.
"""

JD_TEXT = """Acme Corp — Senior Backend Engineer (remote).
We need a senior engineer to own our streaming ingestion (Kafka, Python).
Bonus: Rust experience, comfort with Kubernetes, mentoring juniors.
Compensation: competitive. Location: remote (US)."""


def main() -> None:
    s = get_settings()
    adapter = AnthropicAdapter(
        api_key=s.anthropic_api_key,
        model=s.anthropic_model,
        max_tokens=s.anthropic_max_tokens,
    )
    result = adapter.generate(
        experience_docs=EXPERIENCE_DOCS,
        jd=JobDescription(text=JD_TEXT),
    )
    audit = result.audit
    assert audit.company, "audit.company is empty"
    assert audit.role, "audit.role is empty"
    print(f"Parsed OK. company={audit.company!r}, role={audit.role!r}, "
          f"fit_score={audit.fit_score}")
    print("\nAudit dict:")
    print(asdict(audit))


if __name__ == "__main__":
    main()
