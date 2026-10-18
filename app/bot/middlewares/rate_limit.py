import time
from collections import defaultdict
from app.utils.constants import RATE_LIMIT_PER_MINUTE

_buckets: dict[int, list[float]] = defaultdict(list)
_processing: set[int] = set()


def is_rate_limited(telegram_id: int) -> bool:
    now = time.time()
    window = _buckets[telegram_id]
    _buckets[telegram_id] = [t for t in window if now - t < 60]
    if len(_buckets[telegram_id]) >= RATE_LIMIT_PER_MINUTE:
        return True
    _buckets[telegram_id].append(now)
    return False


def is_processing(telegram_id: int) -> bool:
    return telegram_id in _processing


def set_processing(telegram_id: int, value: bool) -> None:
    if value:
        _processing.add(telegram_id)
    else:
        _processing.discard(telegram_id)
