"""
Competing-risks prediction for resected jejunoileal neuroendocrine tumors.

Two models are shipped together.

  preoperative   six variables known before the operation
  postoperative  the same six plus grade, nodal status and the two nodal counts

Each consists of two cause-specific Cox models, one for death from the index
cancer and one for death from any other cause, combined into a cumulative
incidence so that absolute risk allows for competing mortality.

Nothing here depends on patient data: the module needs only the coefficients
and baseline cumulative hazards in model_coefficients.json.

Equations: Supplementary Methods, section S4.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

MODEL_FILE = Path(__file__).with_name("model_coefficients.json")

# Incrementare quando cambia il formato di model_coefficients.json.
# app.py lo confronta all'avvio: cosi' un model.py vecchio lasciato nel
# repository viene segnalato subito, invece di rompersi piu' avanti.
SCHEMA = 2

# Column order of each design matrix. Must match the fitted models.
COV_POST = [
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
COV_PRE = [
    "eta_dx", "anno_dx", "dim_mm_std", "sesso_std=F",
    "estensione_std=Regionale", "estensione_std=Distante", "metastasectomia",
]


@dataclass
class Patient:
    """One patient, in the units the clinician actually has.

    The four pathological fields are optional: they are ignored by the
    preoperative model and are required only by the postoperative one.
    """

    age: float
    year_of_diagnosis: int
    size_mm: float
    female: bool
    extent: str                       # "Localized" | "Regional" | "Distant"
    metastasectomy: bool
    grade: str | None = None          # "G1" | "G2" | "G3"
    nodes_examined: int | None = None
    nodes_positive: int | None = None

    @property
    def nodal_status(self) -> str:
        """N0, N+ or 'not examined'.

        A patient in whom no node was removed has not been shown to be node
        negative. That is a third category, not a missing value, and the model
        was fitted with it as such.
        """
        if not self.nodes_examined:
            return "not examined"
        return "N+" if (self.nodes_positive or 0) > 0 else "N0"

    def row(self, covariates: list[str]) -> np.ndarray:
        nodal = self.nodal_status
        v = {
            "eta_dx": float(self.age),
            "anno_dx": float(self.year_of_diagnosis),
            "dim_mm_std": float(self.size_mm),
            "ln_esaminati": float(self.nodes_examined or 0),
            "ln_positivi": float(self.nodes_positive or 0) if self.nodes_examined else 0.0,
            "sesso_std=F": 1.0 if self.female else 0.0,
            "grado_final_std=G2": 1.0 if self.grade == "G2" else 0.0,
            "grado_final_std=G3": 1.0 if self.grade == "G3" else 0.0,
            "estensione_std=Regionale": 1.0 if self.extent == "Regional" else 0.0,
            "estensione_std=Distante": 1.0 if self.extent == "Distant" else 0.0,
            "stato_ln=N+": 1.0 if nodal == "N+" else 0.0,
            "stato_ln=Non esaminati": 1.0 if nodal == "not examined" else 0.0,
            "metastasectomia": 1.0 if self.metastasectomy else 0.0,
        }
        return np.array([v[c] for c in covariates], dtype=float)


class CompetingRisksModel:
    """One of the two models, loaded from the shared coefficient file."""

    def __init__(self, which: str = "postoperative", path: Path | str = MODEL_FILE):
        if which not in ("preoperative", "postoperative"):
            raise ValueError("which must be 'preoperative' or 'postoperative'")
        with open(path, encoding="utf-8") as fh:
            m = json.load(fh)
        if which not in m:
            raise ValueError(
                "model_coefficients.json does not contain the two models. "
                "It is probably the single-model file of version 1.x: replace it.")

        self.which = which
        self.version = m["model_version"]
        self.cohort = m["cohort"]
        self.times = np.asarray(m["times_months"], dtype=float)

        b = m[which]
        expected = COV_PRE if which == "preoperative" else COV_POST
        if b["covariates"] != expected:
            raise ValueError(f"{which}: coefficient file does not match the expected columns")

        self.covariates = b["covariates"]
        self.label = b["label"]
        self.means = np.asarray(b["centering_means"], dtype=float)
        self.beta_cancer = np.asarray(b["coef_cancer"], dtype=float)
        self.beta_other = np.asarray(b["coef_other"], dtype=float)
        self.H0_cancer = np.asarray(b["H0_cancer"], dtype=float)
        self.H0_other = np.asarray(b["H0_other"], dtype=float)
        self.kappa = float(b["kappa_recalibration"])
        self.tertiles = list(b["lp_tertile_cutpoints"])

    # ------------------------------------------------------------------ #
    def linear_predictors(self, patient: Patient) -> tuple[float, float]:
        """Centered linear predictors for the two causes.

        The baseline cumulative hazards refer to a patient at the mean of every
        covariate, so the means must be subtracted before the dot product.
        Omitting this step yields predicted risks of essentially zero.
        """
        x = patient.row(self.covariates) - self.means
        return float(x @ self.beta_cancer), float(x @ self.beta_other)

    def risk_group(self, patient: Patient) -> str:
        lp, _ = self.linear_predictors(patient)
        lo, hi = self.tertiles
        return "lower third" if lp < lo else ("middle third" if lp < hi else "upper third")

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
        overall = np.exp(-(H_cancer + H_other))
        prev = np.concatenate(([1.0], overall[:-1]))
        cif_cancer = np.cumsum(np.diff(H_cancer, prepend=0.0) * prev)
        cif_other = np.cumsum(np.diff(H_other, prepend=0.0) * prev)
        if recalibrate:
            cif_cancer = cif_cancer * self.kappa
        return {
            "times": self.times,
            "cancer": cif_cancer,
            "other": cif_other,
            "alive": np.clip(1.0 - cif_cancer - cif_other, 0.0, 1.0),
            "naive_cancer": 1.0 - np.exp(-H_cancer),
            "lp_cancer": lp_c,
        }

    def at(self, prediction: dict, months: float) -> dict:
        """Read the trajectory off at one horizon, as percentages."""
        i = int(np.argmin(np.abs(prediction["times"] - months)))
        return {k: 100 * float(prediction[k][i])
                for k in ("cancer", "other", "alive", "naive_cancer")}
