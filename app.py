"""
Jejunoileal NET Risk Calculator — Streamlit application.

Absolute risk of death from the tumor after intestinal resection for a
jejunoileal neuroendocrine tumor, estimated in the presence of death from
other causes.

Run locally:   streamlit run app.py
No patient-level data are used or stored by this application.
"""

from __future__ import annotations

import datetime as _dt

import numpy as np
import plotly.graph_objects as go
import streamlit as st

from model import CompetingRisksModel, Patient

# --------------------------------------------------------------------------- #
#  Page setup and palette
# --------------------------------------------------------------------------- #
st.set_page_config(
    page_title="Jejunoileal NET Risk Calculator",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="expanded",
)

TEAL = "#0f766e"
TEAL_DARK = "#134e4a"
CORAL = "#c2483c"      # death from the tumor
SLATE = "#94a3b8"      # death from other causes
GREEN = "#2a9d8f"      # alive
AMBER = "#b45309"
INK = "#1f2937"

st.markdown(
    f"""
    <style>
      .block-container {{ padding-top: 1.6rem; max-width: 1250px; }}
      .hero {{
        background: linear-gradient(120deg, {TEAL_DARK} 0%, {TEAL} 55%, #0e7490 100%);
        color: #ffffff; padding: 1.4rem 1.7rem; border-radius: 14px; margin-bottom: 1.2rem;
      }}
      .hero h1 {{ margin: 0 0 .3rem 0; font-size: 1.62rem; font-weight: 700; letter-spacing:-.2px; }}
      .hero p  {{ margin: 0; opacity: .93; font-size: .96rem; }}
      .card {{
        background: #ffffff; border: 1px solid #e5e7eb; border-left: 5px solid {TEAL};
        border-radius: 12px; padding: .9rem 1.1rem; height: 100%;
        box-shadow: 0 1px 3px rgba(15,23,42,.06);
      }}
      .card .lab {{ font-size: .78rem; text-transform: uppercase; letter-spacing: .06em;
                    color: #64748b; font-weight: 600; }}
      .card .val {{ font-size: 2.05rem; font-weight: 700; line-height: 1.15; }}
      .card .sub {{ font-size: .82rem; color: #64748b; }}
      .pill {{ display:inline-block; padding:.16rem .62rem; border-radius: 999px;
               font-size:.78rem; font-weight:600; }}
      .note {{ background:#f8fafc; border:1px solid #e2e8f0; border-radius:10px;
               padding:.8rem 1rem; font-size:.88rem; color:{INK}; }}
      .warn {{ background:#fffbeb; border:1px solid #fcd34d; border-radius:10px;
               padding:.8rem 1rem; font-size:.88rem; color:#78350f; }}
      .stTabs [data-baseweb="tab-list"] {{ gap: .35rem; }}
      .stTabs [data-baseweb="tab"] {{ padding: .55rem 1rem; border-radius: 9px 9px 0 0; }}
      .stTabs [aria-selected="true"] {{ background: #ecfdf5; color: {TEAL_DARK}; font-weight: 650; }}
      table.tidy {{ border-collapse: collapse; width: 100%; font-size: .88rem; }}
      table.tidy th, table.tidy td {{ border-bottom: 1px solid #e5e7eb; padding: .42rem .55rem;
                                      text-align: left; }}
      table.tidy th {{ background:#f1f5f9; font-weight:650; }}
      table.tidy td.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource
def load_model() -> CompetingRisksModel:
    return CompetingRisksModel()


MODEL = load_model()
THIS_YEAR = _dt.date.today().year

st.markdown(
    """
    <div class="hero">
      <h1>Jejunoileal NET — risk of death from the tumor after resection</h1>
      <p>Absolute risk estimated in the presence of death from other causes, from ten
         variables available at the first postoperative visit.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# --------------------------------------------------------------------------- #
#  Sidebar: the patient
# --------------------------------------------------------------------------- #
sb = st.sidebar
sb.markdown("### Patient")
sb.caption("Enter the findings as recorded in the pathology and operative report.")

age = sb.number_input(
    "Age at diagnosis, years", 18, 100, 62, 1,
    help="Age when the tumor was diagnosed, not the current age.",
)
sex = sb.radio("Sex", ["Male", "Female"], horizontal=True)
year = sb.number_input(
    "Year of diagnosis", 2000, THIS_YEAR, min(2023, THIS_YEAR), 1,
    help="The model was developed on diagnoses from 2000 to 2023. Later years are "
         "an extrapolation of the calendar-period trend.",
)

sb.markdown("### Tumor")
size = sb.number_input(
    "Largest diameter of the primary, mm", 1, 200, 20, 1,
    help="Pathological size of the primary tumor. If several tumors are present, "
         "enter the largest.",
)
grade = sb.selectbox(
    "Grade (WHO)", ["G1", "G2", "G3"],
    help="G1: Ki-67 < 3%. G2: Ki-67 3–20%. G3: Ki-67 > 20%, well differentiated. "
         "Poorly differentiated neuroendocrine carcinoma is outside the scope of this model.",
)
extent = sb.selectbox(
    "Disease extent", ["Localized", "Regional", "Distant"],
    index=1,
    help="Localized: confined to the bowel wall. Regional: through the wall and/or "
         "regional nodes involved. Distant: metastases beyond the regional field, "
         "liver included.",
)

sb.markdown("### Lymph nodes")
n_ex = sb.number_input(
    "Lymph nodes examined, n", 0, 90, 12, 1,
    help="Total nodes retrieved and examined. Enter 0 if no lymphadenectomy was "
         "performed — this is treated as its own category, not as missing data.",
)
n_pos = sb.number_input(
    "Positive lymph nodes, n", 0, 90, 3, 1,
    help="Number of examined nodes containing tumor. Cannot exceed the number examined.",
)

sb.markdown("### Surgery")
metx = sb.checkbox(
    "Surgery to a distant site (metastasectomy)",
    value=False,
    help="Resection or ablation of a distant metastasis, most often hepatic, at the "
         "same time as or in addition to the intestinal resection.",
)

if n_pos > n_ex:
    sb.error("Positive nodes cannot exceed the nodes examined.")
    st.stop()
if extent != "Distant" and metx:
    sb.warning("Metastasectomy without distant disease is unusual — check the entry.")

patient = Patient(
    age=age,
    year_of_diagnosis=int(year),
    size_mm=size,
    nodes_examined=int(n_ex),
    nodes_positive=int(n_pos),
    female=(sex == "Female"),
    grade=grade,
    extent=extent,
    metastasectomy=metx,
)

pred = MODEL.predict(patient, recalibrate=False)
pred_rc = MODEL.predict(patient, recalibrate=True)

# --------------------------------------------------------------------------- #
tab_risk, tab_model, tab_cohorts, tab_help, tab_about = st.tabs(
    ["  Risk  ", "  The model  ", "  Cohorts  ", "  How to enter the data  ", "  About  "]
)

# =========================== 1. RISK ======================================== #
with tab_risk:
    horizon = st.radio(
        "Time horizon since diagnosis",
        [36, 60, 120],
        format_func=lambda m: f"{m // 12} years",
        index=1,
        horizontal=True,
    )
    r = MODEL.at(pred, horizon)
    r_rc = MODEL.at(pred_rc, horizon)
    group = MODEL.risk_group(patient)
    gcol = {"lower third": GREEN, "middle third": AMBER, "upper third": CORAL}[group]

    c1, c2, c3 = st.columns(3)
    for col, lab, val, sub, colour in [
        (c1, "Death from the tumor", r["cancer"],
         "the event this model predicts", CORAL),
        (c2, "Death from other causes", r["other"],
         "competing mortality", SLATE),
        (c3, "Alive", r["alive"],
         "neither event has occurred", GREEN),
    ]:
        col.markdown(
            f"""<div class="card" style="border-left-color:{colour}">
                  <div class="lab">{lab}</div>
                  <div class="val" style="color:{colour}">{val:.1f}%</div>
                  <div class="sub">{sub}</div>
                </div>""",
            unsafe_allow_html=True,
        )

    st.markdown(
        f"""<div class="note" style="margin-top:.9rem">
        The three figures partition this patient's next {horizon // 12} years and sum to 100%.
        Predicted risk places this patient in the
        <span class="pill" style="background:{gcol}22;color:{gcol}">{group}</span>
        of the SEER development cohort. In external validation, 20 of the 26 deaths from
        the tumor occurred in the upper third and one in the lower third.
        </div>""",
        unsafe_allow_html=True,
    )

    # ---- two calibrations, side by side ---------------------------------- #
    st.markdown("#### Which calibration applies to your patients?")
    k1, k2 = st.columns(2)
    k1.markdown(
        f"""<div class="card">
              <div class="lab">SEER registry calibration</div>
              <div class="val" style="color:{TEAL_DARK}">{r['cancer']:.1f}%</div>
              <div class="sub">Population-based, unselected surgical practice across
              17 US registries.</div>
            </div>""",
        unsafe_allow_html=True,
    )
    k2.markdown(
        f"""<div class="card" style="border-left-color:{AMBER}">
              <div class="lab">Referral-center calibration (× {MODEL.kappa:.2f})</div>
              <div class="val" style="color:{AMBER}">{r_rc['cancer']:.1f}%</div>
              <div class="sub">Observed risk in a European high-volume referral cohort
              was about 40% lower than the registry prediction.</div>
            </div>""",
        unsafe_allow_html=True,
    )
    st.markdown(
        """<div class="note" style="margin-top:.7rem">
        The two differ only by a single multiplicative factor, so the ranking of patients —
        and therefore the discrimination of the model — is identical. Use the registry
        figure for a general surgical population. The recalibrated figure is the better
        guide if your practice resembles a high-volume referral center where
        metastasectomy, somatostatin analogues and peptide receptor radionuclide therapy
        are routine. The recalibration factor was estimated in a single cohort of 261
        patients and has not been confirmed elsewhere.
        </div>""",
        unsafe_allow_html=True,
    )

    # ---- trajectory ------------------------------------------------------- #
    st.markdown("#### Trajectory over ten years")
    t = pred["times"]
    keep = t <= 120
    fig = go.Figure()
    for name, series, colour in [
        ("Alive", pred["alive"], GREEN),
        ("Death from other causes", pred["other"], SLATE),
        ("Death from the tumor", pred["cancer"], CORAL),
    ]:
        fig.add_trace(
            go.Scatter(
                x=t[keep], y=100 * series[keep], name=name, mode="lines",
                stackgroup="one", line=dict(width=0.6, color=colour),
                fillcolor=colour, hovertemplate="%{y:.1f}%<extra>" + name + "</extra>",
            )
        )
    fig.add_vline(x=horizon, line_dash="dot", line_color="#334155")
    fig.update_layout(
        height=380, margin=dict(l=10, r=10, t=10, b=10),
        xaxis_title="Months since diagnosis", yaxis_title="Probability (%)",
        yaxis_range=[0, 100], hovermode="x unified", plot_bgcolor="white",
        legend=dict(orientation="h", y=-0.22),
    )
    fig.update_xaxes(gridcolor="#eef2f7"); fig.update_yaxes(gridcolor="#eef2f7")
    st.plotly_chart(fig, width='stretch')

    # ---- why competing risks matter --------------------------------------- #
    gap = r["naive_cancer"] - r["cancer"]
    with st.expander("Why this is not one minus the survival curve"):
        f2 = go.Figure()
        f2.add_trace(go.Scatter(x=t[keep], y=100 * pred["naive_cancer"][keep],
                                name="Conventional (1 − survival)", mode="lines",
                                line=dict(color=SLATE, dash="dash", width=2.4)))
        f2.add_trace(go.Scatter(x=t[keep], y=100 * pred["cancer"][keep],
                                name="Cumulative incidence (this model)", mode="lines",
                                line=dict(color=CORAL, width=2.8)))
        f2.update_layout(height=320, margin=dict(l=10, r=10, t=10, b=10),
                         xaxis_title="Months since diagnosis",
                         yaxis_title="Probability of death from the tumor (%)",
                         plot_bgcolor="white", hovermode="x unified",
                         legend=dict(orientation="h", y=-0.25))
        f2.update_xaxes(gridcolor="#eef2f7"); f2.update_yaxes(gridcolor="#eef2f7")
        st.plotly_chart(f2, width='stretch')
        st.markdown(
            f"""
Treating death from other causes as censoring — what the Kaplan–Meier estimator and most
registry nomograms do — answers the question *what is the probability of dying of this
tumor in a world where nothing else can kill this patient*. It always overstates the risk,
and the overstatement grows with age and with time.

For this patient at {horizon // 12} years the conventional method gives
**{r['naive_cancer']:.1f}%** against **{r['cancer']:.1f}%**, a difference of
**{gap:.1f} percentage points**. In the validation cohort the gap reached 20% in relative
terms at ten years in the oldest third of patients.
            """
        )

    st.markdown(
        """<div class="warn" style="margin-top:.9rem">
        <b>How much confidence to place in the number.</b> External validation rests on
        26 deaths from the tumor, so calibration is estimated imprecisely and these
        percentages should be read as an order of magnitude, not to the decimal. The model
        ranks patients well — a concordance index of 0.82 externally — and it is that
        ranking, more than the absolute figure, that should inform how closely a patient
        is followed. This tool supports counseling and follow-up planning. It does not
        select treatment, and no threshold of predicted risk should be used to withhold
        or offer any therapy.
        </div>""",
        unsafe_allow_html=True,
    )

# =========================== 2. THE MODEL =================================== #
with tab_model:
    st.markdown("#### What the model is")
    st.markdown(
        """
Two cause-specific Cox proportional hazards models are fitted to the same ten predictors:
one for death from the index cancer, one for death from any other cause. Their baseline
cumulative hazards are combined into a cumulative incidence function, so that the
probability of dying of the tumor is estimated in a world where the patient can also die
of something else.

Ten survival algorithms were compared before this model was chosen — penalized Cox
regression in three forms, a flexible parametric model, componentwise boosting, a survival
support vector machine, a random survival forest, gradient boosted trees and a neural
network. **None outperformed ordinary Cox regression.**
        """
    )

    c1, c2 = st.columns(2)
    c1.markdown(
        """<table class="tidy">
        <tr><th>Algorithm</th><th class="num">Cross-validated C</th></tr>
        <tr><td>Survival support vector machine</td><td class="num">0.777</td></tr>
        <tr><td>Ridge Cox</td><td class="num">0.777</td></tr>
        <tr><td><b>Cox proportional hazards</b></td><td class="num"><b>0.775</b></td></tr>
        <tr><td>Lasso Cox</td><td class="num">0.775</td></tr>
        <tr><td>Elastic net Cox</td><td class="num">0.775</td></tr>
        <tr><td>Flexible parametric</td><td class="num">0.773</td></tr>
        <tr><td>Gradient boosted trees</td><td class="num">0.772</td></tr>
        <tr><td>Random survival forest</td><td class="num">0.768</td></tr>
        <tr><td>Componentwise boosted Cox</td><td class="num">0.764</td></tr>
        <tr><td>Neural network (DeepSurv)</td><td class="num">0.747</td></tr>
        </table>""",
        unsafe_allow_html=True,
    )
    c2.markdown(
        """<table class="tidy">
        <tr><th>Performance</th><th class="num">Development</th><th class="num">External</th></tr>
        <tr><td>Harrell C-index</td><td class="num">0.775</td><td class="num">0.817</td></tr>
        <tr><td>Uno C-index</td><td class="num">0.779</td><td class="num">0.787</td></tr>
        <tr><td>Time-dependent AUC, 3 y</td><td class="num">0.785</td><td class="num">0.837</td></tr>
        <tr><td>Time-dependent AUC, 5 y</td><td class="num">0.784</td><td class="num">0.820</td></tr>
        <tr><td>Calibration slope</td><td class="num">1 (ref)</td><td class="num">1.18</td></tr>
        <tr><td>Observed / expected, 5 y</td><td class="num">—</td><td class="num">0.59</td></tr>
        <tr><td>Integrated Brier score</td><td class="num">0.069</td><td class="num">0.025</td></tr>
        </table>
        <div class="sub" style="margin-top:.5rem;font-size:.82rem;color:#64748b">
        Discrimination is higher externally because the validation cohort spans a wider
        range of disease extent; discrimination rises with case-mix heterogeneity.</div>""",
        unsafe_allow_html=True,
    )

    st.markdown("#### The ten predictors")
    st.markdown(
        """<table class="tidy">
        <tr><th>Predictor</th><th class="num">Multivariable HR (95% CI)</th><th class="num">P</th></tr>
        <tr><td>Age, per year</td><td class="num">1.05 (1.04–1.06)</td><td class="num">&lt;0.001</td></tr>
        <tr><td>Female sex</td><td class="num">1.35 (1.09–1.69)</td><td class="num">0.007</td></tr>
        <tr><td>Year of diagnosis, per year</td><td class="num">0.96 (0.94–0.99)</td><td class="num">&lt;0.001</td></tr>
        <tr><td>Grade G2 (vs G1)</td><td class="num">1.27 (0.84–1.92)</td><td class="num">0.257</td></tr>
        <tr><td>Grade G3 (vs G1)</td><td class="num">1.59 (0.78–3.23)</td><td class="num">0.197</td></tr>
        <tr><td>Tumor size, per mm</td><td class="num">1.01 (1.00–1.02)</td><td class="num">0.013</td></tr>
        <tr><td>Regional disease (vs localized)</td><td class="num">2.47 (1.45–4.19)</td><td class="num">&lt;0.001</td></tr>
        <tr><td>Distant disease (vs localized)</td><td class="num">7.37 (4.35–12.49)</td><td class="num">&lt;0.001</td></tr>
        <tr><td>Node positive (vs N0)</td><td class="num">0.71 (0.47–1.06)</td><td class="num">0.094</td></tr>
        <tr><td>Nodes not examined (vs N0)</td><td class="num">0.83 (0.52–1.31)</td><td class="num">0.422</td></tr>
        <tr><td>Lymph nodes examined, per node</td><td class="num">0.98 (0.96–0.99)</td><td class="num">0.003</td></tr>
        <tr><td>Positive lymph nodes, per node</td><td class="num">1.04 (1.00–1.08)</td><td class="num">0.039</td></tr>
        <tr><td>Metastasectomy</td><td class="num">1.20 (0.87–1.66)</td><td class="num">0.263</td></tr>
        </table>""",
        unsafe_allow_html=True,
    )
    st.markdown(
        """<div class="note" style="margin-top:.8rem">
        Two of these deserve a word. <b>Grade</b> is strongly prognostic on its own
        (G3 versus G1, hazard ratio 4.29) but loses its effect once stage and nodal burden
        are accounted for; the proliferative index of these tumors clusters so tightly at
        the low end that the G1/G2 cut point separates very little.
        <b>Metastasectomy</b> behaves the same way, falling from 2.81 to 1.20. Neither was
        removed, because the predictor set was fixed in advance and discarding a variable
        for failing to predict in the data that defined it is a known source of optimism.
        <br><br>
        Nodal status and the number of positive nodes are collinear by construction — a
        patient classified N0 has zero positive nodes — so the hazard ratio for
        node-positive disease should not be read in isolation from the count.
        </div>""",
        unsafe_allow_html=True,
    )

# =========================== 3. COHORTS ===================================== #
with tab_cohorts:
    st.markdown("#### Where the model comes from")
    c1, c2 = st.columns(2)
    c1.markdown(
        f"""<div class="card">
        <div class="lab">Development</div>
        <div class="val" style="color:{TEAL_DARK};font-size:1.5rem">SEER, 17 registries</div>
        <div class="sub">2,496 patients · 334 deaths from the tumor · 350 from other
        causes · median follow-up 73 months</div></div>""",
        unsafe_allow_html=True,
    )
    c2.markdown(
        f"""<div class="card" style="border-left-color:{AMBER}">
        <div class="lab">External validation</div>
        <div class="val" style="color:{AMBER};font-size:1.5rem">University of Bologna</div>
        <div class="sub">261 patients · 26 deaths from the tumor · 13 from other causes ·
        median follow-up 43 months</div></div>""",
        unsafe_allow_html=True,
    )

    st.markdown("###### Eligibility, identical in both cohorts")
    st.markdown(
        """
- Well-differentiated neuroendocrine tumor of the jejunum or ileum (ICD-O-3 8240, 8241, 8249)
- Diagnosis from 2000 onwards
- **Treated by intestinal resection** — segmental resection through to radical surgery.
  Patients who had no surgery, local destruction, local excision or polypectomy were excluded,
  because the model is meant to be applied after a resection has been performed.
- First or only primary; cases known only from a death certificate or autopsy excluded
        """
    )

    st.markdown("###### The two cohorts are not alike, and that is the point")
    st.markdown(
        """<table class="tidy">
        <tr><th>Characteristic</th><th class="num">SEER (n = 2,496)</th>
            <th class="num">Bologna (n = 261)</th><th class="num">P</th></tr>
        <tr><td>Male</td><td class="num">52.4%</td><td class="num">60.2%</td><td class="num">0.017</td></tr>
        <tr><td>Age, median</td><td class="num">60</td><td class="num">62</td><td class="num">0.089</td></tr>
        <tr><td>Grade G2</td><td class="num">21.7%</td><td class="num">40.2%</td><td class="num">&lt;0.001</td></tr>
        <tr><td>Tumor size, median mm</td><td class="num">18</td><td class="num">18</td><td class="num">0.402</td></tr>
        <tr><td>Localized</td><td class="num">17.0%</td><td class="num">6.2%</td><td class="num" rowspan="3">&lt;0.001</td></tr>
        <tr><td>Regional</td><td class="num">59.3%</td><td class="num">45.1%</td></tr>
        <tr><td>Distant</td><td class="num">23.7%</td><td class="num">48.7%</td></tr>
        <tr><td>Nodes examined, median</td><td class="num">12</td><td class="num">9</td><td class="num">&lt;0.001</td></tr>
        <tr><td>Metastasectomy, of those with distant disease</td>
            <td class="num">31.5%</td><td class="num">52.8%</td><td class="num">—</td></tr>
        </table>""",
        unsafe_allow_html=True,
    )
    st.markdown(
        """<div class="note" style="margin-top:.8rem">
        The validation cohort has twice the proportion of distant disease and is treated far
        more aggressively. A model that survives that much difference in case mix has been
        tested properly. It also explains why absolute risk transported less well than
        relative risk: the ranking of patients held, the level did not.
        </div>""",
        unsafe_allow_html=True,
    )

# =========================== 4. HOW TO ENTER ================================ #
with tab_help:
    st.markdown("#### Field by field")
    st.markdown(
        """
**Age at diagnosis** — age when the tumor was diagnosed, not the age today. Age is the
second strongest predictor after disease extent, and it also drives the competing risk of
death from other causes.

**Sex** — recorded as at diagnosis.

**Year of diagnosis** — the model was fitted on 2000–2023 and includes a calendar-period
effect (risk falls about 4% per year of later diagnosis, reflecting stage migration and
improving therapy). Entering a year after 2023 extrapolates that trend.

**Largest diameter of the primary** — in millimetres, from the pathology report. If the
tumor is multifocal, as jejunoileal NETs often are, enter the largest lesion. Size
contributes little once stage is known: about 11% additional risk per centimetre.

**Grade** — the WHO classification, based on the Ki-67 index: G1 below 3%, G2 from 3 to
20%, G3 above 20% while still well differentiated. Poorly differentiated neuroendocrine
carcinoma is a different disease and is outside the scope of this model. Note that grade
adds almost nothing once stage and nodal burden are known.

**Disease extent** — the single most important field.
*Localized* means confined to the bowel wall with no nodal or distant involvement.
*Regional* means extension beyond the wall and/or involvement of regional lymph nodes.
*Distant* means metastases beyond the regional nodal field, hepatic metastases included.

**Lymph nodes examined** — the total number retrieved and examined by the pathologist.
Enter **0** if no lymphadenectomy was performed. Zero is not a missing value: it is a
recognized category in this model, because a patient in whom no node was removed has not
been shown to be node negative. More nodes examined is associated with lower risk — about
22% lower per ten nodes — which may reflect more accurate staging, more complete surgery,
or both.

**Positive lymph nodes** — of the nodes examined, how many contained tumor. Must not
exceed the number examined. If no node was examined, leave at 0.

**Surgery to a distant site (metastasectomy)** — tick if a distant metastasis, usually
hepatic, was resected or ablated. Conditional on stage this carries no independent
prognostic weight, but it is part of the fitted model and is retained.
        """
    )
    st.markdown(
        """<div class="warn">
        <b>Who this model does not apply to.</b> Patients who did not undergo an intestinal
        resection; those treated by polypectomy or local excision alone; poorly
        differentiated neuroendocrine carcinoma; goblet cell and mixed tumors; primary sites
        other than jejunum and ileum. The model is applied once, at the first postoperative
        visit, and is not designed to be updated as follow-up accrues.
        </div>""",
        unsafe_allow_html=True,
    )

# =========================== 5. ABOUT ======================================= #
with tab_about:
    st.markdown("#### About this calculator")
    st.markdown(
        f"""
This application implements the prediction model described in the accompanying article.
It contains the model coefficients, the two baseline cumulative hazards and the
recalibration factor — **no patient-level data**. Nothing entered here is transmitted or
stored.

**Model version** {MODEL.version} · **Development cohort** {MODEL.cohort}

##### Citation
Ricci C, D'Ambra V, Sissa L, Alberici L, Ingaldi C, Malvi D, Fichera M, Lamberti G,
Campana D, Mosconi C & Casadei R. *Predicting cancer-specific death after resection of
jejunoileal neuroendocrine tumors: competing-risks model development in SEER and external
validation.* (submitted)

##### Limitations, stated plainly
- External validation rests on **26 deaths from the tumor**. Calibration is imprecise;
  the confidence interval of the calibration slope runs from 0.67 to 1.69.
- The recalibration factor of {MODEL.kappa:.2f} was estimated in the same cohort in which
  it was assessed, and is therefore optimistic. It needs confirmation elsewhere.
- Validation was at a single European referral center. Referral centers are not
  representative of surgical practice at large.
- Neither cohort recorded the Ki-67 index as a continuous value, chromogranin A, carcinoid
  syndrome or carcinoid heart disease, mesenteric involvement, or systemic treatment.
- Neither cohort recorded **comorbidity**. That gap falls on the model for death from
  other causes, which is precisely the component for which comorbidity would be the
  natural predictor — so the competing-risk half of this calculator is the weaker half.
- Cause of death is imperfectly classified in registry and institutional data alike.

##### Intended use
Counseling and planning the intensity of follow-up. **Not** for selecting treatment: every
patient to whom this model applies has already undergone resection, and no adjuvant
decision in this disease is currently governed by a threshold of predicted risk.

##### Disclaimer
For research and educational use. This is not a medical device and must not substitute for
clinical judgement. The authors accept no responsibility for decisions taken on the basis
of its output.
        """
    )

st.markdown(
    """<div style="text-align:center;color:#94a3b8;font-size:.8rem;margin-top:2rem">
    Jejunoileal NET Risk Calculator · developed on SEER, externally validated at the
    University of Bologna · no patient data are stored</div>""",
    unsafe_allow_html=True,
)
