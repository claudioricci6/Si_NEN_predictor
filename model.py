"""
Competing-risks prediction model for resected jejunoileal neuroendocrine tumors.

Two cause-specific Cox models — one for death from the index cancer, one for
death from other causes — are combined into a cumulative incidence function.
Nothing here depends on the original patient data: the module needs only the
coefficients and baseline cumulative hazards stored in model_coefficients.json.

Reference implementation of the equations: see Supplementary Methods, section S4.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

MODEL_FILE = Path(__file__).with_name("model_coefficients.json")

# Order of the columns in the design matrix. Must match the training model.
COVARIATES = [
    "eta_dx",                    # age at diagnosis, years
    "anno_dx",                   # year of diagnosis
    "dim_mm_std",                # tumor size, mm
    "ln_esaminati",              # lymph nodes examined, n
    "ln_positivi",               # positive lymph nodes, n
    "sesso_std=F",               # female sex
    "grado_final_std=G2",        # grade G2 (reference G1)
    "grado_final_std=G3",        # grade G3
    "estensione_std=Regionale",  # regional disease (reference localized)
    "estensione_std=Distante",   # distant disease
    "stato_ln=N+",               # node positive (reference N0)
    "stato_ln=Non esaminati",    # no node examined
    "metastasectomia",           # surgery to a distant site
]


@dataclass
class Patient:
    """One patient, in the units the clinician actually has."""

    age: float                 # years
    year_of_diagnosis: int
    size_mm: float             # largest diameter of the primary, mm
    nodes_examined: int
    nodes_positive: int
    female: bool
    grade: str                 # "G1" | "G2" | "G3"
    extent: str                # "Localized" | "Regional" | "Distant"
    metastasectomy: bool

    # ------------------------------------------------------------------ #
    @property
    def nodal_status(self) -> str:
        """N0, N+ or 'not examined'.

        A patient in whom no node was removed has not been shown to be node
        negative. That is a third category, not a missing value, and the model
        was fitted with it as such.
        """
        if self.nodes_examined == 0:
            return "not examined"
        return "N+" if self.nodes_positive > 0 else "N0"

    def design_row(self) -> np.ndarray:
        """Build the model-matrix row, in COVARIATES order."""
        nodal = self.nodal_status
        return np.array(
            [
                float(self.age),
                float(self.year_of_diagnosis),
                float(self.size_mm),
                float(self.nodes_examined),
                float(self.nodes_positive if self.nodes_examined > 0 else 0),
                1.0 if self.female else 0.0,
                1.0 if self.grade == "G2" else 0.0,
                1.0 if self.grade == "G3" else 0.0,
                1.0 if self.extent == "Regional" else 0.0,
                1.0 if self.extent == "Distant" else 0.0,
                1.0 if nodal == "N+" else 0.0,
                1.0 if nodal == "not examined" else 0.0,
                1.0 if self.metastasectomy else 0.0,
            ],
            dtype=float,
        )


class CompetingRisksModel:
    """Absolute risk of death from the tumor, allowing for death from other causes."""

    def __init__(self, path: Path | str = MODEL_FILE):
        with open(path, encoding="utf-8") as fh:
            m = json.load(fh)

        if m["covariates"] != COVARIATES:
            raise ValueError("model_coefficients.json does not match COVARIATES")

        self.means = np.asarray(m["centering_means"], dtype=float)
        self.beta_cancer = np.asarray(m["coef_cancer"], dtype=float)
        self.beta_other = np.asarray(m["coef_other"], dtype=float)
        self.times = np.asarray(m["times_months"], dtype=float)
        self.H0_cancer = np.asarray(m["H0_cancer"], dtype=float)
        self.H0_other = np.asarray(m["H0_other"], dtype=float)
        self.kappa = float(m["kappa_recalibration"])
        self.tertiles = list(m["lp_tertile_cutpoints"])
        self.cohort = m["cohort"]
        self.version = m["model_version"]

    # ------------------------------------------------------------------ #
    def linear_predictors(self, patient: Patient) -> tuple[float, float]:
        """Centred linear predictors for the two causes.

        The baseline cumulative hazards refer to a patient at the mean of every
        covariate, so the means must be subtracted before the dot product.
        Omitting this step yields predicted risks of essentially zero.
        """
        x = patient.design_row() - self.means
        return float(x @ self.beta_cancer), float(x @ self.beta_other)

    def risk_group(self, patient: Patient) -> str:
        """Where this patient falls in the training cohort's risk distribution."""
        lp, _ = self.linear_predictors(patient)
        lo, hi = self.tertiles
        if lp < lo:
            return "lower third"
        if lp < hi:
            return "middle third"
        return "upper third"

    # ------------------------------------------------------------------ #
    def predict(self, patient: Patient, recalibrate: bool = False) -> dict:
        """Full risk trajectory from diagnosis to 120 months.

        Returns cumulative incidences that partition the patient's future:
        death from the tumor, death from other causes, still alive. The three
        sum to 1 at every time point, which is the property the conventional
        one-minus-survival calculation does not have.
        """
        lp_c, lp_o = self.linear_predictors(patient)

        H_cancer = self.H0_cancer * np.exp(lp_c)
        H_other = self.H0_other * np.exp(lp_o)
        overall_survival = np.exp(-(H_cancer + H_other))

        # cumulative incidence: accumulate cause-specific hazard increments,
        # each weighted by the probability of still being alive just before
        prev_surv = np.concatenate(([1.0], overall_survival[:-1]))
        cif_cancer = np.cumsum(np.diff(H_cancer, prepend=0.0) * prev_surv)
        cif_other = np.cumsum(np.diff(H_other, prepend=0.0) * prev_surv)

        if recalibrate:
            cif_cancer = cif_cancer * self.kappa

        # what the conventional method would report: ignores competing mortality
        naive_cancer = 1.0 - np.exp(-H_cancer)

        return {
            "times": self.times,
            "cancer": cif_cancer,
            "other": cif_other,
            "alive": np.clip(1.0 - cif_cancer - cif_other, 0.0, 1.0),
            "naive_cancer": naive_cancer,
            "lp_cancer": lp_c,
        }

    def at(self, prediction: dict, months: float) -> dict:
        """Read the trajectory off at one horizon, as percentages."""
        i = int(np.argmin(np.abs(prediction["times"] - months)))
        return {
            "cancer": 100 * float(prediction["cancer"][i]),
            "other": 100 * float(prediction["other"][i]),
            "alive": 100 * float(prediction["alive"][i]),
            "naive_cancer": 100 * float(prediction["naive_cancer"][i]),
        }
