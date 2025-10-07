import math
import time
from datetime import datetime


# ============================================================
#  ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================

def fmt_num(num, digits=2):
    """Форматирование числа с ограничением знаков после запятой"""
    try:
        return f"{float(num):.{digits}f}"
    except Exception:
        return str(num)


def fmt_pct(value):
    """Форматирование процента"""
    try:
        return f"{float(value):.2f}%"
    except Exception:
        return str(value)


def round_qty(symbol, qty):
    """
    Округление количества до разумного значения.
    Можно адаптировать под фильтры биржи.
    """
    if qty < 0.0001:
        return 0.0
    return round(qty, 3)


def now_ms():
    """Текущее время в миллисекундах"""
    return int(time.time() * 1000)


def human_time(ms):
    """Преобразует миллисекунды в читаемый формат"""
    try:
        dt = datetime.fromtimestamp(ms / 1000)
        return dt.strftime("%d.%m %H:%M:%S")
    except Exception:
        return "-"


def format_duration(ms_start, ms_end=None):
    """Возвращает длительность сделки в минутах"""
    if not ms_start:
        return "-"
    if not ms_end:
        ms_end = now_ms()
    delta = (ms_end - ms_start) / 1000
    minutes = delta / 60
    hours = minutes / 60
    if hours >= 1:
        return f"{hours:.1f} ч"
    else:
        return f"{minutes:.0f} мин"


def percent_change(old, new):
    """Изменение в процентах"""
    if old == 0:
        return 0.0
    return (new - old) / old * 100.0


def clamp(value, min_value, max_value):
    """Ограничивает значение в диапазоне"""
    return max(min_value, min(value, max_value))
