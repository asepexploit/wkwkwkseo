from dataclasses import dataclass
from datetime import datetime


@dataclass
class CheckHistory:
    id: int
    user_id: int
    domain: str
    da: int | None
    pa: int | None
    ss: str | None
    age: str | None
    dr: int | None
    bc: str | None
    rd: str | None
    checked_at: datetime

    @staticmethod
    def from_row(row) -> "CheckHistory":
        return CheckHistory(
            id=row["id"],
            user_id=row["user_id"],
            domain=row["domain"],
            da=row["da"],
            pa=row["pa"],
            ss=row["ss"],
            age=row["age"],
            dr=row["dr"],
            bc=row["bc"],
            rd=row["rd"],
            checked_at=row["checked_at"],
        )
