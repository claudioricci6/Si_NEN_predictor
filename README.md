# Jejunoileal NET Risk Calculator

Absolute risk after intestinal resection for a jejunoileal neuroendocrine tumor, estimated
**in the presence of death from other causes**.

Developed on 2,496 patients from the SEER programme (17 registries, 2000–2023) and
externally validated on 261 consecutively resected patients at the University of Bologna.

**Live application:** <https://sinenpredictor-mva5w8ltbkmy9cqcf9zux9.streamlit.app/>

---

## Two models, chosen by the user

The first question the application asks is which model to use.

| | Preoperative | Postoperative |
|---|---|---|
| When | at the first consultation | at the first postoperative visit |
| Variables | age, sex, year of diagnosis, tumor size, disease extent, metastasectomy | the same six, plus grade, nodal status, nodes examined, positive nodes |
| Parameters | 7 | 13 |
| Cross-validated C-index | 0.772 | 0.777 |
| External C-index | 0.823 | 0.817 |
| Recalibration factor | 0.62 | 0.59 |

The paired difference in external discrimination was +0.006, with a bootstrap interval from
−0.025 to +0.042: the two models are indistinguishable. Grade and the nodal variables add
almost nothing once age, sex, calendar period, tumor size and disease extent are known,
which is why a number can be given to the patient before the operation and not only after it.

**The preoperative model does not decide whether to operate.** It was developed exclusively
in patients who underwent an intestinal resection, so it estimates what resection is
expected to achieve. A patient for whom surgery is being withheld is not represented in
these data.

## What the application returns

For a given patient and horizon (3, 5 or 10 years) it returns a complete partition of the
patient's future, summing to 100%:

| Output | Meaning |
|---|---|
| Alive | neither event has occurred |
| Disease-related death | cumulative incidence of death from the tumor |
| Non-disease-related death | the competing event |

alongside the patient's position in the risk distribution of the development cohort, the
trajectory over ten years, and a comparison with the conventional one-minus-survival
calculation, which ignores competing mortality and always overstates the risk.

Absolute risk depends on where the patient is treated, so the sidebar asks that question
directly. Choosing *high-volume referral center* applies a single multiplicative factor,
specific to each model, estimated in the validation cohort. The factor rescales absolute
risk without touching any coefficient, so the ranking of patients is identical either way.

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

## Files

| File | Contents |
|---|---|
| `app.py` | The Streamlit interface |
| `model.py` | Both competing-risks models: design matrix, linear predictors, cumulative incidence |
| `model_coefficients.json` | Coefficients, centering means, baseline cumulative hazards, recalibration factors and risk tertile cut points, for each of the two models |
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

## Model in one paragraph

Each model consists of two cause-specific Cox proportional hazards models, one for death
from the index cancer and one for death from any other cause. For a patient with covariate
vector *x*, centered on the training means, the cause-specific cumulative hazards are
H₁(t) = H₀₁(t)·exp(β₁ᵀx) and H₂(t) = H₀₂(t)·exp(β₂ᵀx), overall survival is
S(t) = exp{−H₁(t) − H₂(t)}, and the cumulative incidence of cancer death is obtained by
accumulating the cause-specific hazard increments weighted by the probability of still being
alive. Ten survival algorithms were compared before Cox regression was chosen, including
random survival forests, gradient boosted trees and a neural network; none outperformed it.

## Limitations

External validation rests on 26 disease-related deaths, so calibration is imprecise. With
only 13 deaths from other causes the model for non-cancer mortality could not be
meaningfully validated externally. The recalibration factors were estimated in the same
cohort in which they were assessed and are therefore optimistic. Validation was at a single
European referral center. Neither cohort recorded the Ki-67 index as a continuous value,
chromogranin A, carcinoid syndrome, systemic treatment, or comorbidity.

## Citation

Ricci C, D'Ambra V, Sissa L, Alberici L, Ingaldi C, Malvi D, Fichera M, Lamberti G,
Campana D, Mosconi C & Casadei R. *Predicting cancer-specific death after resection of
jejunoileal neuroendocrine tumors: competing-risks model development in SEER and external
validation.* (under revision)

## Licence

MIT — see `LICENSE`.

## Disclaimer

For research and educational use. This is not a medical device and must not substitute for
clinical judgement. The authors accept no responsibility for decisions taken on the basis of
its output.
