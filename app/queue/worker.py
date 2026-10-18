import asyncio
from app.services.domain_service import check_domain
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


_TIMEOUT = 300  # 5 menit max per domain (moz + ahrefs sekuensial 1 Chrome)


async def run_worker(queue: asyncio.Queue, manager=None):
    while True:
        domain, tg_id, future = await queue.get()
        if manager:
            manager._active += 1
        try:
            result = await asyncio.wait_for(
                check_domain(domain, tg_id=tg_id),
                timeout=_TIMEOUT,
            )
            future.set_result(result)
        except asyncio.TimeoutError:
            logger.error(f"Worker timeout for {domain} (>{_TIMEOUT}s)")
            future.set_exception(Exception(f"Timeout setelah {_TIMEOUT} detik"))
        except Exception as e:
            logger.error(f"Worker error for {domain}: {e}")
            future.set_exception(e)
        finally:
            if manager:
                manager._active = max(0, manager._active - 1)
            queue.task_done()
