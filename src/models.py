from dataclasses import dataclass, field
from src.config import NOT_FOUND

@dataclass
class Field:
    value: str = NOT_FOUND
    source: str = 'No localizado'
    confidence: str = 'bajo'

@dataclass
class Evidence:
    id: str
    name: str
    sha256: str
    pages: list[str] = field(default_factory=list)
    status: str = 'Texto extraído'

@dataclass
class Report:
    process_number: str
    fields: dict[str, Field]
    obligations: list[Field]
    evidence: list[Evidence]
    warnings: list[str] = field(default_factory=list)
    activities: dict[int, str] = field(default_factory=dict)
    links: dict[int, list[str]] = field(default_factory=dict)
    contract_source: dict = field(default_factory=dict)
