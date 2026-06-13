"""Generate a sample resume .docx using the DocxRenderer — no API call needed.

Run: python -m scripts.gen_sample_resume
Output: /tmp/sample_resume.docx
"""
# ruff: noqa: E501, RUF001 -- dev-only fixture: the long sample-data strings and
# the en dash glyph in the date range are intentional here.
from __future__ import annotations

from app.adapters.docx_resume import DocxRenderer
from app.domain.models import (
    AdditionalLine,
    ContactHeader,
    EducationEntry,
    ExperienceEntry,
    ResumeContent,
)

resume = ResumeContent(
    header=ContactHeader(
        name="Alfredo Gutierrez",
        location="Austin, TX",
        email="aseba.gutierrezm@gmail.com",
        phone="+1 631 431 8524",
        links=(
            "linkedin.com/in/asebagutierrezm",
            "github.com/CevittoG",
            "asebagutierrezm.com",
        ),
    ),
    experience=[
        ExperienceEntry(
            company="AidProf",
            title="AI Engineer",
            location="Remote",
            start="Oct 2024",
            end="Present",
            bullets=[
                "Architected a retrieval-augmented generation pipeline (FastAPI + ChromaDB + Claude) that reduced average tutor response time from 12 s to 1.4 s across 8,000 daily sessions.",
                "Designed and shipped a cosine-similarity reranker (threshold = 0.72) that cut irrelevant context injections by 41%, improving answer accuracy scores from 71% to 86% on the internal eval set.",
                "Led a team of 3 engineers to migrate the monolith to a ports-and-adapters architecture, enabling independent deployment of the LLM adapter and reducing integration-test cycle time by 60%.",
                "Implemented prompt-caching on the shared system + experience-docs prefix, reducing per-request Anthropic token cost by 87% on repeat queries within the 5-minute TTL window.",
            ],
        ),
        ExperienceEntry(
            company="Freelance",
            title="Senior Software Engineer",
            location="Remote",
            start="Mar 2022",
            end="Sep 2024",
            bullets=[
                "Delivered 6 end-to-end Python/FastAPI services for clients across e-commerce and edtech, each with full CI/CD on GitHub Actions and 90%+ unit-test coverage.",
                "Built a real-time inventory sync system (PostgreSQL + Redis + Celery) that processed 40,000 SKU updates per hour with < 200 ms end-to-end latency.",
                "Introduced mypy strict typing and ruff linting across a legacy 80 k-line Django codebase, eliminating a class of null-pointer bugs that had caused 3 production incidents in 6 months.",
            ],
        ),
        ExperienceEntry(
            company="MercadoLibre",
            title="Backend Engineer",
            location="Buenos Aires, Argentina",
            start="Aug 2019",
            end="Feb 2022",
            bullets=[
                "Owned the payments microservice (Java / Spring Boot) serving 2 M daily transactions; reduced p99 latency from 420 ms to 180 ms by introducing connection pooling and query plan caching.",
                "Co-designed the fraud-scoring API used by 14 internal teams; defined the REST contract, wrote the OpenAPI spec, and coordinated cross-team rollout across 3 time zones.",
                "Mentored 4 junior engineers; ran bi-weekly design reviews and pair-programming sessions that raised the team's PR approval-first-pass rate from 54% to 81%.",
            ],
        ),
    ],
    education=[
        EducationEntry(
            institution="Universidad de Buenos Aires",
            degree="B.Sc. Computer Science",
            location="Buenos Aires, Argentina",
            dates="Mar 2015 – Dec 2019",
            detail="Relevant coursework: Algorithms & Data Structures, Distributed Systems, Machine Learning.",
        ),
    ],
    additional=[
        AdditionalLine(
            label="Technical Skills",
            text="Python, FastAPI, PostgreSQL, Redis, Docker, Kubernetes, AWS (ECS/Lambda/S3), LLM APIs (Anthropic/OpenAI), RAG pipelines, mypy, ruff, pytest",
        ),
        AdditionalLine(
            label="Abilities",
            text="System design, API design, team leadership, cross-functional collaboration, technical mentoring",
        ),
        AdditionalLine(
            label="Languages",
            text="Spanish (native), English (professional)",
        ),
        AdditionalLine(
            label="Work Authorization",
            text="Argentine citizen; eligible to work remotely for international employers",
        ),
    ],
)

renderer = DocxRenderer()
docx_bytes = renderer.render_resume_docx(resume)

out = "/tmp/sample_resume.docx"
with open(out, "wb") as f:
    f.write(docx_bytes)

print(f"Written {len(docx_bytes):,} bytes → {out}")
