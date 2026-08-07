# Jejunoileal NET Risk Calculator

Absolute risk of death from the tumor after intestinal resection for a jejunoileal
neuroendocrine tumor, estimated **in the presence of death from other causes**.

Developed on 2,496 patients from the SEER programme (17 registries, 2000–2023) and
externally validated on 261 consecutively resected patients at the University of Bologna.

**Live application:** _(add the Streamlit Community Cloud URL here after deployment)_

---

## What it returns

For a given patient and time horizon (3, 5 or 10 years) the calculator returns a complete
partition of the patient's future, summing to 100%:

| Output | Meaning |
|---|---|
| Alive | neither event has occurred |
| Disease-related death | cumulative incidence of death from the tumor |
| Non-disease-related death | the competing event |

alongside the patient's position in the risk distribution of the development cohort, the
full trajectory over ten years, and a direct comparison with the conventional
one-minus-survival calculation, which ignores competing mortality and always overstates
the risk.

Absolute risk depends on where the patient is treated, so the sidebar asks that question
directly. Choosing *high-volume referral center* applies a single multiplicative factor
(κ = 0.59) estimated in the validation cohort, where the observed risk was about 40% lower
than the registry predicted. The factor rescales absolute risk without touching any
coefficient, so the ranking of patients — and therefore the discrimination of the model —
is identical either way.

## What it does not do

It does not recommend treatment and does not label patients above a risk threshold. Every
patient to whom the model applies has already undergone resection, and no adjuvant decision
in this disease is currently governed by a threshold of predicted risk. The tool is for
counseling and for planning the intensity of follow-up.

---

## Running it

### Locally

```bash
git clone https://github.com/<user>/<repo>.git
cd <repo>
pip install -r requirements.txt
streamlit run app.py
```

### On Streamlit Community Cloud

1. Push this repository to GitHub (public).
2. Go to <https://share.streamlit.io>, sign in with GitHub, choose **New app**.
3. Select the repository, branch `main`, main file `app.py`.
4. Deploy. Dependencies are read from `requirements.txt`.

No configuration, secrets or environment variables are required.

---

## Files

| File | Contents |
|---|---|
| `app.py` | The Streamlit interface |
| `model.py` | The competing-risks model: design matrix, linear predictors, cumulative incidence |
| `model_coefficients.json` | Coefficients, centring means, the two baseline cumulative hazards, recalibration factor, risk tertile cut points |
| `requirements.txt` | Python dependencies |

## Data

**No patient-level data are contained in this repository, and none may be added to it.**
`.gitignore` blocks the file types in which the source data are held.

The development data are publicly available from the National Cancer Institute
(<https://seer.cancer.gov>) under its data use agreement. The institutional validation data
cannot be shared because they contain information that could compromise patient privacy;
they are available from the corresponding author on reasonable request.

The application transmits and stores nothing. Values entered by the user exist only for the
duration of the browser session.

---

## Model in one paragraph

Two cause-specific Cox proportional hazards models are fitted to the same ten predictors —
age, sex, year of diagnosis, grade, tumor size, disease extent, nodal status, nodes
examined, positive nodes, metastasectomy — one for death from the index cancer and one for
death from any other cause. For a patient with covariate vector *x*, centred on the
training means, the cause-specific cumulative hazards are H₁(t) = H₀₁(t)·exp(β₁ᵀx) and
H₂(t) = H₀₂(t)·exp(β₂ᵀx), overall survival is S(t) = exp{−H₁(t) − H₂(t)}, and the
cumulative incidence of cancer death is obtained by accumulating the cause-specific hazard
increments weighted by the probability of still being alive.

Ten survival algorithms were compared before this model was chosen, including random
survival forests, gradient boosted trees and a neural network. None outperformed ordinary
Cox regression.

**Performance** — development (5-fold cross-validation, 5 imputed datasets): C-index 0.775.
External validation: C-index 0.817 (0.744–0.882), calibration slope 1.18 (0.67–1.69),
observed/expected 0.59 at five years.

## Limitations

External validation rests on 26 deaths from the tumor, so calibration is imprecise. The
recalibration factor was estimated in the same cohort in which it was assessed and is
therefore optimistic. Validation was at a single European referral center. Neither cohort
recorded the Ki-67 index as a continuous value, chromogranin A, carcinoid syndrome, or
systemic treatment — and neither recorded comorbidity, a gap that falls squarely on the
model for death from other causes.

---

## Citation

Ricci C, D'Ambra V, Sissa L, Alberici L, Ingaldi C, Malvi D, Fichera M, Lamberti G,
Campana D, Mosconi C & Casadei R. *Predicting cancer-specific death after resection of
jejunoileal neuroendocrine tumors: competing-risks model development in SEER and external
validation.* (submitted)

## Licence

MIT — see `LICENSE`.

## Disclaimer

For research and educational use. This is not a medical device and must not substitute for
clinical judgement. The authors accept no responsibility for decisions taken on the basis
of its output.
