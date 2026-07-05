"""HeatShield risk engine excerpt: transparent weighted scoring.

Each ward receives a heat risk score computed as a weighted sum of normalized
features. Per-feature attribution is preserved so the UI can explain exactly
why a ward is high risk.
"""
WEIGHTS = {
    "land_surface_temperature": 0.30,
    "vegetation_index_inverse": 0.20,
    "population_density": 0.20,
    "impervious_surface_fraction": 0.15,
    "elderly_population_share": 0.15,
}

def risk_score(features: dict[str, float]) -> tuple[float, dict[str, float]]:
    """Return total risk in [0, 1] plus per-feature attribution."""
    contributions = {k: WEIGHTS[k] * features.get(k, 0.0) for k in WEIGHTS}
    return sum(contributions.values()), contributions
