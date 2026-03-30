def divide(dividendo: int | float, divisor: int | float) -> float:
    """
    Evita ZeroDivisionError.
    """
    if divisor == 0:
        return 0
    else:
        return dividendo / divisor
