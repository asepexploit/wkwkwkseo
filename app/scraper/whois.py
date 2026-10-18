import asyncio
import logging
import urllib.request
import json

logger = logging.getLogger(__name__)


async def get_domain_age(domain: str) -> str | None:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _fetch_age, domain)


def _fetch_age(domain: str) -> str | None:
    # Coba API whatsmydns dulu (cepat, tidak butuh browser)
    result = _whatsmydns_age(domain)
    if result:
        return result
    # Fallback ke python-whois
    return _whois_age(domain)


def _whatsmydns_age(domain: str) -> str | None:
    try:
        url = f"https://www.whatsmydns.net/api/domain?q={domain}"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0 Safari/537.36",
                "Accept": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())

        years = data.get("years")
        months = data.get("months")
        days = data.get("days")
        date = data.get("date") or data.get("registered")

        if years is not None:
            parts = []
            if int(years) > 0:
                parts.append(f"{years} Tahun")
            if int(months or 0) > 0:
                parts.append(f"{months} Bulan")
            if parts:
                return ", ".join(parts)
            if days is not None:
                return f"{days} Hari"

        if date:
            return str(date)

        return None
    except Exception as e:
        logger.debug(f"whatsmydns {domain}: {e}")
        return None


def _whois_age(domain: str) -> str | None:
    try:
        import whois
        from datetime import datetime
        w = whois.whois(domain)
        created = w.creation_date
        if isinstance(created, list):
            created = created[0]
        if not created:
            return None
        age_days = (datetime.utcnow() - created).days
        years = age_days // 365
        months = (age_days % 365) // 30
        if years > 0:
            return f"{years} Tahun" + (f", {months} Bulan" if months else "")
        return f"{months} Bulan"
    except Exception as e:
        logger.debug(f"whois {domain}: {e}")
        return None
