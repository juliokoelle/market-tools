"""Shared utilities for the Daily Global Economic Briefing."""

from datetime import date


def today() -> str:
    return date.today().isoformat()


def oz_to_gram(price_per_oz: float) -> float:
    return round(price_per_oz / 31.1035, 2)


def oz_to_kg(price_per_oz: float) -> float:
    return round(price_per_oz / 31.1035 * 1000, 2)


def format_precious_metal(name: str, price_per_oz: float) -> str:
    """Return the mandatory tri-unit price block for Gold or Silver."""
    g = oz_to_gram(price_per_oz)
    kg = oz_to_kg(price_per_oz)
    return (
        f"{name}\n"
        f"  {price_per_oz:,.2f} USD/oz\n"
        f"  {g:,.2f} USD/g\n"
        f"  {kg:,.2f} USD/kg"
    )


def data_dir(run_date: str = None) -> str:
    d = run_date or today()
    return f"data/raw/{d}"


def output_path(run_date: str = None) -> str:
    d = run_date or today()
    return f"outputs/{d}-briefing.md"
