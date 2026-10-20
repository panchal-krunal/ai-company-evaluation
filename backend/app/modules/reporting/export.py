"""Export an evaluation as Markdown (for reading/sharing) or JSON (for systems)."""

from typing import Any

from app.models import Company, Evaluation

MODULE_TITLES = {
    "management_outlook": "Management Outlook",
    "products_segments": "Products & Segments",
    "industry_outlook": "Industry Outlook",
    "competitors": "Competitors",
    "debt_structure": "Debt Structure",
    "related_party_transactions": "Related Party Transactions",
    "financial_warnings": "Financial Warning Checks",
    "growth_analysis": "Growth Analysis",
    "company_risks": "Company Risks",
    "why_not_invest": "Why Not Invest",
}


def _fmt(value: Any, kind: str = "") -> str:
    if value is None:
        return "—"
    if kind == "pct":
        return f"{value * 100:.1f}%"
    if kind == "cr":
        return f"₹{value:,.1f} Cr"
    if isinstance(value, float):
        return f"{value:,.2f}"
    return str(value)


def to_markdown(evaluation: Evaluation, company: Company) -> str:
    out = [
        f"# Evaluation: {company.name}",
        "",
        f"- NSE: {company.nse_symbol or '—'} · BSE: {company.bse_code or '—'} · ISIN: {company.isin or '—'}",
        f"- Status: **{evaluation.status}**"
        + (f" (approved by {evaluation.approved_by})" if evaluation.approved_by else ""),
        f"- Created: {evaluation.created_at:%d %b %Y %H:%M} UTC · formula v{evaluation.formula_version} · prompts v{evaluation.prompt_version}",
        "",
    ]
    findings = {f.module: f for f in evaluation.findings}
    for module, title in MODULE_TITLES.items():
        f = findings.get(module)
        out += [f"## {title}", ""]
        if f is None or f.status in ("not_run", "queued", "running"):
            out += [
                f"_Not produced ({f.status if f else 'missing'}){': ' + f.error if f and f.error else ''}._",
                "",
            ]
            continue
        if f.override_summary:
            out += [f"**Analyst override:** {f.override_summary}", f"_Reason: {f.override_reason}_", ""]
        out += [f.summary, ""]
        data = f.data
        for r in data.get("results", []):
            out.append(f"- **{r['check']}**: {r['status']} ({_fmt(r['value'])}). {r['explanation']}")
        for c in data.get("claims", []):
            mark = "" if c.get("supported") else " _(unsupported)_"
            refs = "; ".join(
                f"{e['document_title']} p.{e['page_number']}"
                for e in c.get("evidence", [])
                if e.get("verified")
            )
            out.append(f"- {c['statement']}{mark}" + (f" [{refs}]" if refs else ""))
        for m in data.get("metrics", []):
            kind = (
                "cr"
                if m["key"] == "revenue"
                else ("" if m["key"] in ("debt_to_equity", "ocf_to_profit") else "pct")
            )
            out.append(
                f"- {m['label']}: {_fmt(m['subject'], kind)} vs peer median {_fmt(m['peer_median'], kind)}"
            )
        for flag in data.get("rule_based_flags", []):
            out.append(f"- [{flag['severity']}] **{flag['title']}**: {flag['explanation']}")
        if ai := data.get("ai"):
            for reason in ai.get("reasons", []):
                out.append(f"- [{reason['severity']}] **{reason['title']}**: {reason['explanation']}")
        if f.evidence:
            out += ["", "Sources: " + "; ".join(e["title"] for e in f.evidence)]
        out.append("")
    return "\n".join(out)


def to_json(evaluation: Evaluation, company: Company) -> dict[str, Any]:
    return {
        "company": {"id": str(company.id), "name": company.name, "nse_symbol": company.nse_symbol},
        "evaluation": {
            "id": str(evaluation.id),
            "status": evaluation.status,
            "approved_by": evaluation.approved_by,
            "created_at": evaluation.created_at.isoformat(),
            "formula_version": evaluation.formula_version,
            "prompt_version": evaluation.prompt_version,
        },
        "findings": [
            {
                "module": f.module,
                "status": f.status,
                "summary": f.summary,
                "override_summary": f.override_summary,
                "override_reason": f.override_reason,
                "data": f.data,
                "evidence": f.evidence,
            }
            for f in evaluation.findings
        ],
    }
