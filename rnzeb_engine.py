"""
NZE Intelligence - RNZEB engine v0 (proof of concept)
Implements the Realistic Net Zero Energy Building (RNZEB) balance
  0 >= E1 + E2 - E3   (Ercal & Shafique, Sustainable Horizons 2026)
and the BIM-ICE embodied-carbon workflow
  CF = sum(Q_i * EF_i) (Ercal & Shafique, Carbon Footprints 2026)
"""
from dataclasses import dataclass, field
import json, math, os

HERE = os.path.dirname(os.path.abspath(__file__))
MJ_PER_KWH = 3.6


# ---------- E1: embodied ----------
def embodied_carbon(materials):
    """materials: list of {material, qty_kg, ec_factor} -> kgCO2e (A1-A3)"""
    return sum(m["qty_kg"] * m["ec_factor"] for m in materials)


def embodied_energy_kwh(materials):
    """materials need ee_factor in MJ/kg. Returns kWh."""
    return sum(m["qty_kg"] * m["ee_factor"] for m in materials) / MJ_PER_KWH


# ---------- E2: operational (annual, kWh) ----------
@dataclass
class Operation:
    heating_load_kw: float
    heating_hours: float = 1800
    heating_eff: float = 3.5        # COP for heat pump, boiler efficiency (e.g. 0.92) for gas
    cooling_kwh_thermal: float = 0  # cooling load expressed as annual thermal kWh
    cooling_cop: float = 1.0
    lighting_kwh: float = 0
    appliances_kwh: float = 0
    all_electric: bool = True

    def breakdown(self):
        return {
            "heating": self.heating_load_kw * self.heating_hours / self.heating_eff,
            "cooling": self.cooling_kwh_thermal / self.cooling_cop,
            "lighting": self.lighting_kwh,
            "appliances": self.appliances_kwh,
        }

    def annual_kwh(self):
        return sum(self.breakdown().values())


# ---------- E3: generation (annual, kWh) ----------
@dataclass
class Generation:
    pv_area_m2: float = 0
    irradiance_kwh_m2: float = 980
    pv_eff: float = 0.215
    wind_kwh: float = 0             # manufacturer/site estimate; kept separate and conservative

    def breakdown(self):
        return {"pv": self.pv_area_m2 * self.irradiance_kwh_m2 * self.pv_eff,
                "wind": self.wind_kwh}

    def annual_kwh(self):
        return sum(self.breakdown().values())


# ---------- RNZEB balance ----------
def energy_net_zero(e1_kwh, e2_annual, e3_annual, lifespan=50):
    """Returns exact years, the building-life year in which balance is reached,
    and whether it happens within lifespan."""
    surplus = e3_annual - e2_annual
    if surplus <= 0:
        return {"surplus_kwh": surplus, "years_exact": math.inf, "year_reached": None, "within_life": False}
    yrs = e1_kwh / surplus
    return {"surplus_kwh": surplus, "years_exact": yrs, "year_reached": math.ceil(yrs),
            "within_life": yrs <= lifespan}


def grid_intensity(year_index, start=0.15, annual_decline=0.07, floor=0.01):
    """ILLUSTRATIVE UK grid carbon intensity (kgCO2e/kWh) for year_index=1..N.
    Placeholder assumption - replace with DESNZ / NESO FES projections."""
    return max(floor, start * (1 - annual_decline) ** (year_index - 1))


def carbon_net_zero(ec_kg, e2_annual, e3_annual, lifespan=50, **grid):
    """Embodied carbon offset by exported surplus x (decarbonising) grid factor.
    Assumes all-electric building, so net-annual-positive => zero operational carbon."""
    surplus = e3_annual - e2_annual
    cum, curve = 0.0, []
    year_reached = None
    for y in range(1, lifespan + 1):
        cum += max(surplus, 0) * grid_intensity(y, **grid)
        curve.append(cum)
        if year_reached is None and cum >= ec_kg:
            year_reached = y
    return {"year_reached": year_reached, "offset_at_end_kg": cum,
            "share_offset": cum / ec_kg if ec_kg else 1, "curve": curve}


# ---------- Material substitution recommender (rule-based v0) ----------
def load_cf_tables(path=os.path.join(HERE, "cf_tables.json")):
    return json.load(open(path))


def substitution_library(tables):
    """Derive functionally-equivalent substitutions from paired traditional/low-carbon
    scenarios (same row order in Carbon Footprints supplementary tables S1-S6)."""
    lib = {}
    for system in ("steel", "rc", "timber"):
        trad, low = tables[f"{system}_trad"], tables[f"{system}_low"]
        for a, b in zip(trad, low):
            if a["material"] != b["material"]:
                lib[a["material"]] = {
                    "alternative": b["material"],
                    "mass_ratio": b["qty_kg"] / a["qty_kg"],   # e.g. mineral wool -> PIR ~ 1/4.6
                    "ec_factor": b["ec_factor"],
                }
    return lib


def recommend(materials, lib):
    recs = []
    for m in materials:
        alt = lib.get(m["material"])
        if not alt:
            continue
        before = m["qty_kg"] * m["ec_factor"]
        after = m["qty_kg"] * alt["mass_ratio"] * alt["ec_factor"]
        if after < before:
            recs.append({"replace": m["material"], "with": alt["alternative"],
                         "saving_kg": before - after, "saving_pct": 100 * (before - after) / before})
    return sorted(recs, key=lambda r: -r["saving_kg"])
