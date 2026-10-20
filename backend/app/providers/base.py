"""Market-data provider adapter. Swap vendors without touching business logic."""

from datetime import date
from typing import Protocol


class FilingRef(Protocol):
    filing_type: str
    period_end: date
    url: str


class MarketDataProvider(Protocol):
    async def list_filings(self, symbol: str, since: date) -> list[FilingRef]: ...

    async def download(self, url: str) -> bytes: ...
