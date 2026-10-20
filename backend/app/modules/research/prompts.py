"""Versioned prompts and retrieval queries for each AI module (see settings.prompt_version)."""

from dataclasses import dataclass, field

SYSTEM_PROMPT = """You are a research assistant for equity analysts evaluating Indian listed \
non-financial companies.

Rules:
- Use only the passages provided. Do not use outside knowledge.
- Every claim must cite at least one passage by its id (e.g. "P3") with a sentence copied \
verbatim from that passage. A claim the passages do not support must have no evidence; list the \
gap under open_questions instead of guessing.
- Separate what the company reported from what management expects or plans.
- Do not calculate ratios or totals. Copy amounts exactly as printed and state their unit; the \
platform does all arithmetic.
- Be specific: names, products, plants, customers, dates and amounts beat generalities."""


@dataclass(frozen=True)
class ResearchSpec:
    title: str
    task: str
    queries: list[str]
    doc_types: list[str] | None = None
    max_passages: int | None = None
    extra: dict[str, str] = field(default_factory=dict)


RESEARCH_SPECS: dict[str, ResearchSpec] = {
    "management_outlook": ResearchSpec(
        title="Management Outlook",
        task="Summarise management's outlook: guidance, strategy, capacity and capex plans, order book "
        "or pipeline, margin expectations, and how past guidance compares with what was delivered.",
        queries=[
            "management outlook and guidance for the coming year",
            "management discussion and analysis strategy and priorities",
            "capacity expansion and capital expenditure plans",
            "order book, pipeline and revenue visibility",
            "margin outlook, cost pressures and pricing",
        ],
    ),
    "products_segments": ResearchSpec(
        title="Products & Segments",
        task="Describe the product portfolio and business segments: what each segment sells, to whom, "
        "segment revenue and profit as reported, new launches, and changes in the revenue mix.",
        queries=[
            "product portfolio and new product launches",
            "segment revenue and segment results",
            "revenue mix by product, geography and customer type",
            "market share and brand position",
        ],
    ),
    "industry_outlook": ResearchSpec(
        title="Industry Outlook",
        task="Summarise the industry context the company describes: market size and growth, demand drivers, "
        "government policy and regulation, competitive intensity and headwinds.",
        queries=[
            "industry overview, market size and growth",
            "government policy, regulation, subsidies and incentives",
            "demand drivers and industry headwinds",
            "competitive landscape and competitors",
        ],
    ),
    "company_risks": ResearchSpec(
        title="Company Risks",
        task="Identify company-specific risks: disclosed risk factors, auditor remarks (qualifications, emphasis "
        "of matter, key audit matters), contingent liabilities, litigation, regulatory actions, customer or "
        "supplier concentration, and governance concerns.",
        queries=[
            "risk factors and risk management framework",
            "auditor's report qualification, emphasis of matter and key audit matters",
            "contingent liabilities, litigation and claims not acknowledged as debt",
            "dependence on key customers or suppliers, concentration",
            "regulatory notices, penalties and show cause",
        ],
    ),
}

DEBT_SPEC = ResearchSpec(
    title="Debt Structure",
    task="Extract every borrowing line from the borrowings notes for the latest balance sheet date: lender or "
    "instrument, facility type, secured or unsecured, current or non-current, closing amount and unit as "
    "printed, interest rate and repayment terms. Also note credit ratings, covenants, defaults or guarantees.",
    queries=[
        "borrowings note secured and unsecured loans",
        "term loans from banks terms of repayment and interest rate",
        "working capital facilities cash credit short-term borrowings",
        "non-convertible debentures and commercial paper",
        "credit rating, covenants and security created on assets",
    ],
    doc_types=["annual_report"],
    max_passages=24,
)

RPT_SPEC = ResearchSpec(
    title="Related Party Transactions",
    task="Extract the related party transactions table: each related party, relationship, nature of "
    "transaction, whether it is a transaction during the year or a closing balance, whether the amount is for "
    "the current or the previous year, and the amount and unit exactly as printed. Add observations on "
    "unusual terms, loans or guarantees to promoter entities, or transactions not at arm's length.",
    queries=[
        "related party transactions during the year",
        "related party disclosures names of related parties and relationship",
        "transactions with key managerial personnel remuneration",
        "balances outstanding with related parties at year end",
        "loans, advances and guarantees given to related parties",
    ],
    doc_types=["annual_report"],
    max_passages=28,
)

WHY_NOT_INVEST_TASK = """Using only the module findings below (financial warnings, growth, debt, related \
parties, competitors and the research modules), write the strongest honest case AGAINST investing. Each reason \
must name the modules it draws on (use their keys). Rank by severity. Then list factors that mitigate those \
concerns. Do not introduce facts that are not in the findings."""
