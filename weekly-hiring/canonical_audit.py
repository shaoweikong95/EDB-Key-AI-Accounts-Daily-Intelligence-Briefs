"""Canonical job audit and fail-safe validation for weekly hiring reports.

No network calls or spreadsheet writes occur in this module.
"""
from __future__ import annotations
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Iterable

CATEGORIES = ("Research","Engineering","Applied AI","Product","Sales","GTM","Marketing","Corporate","Policy")
ACCOUNTS = ("OpenAI","Databricks","AvePoint","Wonderful AI","Openmind Research Institute","Bottlecap AI","Zhipu AI (Z.ai)","Decart","SandboxAQ","Casual Labs","Sakana AI","Snowflake","MSRA (Microsoft Research Asia)","Workato","ServiceNow","Cohere","BeyondMath","StepFun","Mistral AI","SpaceX","Deepgram","Preferred Networks","Enigma","AI21 Labs","MiniMax","Moonshot AI (Kimi)","Periodic AI","Google DeepMind","Catina AI","Luma AI","Thinking Machines Lab","Safe Superintelligence (SSI)","NVIDIA","Anthropic (Claude)","ElevenLabs","AMI Labs (Advanced Machine Intelligence)","Prometheus","Manus AI","Datadog","Cognition AI (Devin, Windsurf)")

@dataclass(frozen=True)
class Posting:
    account: str
    entity: str
    job_id: str
    canonical_url: str
    title: str
    category: str
    countries: tuple[str, ...]
    source_board_url: str

def validate(postings: Iterable[Posting], coverage: dict[str,str], failures: dict[str,str]):
    rows = list(postings)
    if len(ACCOUNTS) != 40 or set(coverage) != set(ACCOUNTS):
        raise ValueError("Exactly 40 accounts and coverage records required")
    if any(s not in {"Complete","Partial","Unverified"} for s in coverage.values()):
        raise ValueError("Invalid coverage status")
    if sum(coverage[a]=="Unverified" and a in failures for a in ACCOUNTS)>10:
        raise ValueError("Fail-safe: more than 25% transient extraction failures")
    seen=set()
    for p in rows:
        if p.account not in ACCOUNTS or p.category not in CATEGORIES or not p.job_id or not p.canonical_url or not p.source_board_url:
            raise ValueError(f"Invalid canonical posting: {p}")
        key=(p.account,p.entity,p.job_id)
        if key in seen: raise ValueError(f"Duplicate posting: {key}")
        seen.add(key)
        if not p.countries: raise ValueError(f"Missing explicit location: {key}")
        if coverage[p.account]=="Unverified":
            raise ValueError(f"Unverified account included in verified audit: {p.account}")
    sg=Counter((p.account,p.category) for p in rows if "Singapore" in p.countries)
    per_account={a:{c:sg[(a,c)] for c in CATEGORIES} for a in ACCOUNTS if coverage[a]!="Unverified"}
    for a in per_account:
        if sum(per_account[a].values())!=len({(p.entity,p.job_id) for p in rows if p.account==a and "Singapore" in p.countries}):
            raise ValueError(f"Singapore account reconciliation failed: {a}")
    # A Partial row must have a reliable enumerated SG board, including explicit zero.
    # Callers must supply sg_verified_accounts only after an exhaustive SG board scan.
    matrix=Counter((country,p.category) for p in rows for country in set(p.countries))
    sg_total=sum(sum(v.values()) for v in per_account.values())
    if sg_total!=sum(matrix[("Singapore",c)] for c in CATEGORIES):
        raise ValueError("Singapore country matrix reconciliation failed")
    return {"singapore_by_account":per_account,"singapore_total":sg_total,
            "country_matrix":{country:{cat:matrix[(country,cat)] for cat in CATEGORIES}
                              for country in sorted({k[0] for k in matrix})},
            "posting_audit":rows}

def gate(postings, coverage, failures, sg_verified_accounts):
    if any(coverage[a]=="Partial" and a not in sg_verified_accounts for a in ACCOUNTS):
        raise ValueError("Blank or unverified Singapore counts in Partial account")
    if any(coverage[a]=="Complete" and a not in sg_verified_accounts for a in ACCOUNTS):
        raise ValueError("Complete account not Singapore verified")
    if any(coverage[a]=="Unverified" and a not in failures for a in ACCOUNTS):
        raise ValueError("Unverified account lacks documented retry/failure reason")
    return validate(postings,coverage,failures)
