"""Serial campaign accounting; uncertainty keeps the entire cell reservation."""

import json
from decimal import Decimal
from pathlib import Path


class SpendLedger:
    def __init__(self, path, limit="100"):
        self.path = Path(path)
        self.limit = Decimal(str(limit))
        if not self.limit.is_finite() or not 0 < self.limit <= 100:
            raise ValueError("Campaign cap must be positive and at most $100")
        self.cells = {}
        self.path.open("x", encoding="ascii").close()
        self._append({"event": "opened", "limit": str(self.limit)})

    def _append(self, event):
        with self.path.open("a", encoding="ascii") as stream:
            stream.write(json.dumps(event) + "\n")
            stream.flush()

    @property
    def committed(self):
        return sum(
            (row.get("actual", row["reserved"]) for row in self.cells.values()),
            Decimal(0),
        )

    def reserve(self, cell, amount="7"):
        value = Decimal(str(amount))
        if (
            cell in self.cells
            or not value.is_finite()
            or not 0 < value <= 7
            or self.committed + value > self.limit
        ):
            raise ValueError("Duplicate, invalid, or unaffordable cell reservation")
        if any("actual" not in row for row in self.cells.values()):
            raise ValueError("Unsettled prior cell: do not launch another")
        self._append({"event": "reserved", "cell": cell, "amount": str(value)})
        self.cells[cell] = {"reserved": value}

    def settle(self, cell, actual):
        value = Decimal(str(actual))
        row = self.cells[cell]
        if not value.is_finite() or value < 0 or "actual" in row:
            raise ValueError("Invalid or duplicate settlement")
        self._append({"event": "settled", "cell": cell, "actual": str(value)})
        row["actual"] = value
        if value > row["reserved"] or self.committed > self.limit:
            raise ValueError("Accounting breach: stop campaign")
