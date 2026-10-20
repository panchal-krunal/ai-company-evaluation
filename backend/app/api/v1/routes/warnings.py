from dataclasses import asdict

from fastapi import APIRouter

from app.core.config import get_settings
from app.modules.financial_engine.service import run_all_checks
from app.schemas.warnings import WarningInputs, WarningReport, WarningResultRead

router = APIRouter(prefix="/warnings", tags=["financial-engine"])


@router.post("/evaluate", response_model=WarningReport)
async def evaluate_warnings(inputs: WarningInputs) -> WarningReport:
    """Run the eight deterministic warning checks on the supplied inputs."""
    return WarningReport(
        formula_version=get_settings().formula_version,
        results=[WarningResultRead(**asdict(r)) for r in run_all_checks(inputs)],
    )
