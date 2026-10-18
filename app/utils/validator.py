import re


_DOMAIN_RE = re.compile(
    r"^(?:[a-zA-Z0-9]"
    r"(?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+"
    r"[a-zA-Z]{2,}$"
)


def is_valid_domain(text: str) -> bool:
    text = text.strip().lower()
    text = text.removeprefix("http://").removeprefix("https://").removeprefix("www.")
    text = text.split("/")[0]
    return bool(_DOMAIN_RE.match(text))


def clean_domain(text: str) -> str:
    text = text.strip().lower()
    text = text.removeprefix("http://").removeprefix("https://").removeprefix("www.")
    return text.split("/")[0]
