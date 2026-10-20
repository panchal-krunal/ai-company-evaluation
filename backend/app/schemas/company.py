import uuid

from pydantic import BaseModel, ConfigDict


class CompanyCreate(BaseModel):
    name: str
    nse_symbol: str | None = None
    bse_code: str | None = None
    isin: str | None = None
    sector: str | None = None


class CompanyRead(CompanyCreate):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    coverage: str = "evaluated"
