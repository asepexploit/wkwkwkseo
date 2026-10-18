from dataclasses import dataclass
from datetime import datetime


@dataclass
class User:
    id: int
    telegram_id: int
    username: str | None
    nama: str | None
    kredit: int
    joined_at: datetime
    is_banned: bool

    @staticmethod
    def from_row(row) -> "User":
        return User(
            id=row["id"],
            telegram_id=row["telegram_id"],
            username=row["username"],
            nama=row["nama"],
            kredit=row["kredit"],
            joined_at=row["joined_at"],
            is_banned=bool(row["is_banned"]),
        )
