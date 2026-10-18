import asyncio
from app.queue.worker import run_worker
from app.utils.constants import MAX_WORKERS


class QueueManager:
    def __init__(self):
        self._queue: asyncio.Queue = asyncio.Queue()
        self._workers: list[asyncio.Task] = []
        self._active: int = 0  # domain yang sedang diproses worker

    async def start(self):
        for _ in range(MAX_WORKERS):
            task = asyncio.create_task(run_worker(self._queue, self))
            self._workers.append(task)

    def queue_size(self) -> int:
        return self._queue.qsize()

    def active_count(self) -> int:
        return self._active

    def total_busy(self) -> int:
        """Jumlah domain sedang diproses + menunggu antrian."""
        return self._active + self._queue.qsize()

    async def enqueue(self, domain: str, tg_id: int = 0) -> dict:
        future: asyncio.Future = asyncio.get_event_loop().create_future()
        # posisi antrian = berapa domain di queue SEBELUM domain ini
        position = self._queue.qsize() + self._active
        await self._queue.put((domain, tg_id, future))
        return await future

    async def stop(self):
        for w in self._workers:
            w.cancel()
