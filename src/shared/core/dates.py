# Si el script se ejecuta directamente, agregamos la raiz del proyecto para que los imports `src.*` funcionen.
if __package__ in {None, ""}:
    import sys
    from pathlib import Path

    project_root = Path(".").resolve()
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

import calendar
from copy import deepcopy
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from src.config import Config


class Date:
    """
    Clase INMUTABLE principal para manejar fechas y horas de forma consistente
    entre servidores con diferentes zonas horarias.
    """

    DEFAULT_TZ = ZoneInfo(Config.local_timezone)
    UTC_TZ = ZoneInfo("UTC")

    def __init__(self, dt: datetime | None = None):
        if dt is None:
            self.__dt = datetime.now(tz=self.DEFAULT_TZ)
        else:
            if dt.tzinfo is None:
                self.__dt = dt.replace(tzinfo=self.DEFAULT_TZ)
            else:
                self.__dt = dt

    def __str__(self) -> str:
        return str(self.__dt)

    # region Constructors
    @classmethod
    def from_timestamp(cls, timestamp: float | int) -> Date:
        """
        Crea DateUtils desde un timestamp (segundos desde epoch).
        """
        return cls(datetime.fromtimestamp(timestamp))

    @classmethod
    def from_timestamp_ms(cls, timestamp: float) -> Date:
        """
        Crea DateUtils desde un timestamp en milisegundos desde epoch.

        Si no se especifica tz → se crea en UTC (comportamiento más seguro y recomendado).
        """
        return cls(datetime.fromtimestamp(timestamp / 1000))

    @classmethod
    def from_isostring(cls, isostring: str) -> Date:
        """Parsea ISO 8601 (soporta 'Z' y offset)."""
        cleaned = isostring.replace("Z", "+00:00")
        return cls(datetime.fromisoformat(cleaned))

    @classmethod
    def from_str(cls, date_string: str, fmt: str | None = None) -> Date:
        """
        Parsea fechas. Si se pasa `fmt`, lo usa directamente.
        Sin `fmt`, prueba solo formatos year-first (no ambiguos).
        """
        if fmt is not None:
            return cls(datetime.strptime(date_string.strip(), fmt))

        formatos = [
            "%Y-%m-%d",
            "%Y/%m/%d",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%d %H:%M:%S",
        ]

        for f in formatos:
            try:
                return cls(datetime.strptime(date_string.strip(), f))
            except ValueError:
                continue

        raise ValueError(f"Formato de fecha no soportado: '{date_string}'")

    # endregion Constructors

    # region Properties
    @property
    def utc(self) -> Date:
        """Devuelve el mismo instante en UTC."""
        return self.__class__(self.__dt.astimezone(self.UTC_TZ))

    @property
    def local(self) -> Date:
        """Devuelve el mismo instante en la zona horaria local por defecto (America/Bogota)."""
        return self.__class__(self.__dt.astimezone(self.DEFAULT_TZ))

    @property
    def to_isostring(self) -> str:
        """ISO 8601 en UTC con 'Z' (formato recomendado para APIs)."""
        return self.utc.__dt.isoformat().replace("+00:00", "Z")

    # endregion Properties

    # region Helpers

    def replace_tz(self, tz: ZoneInfo | None = None) -> Date:
        """Convierte cualquier datetime a DateUtils (si es naive → lo asume como DEFAULT_TZ)."""
        dt = deepcopy(self)
        if tz is None:
            dt.__dt = dt.__dt.replace(tzinfo=self.DEFAULT_TZ)
        else:
            dt.__dt = dt.__dt.replace(tzinfo=tz)
        return dt

    def get_tz(self) -> str:
        return str(self.__dt.tzinfo)

    def get_weekday(self) -> int:
        return calendar.weekday(self.__dt.year, self.__dt.month, self.__dt.day)

    def next_business_day(self, no_working_days: list[int] | None = None) -> Date:
        if no_working_days is None:
            no_working_days = [5, 6]  # sábado y domingo

        dt = deepcopy(self)
        while dt.get_weekday() in no_working_days:
            dt.__dt += timedelta(days=1)

        return dt

    def next_business_day_col(self, no_working_days: list[int] | None = None) -> Date:
        from holidays_co import get_colombia_holidays_by_year

        if no_working_days is None:
            no_working_days = [5, 6]  # sábado y domingo

        dt = deepcopy(self)
        weekday = dt.get_weekday()
        holidays = {h.date for h in get_colombia_holidays_by_year(dt.__dt.year)}
        while dt.__dt.date() in holidays or weekday in no_working_days:
            dt.__dt += timedelta(days=1)
            weekday = dt.get_weekday()
        return dt

    # endregion Helpers


def last_completed_workweek_range(
    reference: date | datetime | None = None,
) -> tuple[date, date]:
    """Retorna el rango lunes-viernes de la ultima semana laboral completa."""

    if reference is None:
        reference_date = datetime.now(tz=Date.DEFAULT_TZ).date()
    elif isinstance(reference, datetime):
        reference_date = reference.date()
    else:
        reference_date = reference

    weekday = reference_date.weekday()
    days_back_to_friday = weekday - 4 if weekday >= 5 else weekday + 3
    friday = reference_date - timedelta(days=days_back_to_friday)
    monday = friday - timedelta(days=4)
    return monday, friday


if __name__ == "__main__":
    current_date = Date()
    print(current_date.get_tz())
    print(current_date.utc)
    print(current_date.get_tz())
    print(current_date.local)
    print(current_date.get_tz())
