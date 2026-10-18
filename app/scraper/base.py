from dataclasses import dataclass


@dataclass
class DomainMetrics:
    da:  int | None = None
    pa:  int | None = None
    ss:  str | None = None
    age: str | None = None
    dr:  int | None = None
    bc:  str | None = None
    rd:  str | None = None
