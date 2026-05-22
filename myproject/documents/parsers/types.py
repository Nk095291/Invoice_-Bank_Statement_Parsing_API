from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal


@dataclass
class ParsedLineItem:
    description: str
    amount: Decimal
    quantity: str | None = None
    sort_order: int = 0


@dataclass
class ParsedBankTransaction:
    transaction_date: date | None
    description: str
    debit: Decimal | None = None
    credit: Decimal | None = None
    balance: Decimal | None = None
    currency: str | None = None


@dataclass
class ParsedDocument:
    vendor: str | None = None
    document_date: date | None = None
    total_amount: Decimal | None = None
    currency: str | None = None
    metadata: dict = field(default_factory=dict)
    line_items: list[ParsedLineItem] = field(default_factory=list)
    transactions: list[ParsedBankTransaction] = field(default_factory=list)
