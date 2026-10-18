from dataclasses import dataclass
from datetime import datetime


@dataclass
class DomainCache:
    domain: str
    da: int | None
    pa: int | None
    ss: str | None
    age: str | None
    dr: int | None
    bc: str | None
    bc_df: int | None
    rd: str | None
    rd_df: int | None
    cached_at: datetime
    expired_at: datetime

    @staticmethod
    def from_row(row) -> "DomainCache":
        return DomainCache(
            domain=row["domain"],
            da=row["da"],
            pa=row["pa"],
            ss=row["ss"],
            age=row["age"],
            dr=row["dr"],
            bc=row["bc"],
            bc_df=row["bc_df"] if "bc_df" in row.keys() else None,
            rd=row["rd"],
            rd_df=row["rd_df"] if "rd_df" in row.keys() else None,
            cached_at=row["cached_at"],
            expired_at=row["expired_at"],
        )
