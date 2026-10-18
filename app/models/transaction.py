from dataclasses import dataclass
from datetime import datetime


@dataclass
class Transaction:
    id: int
    user_id: int
    paket: str
    jumlah_kredit: int
    harga: int
    status: str
    bukti_url: str | None
    created_at: datetime
    confirmed_at: datetime | None

    @staticmethod
    def from_row(row) -> "Transaction":
        return Transaction(
            id=row["id"],
            user_id=row["user_id"],
            paket=row["paket"],
            jumlah_kredit=row["jumlah_kredit"],
            harga=row["harga"],
            status=row["status"],
            bukti_url=row["bukti_url"],
            created_at=row["created_at"],
            confirmed_at=row["confirmed_at"],
        )
