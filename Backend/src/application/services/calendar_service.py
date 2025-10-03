"""Calendar utilities for Argentine banking branches."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Dict, Optional


@dataclass(frozen=True)
class OperatingWindow:
    """Represents an operating window for a branch."""

    start: time
    end: time
    label: str

    def contains(self, timestamp: datetime) -> bool:
        return self.start <= timestamp.time() <= self.end


ARGENTINE_HOLIDAYS = {
    # 2025 official holidays (extendable)
    date(2025, 1, 1),   # Ano Nuevo
    date(2025, 2, 3),   # Carnaval
    date(2025, 2, 4),   # Carnaval
    date(2025, 3, 24),  # Dia de la Memoria
    date(2025, 4, 17),  # Jueves Santo (con fines turisticos)
    date(2025, 4, 18),  # Viernes Santo
    date(2025, 5, 1),   # Dia del Trabajador
    date(2025, 5, 25),  # Revolucion de Mayo
    date(2025, 6, 16),  # Paso a la Inmortalidad de Guemes (trasladado)
    date(2025, 6, 20),  # Paso a la Inmortalidad de Belgrano
    date(2025, 7, 9),   # Independencia
    date(2025, 8, 18),  # San Martin (trasladado)
    date(2025, 10, 13), # Diversidad Cultural (trasladado)
    date(2025, 11, 20), # Soberania Nacional
    date(2025, 12, 8),  # Inmaculada Concepcion
    date(2025, 12, 25), # Navidad
}

BRANCH_OPERATING_WINDOW = OperatingWindow(start=time(8, 0), end=time(20, 0), label="interno")
PUBLIC_WINDOW = OperatingWindow(start=time(10, 0), end=time(17, 30), label="atencion publico")


class CalendarService:
    """Provides helpers to reason about working days and operating windows."""

    def __init__(self, holidays: Optional[set[date]] = None) -> None:
        self._holidays = holidays or set(ARGENTINE_HOLIDAYS)

    def is_holiday(self, day: date) -> bool:
        return day in self._holidays

    def is_business_day(self, day: date) -> bool:
        return day.weekday() < 5 and not self.is_holiday(day)

    def current_windows(self, ts: datetime) -> Dict[str, bool]:
        """Return operating flags for the provided timestamp."""
        open_branch = BRANCH_OPERATING_WINDOW.contains(ts)
        open_public = PUBLIC_WINDOW.contains(ts)
        return {
            "branch_open": open_branch,
            "public_open": open_public and self.is_business_day(ts.date()),
            "is_business_day": self.is_business_day(ts.date()),
            "is_holiday": self.is_holiday(ts.date()),
            "weekday": ts.weekday(),
        }

    def next_business_day(self, ts: datetime) -> datetime:
        candidate = ts + timedelta(days=1)
        while not self.is_business_day(candidate.date()):
            candidate += timedelta(days=1)
        return candidate.replace(hour=BRANCH_OPERATING_WINDOW.start.hour, minute=0, second=0, microsecond=0)

    def next_public_window(self, ts: datetime) -> datetime:
        if self.is_business_day(ts.date()) and ts.time() <= PUBLIC_WINDOW.end:
            if ts.time() < PUBLIC_WINDOW.start:
                return ts.replace(hour=PUBLIC_WINDOW.start.hour, minute=PUBLIC_WINDOW.start.minute, second=0, microsecond=0)
            return ts.replace(hour=PUBLIC_WINDOW.start.hour, minute=PUBLIC_WINDOW.start.minute, second=0, microsecond=0)
        next_day = self.next_business_day(ts)
        return next_day.replace(hour=PUBLIC_WINDOW.start.hour, minute=PUBLIC_WINDOW.start.minute)

    def describe(self, ts: datetime) -> Dict[str, str]:
        windows = self.current_windows(ts)
        status = "cerrado"
        if windows["branch_open"]:
            status = "operativo"
        if windows["public_open"]:
            status = "atencion al publico"
        return {
            "status": status,
            "business_day": "si" if windows["is_business_day"] else "no",
            "holiday": "si" if windows["is_holiday"] else "no",
        }
