"""Representación de valores monetarios (COP, NUMERIC(14,2) en PostgreSQL).

Internamente se usa Decimal (nunca float) para no perder precisión.
En JSON los valores se envían como cadena con dos decimales, por ejemplo
"185000.00"; el frontend los formatea para mostrarlos en pesos colombianos.
"""
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

_DOS_DECIMALES = Decimal("0.01")


def a_decimal(valor):
    """Convierte un valor (Decimal, int o str) a Decimal con dos decimales."""
    if valor is None:
        raise ValueError("El valor monetario no puede ser nulo.")
    if isinstance(valor, float):
        # Evita arrastrar errores binarios de float a los cálculos.
        raise TypeError("Use Decimal, int o str para valores monetarios, no float.")
    try:
        numero = Decimal(valor)
    except (InvalidOperation, TypeError) as exc:
        raise ValueError(f"Valor monetario inválido: {valor!r}") from exc
    if not numero.is_finite():
        raise ValueError("El valor monetario debe ser finito.")
    return numero.quantize(_DOS_DECIMALES, rounding=ROUND_HALF_UP)


def serializar_dinero(valor):
    """Decimal -> cadena con dos decimales y sin notación científica."""
    return format(a_decimal(valor), "f")
