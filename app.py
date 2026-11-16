"""
Jejunoileal NET Risk Calculator — Streamlit application.

Two models are available and the user chooses between them first:
a preoperative model, usable at the first consultation, and a postoperative
model that adds the information contained in the resection specimen.

Run locally:   streamlit run app.py
No patient-level data are used or stored by this application.
"""

from __future__ import annotations

import datetime as _dt

import plotly.graph_objects as go
import streamlit as st

from model import CompetingRisksModel, Patient

st.set_page_config(page_title="Jejunoileal NET Risk Calculator",
                   page_icon="🩺", layout="wide", initial_sidebar_state="expanded")

TEAL, TEAL_DARK = "#0f766e", "#134e4a"
GREEN, CORAL, SLATE, AMBER = "#2a9d8f", "#c2483c", "#94a3b8", "#b45309"
INK = "#1f2937"

st.markdown(f"""
<style>
  .block-container {{ padding-top: 1.5rem; max-width: 1250px; }}
  .hero {{ background: linear-gradient(120deg, {TEAL_DARK} 0%, {TEAL} 55%, #0e7490 100%);
          color:#fff; padding:1.3rem 1.7rem; border-radius:14px; margin-bottom:1rem; }}
  .hero h1 {{ margin:0 0 .3rem 0; font-size:1.58rem; font-weight:700; letter-spacing:-.2px; }}
  .hero p  {{ margin:0; opacity:.93; font-size:.95rem; }}
  .card {{ background:#fff; border:1px solid #e5e7eb; border-left:5px solid {TEAL};
          border-radius:12px; padding:.9rem 1.1rem; height:100%;
          box-shadow:0 1px 3px rgba(15,23,42,.06); }}
  .card .lab {{ font-size:.78rem; text-transform:uppercase; letter-spacing:.06em;
               color:#64748b; font-weight:600; }}
  .card .val {{ font-size:2.2rem; font-weight:700; line-height:1.15; }}
  .card .sub {{ font-size:.82rem; color:#64748b; }}
  .pill {{ display:inline-block; padding:.16rem .62rem; border-radius:999px;
          font-size:.78rem; font-weight:600; }}
  .note {{ background:#f8fafc; border:1px solid #e2e8f0; border-radius:10px;
          padding:.85rem 1.05rem; font-size:.88rem; color:{INK}; }}
  .info {{ background:#f0fdfa; border:1px solid #99f6e4; border-radius:12px;
          padding:1rem 1.2rem; font-size:.88rem; color:#134e4a; }}
  .info h4 {{ margin:0 0 .5rem 0; font-size:1rem; color:{TEAL_DARK}; }}
  .warn {{ background:#fffbeb; border:1px solid #fcd34d; border-radius:10px;
          padding:.85rem 1.05rem; font-size:.88rem; color:#78350f; }}
  .modebox {{ background:#ecfdf5; border:1px solid #6ee7b7; border-radius:10px;
             padding:.6rem .85rem; font-size:.84rem; color:#065f46; margin-bottom:.4rem; }}
  .stTabs [data-baseweb="tab-list"] {{ gap:.35rem; }}
  .stTabs [data-baseweb="tab"] {{ padding:.55rem 1rem; border-radius:9px 9px 0 0; }}
  .stTabs [aria-selected="true"] {{ background:#ecfdf5; color:{TEAL_DARK}; font-weight:650; }}
  table.tidy {{ border-collapse:collapse; width:100%; font-size:.88rem; }}
  table.tidy th, table.tidy td {{ border-bottom:1px solid #e5e7eb; padding:.42rem .55rem; text-align:left; }}
  table.tidy th {{ background:#f1f5f9; font-weight:650; }}
  table.tidy td.num {{ text-align:right; font-variant-numeric:tabular-nums; }}
  .foot {{ text-align:center; color:#64748b; font-size:.83rem; line-height:1.7;
          margin-top:2.2rem; padding-top:1.1rem; border-top:1px solid #e5e7eb; }}
  .foot b {{ color:{TEAL_DARK}; }}
</style>""", unsafe_allow_html=True)


APP_SCHEMA = 2          # deve coincidere con model.SCHEMA


@st.cache_resource
def load(which: str) -> CompetingRisksModel:
    return CompetingRisksModel(which)


def _check_files() -> None:
    """Ferma l'app con un messaggio chiaro se i tre file non sono della stessa versione."""
    import model as _m
    if getattr(_m, "SCHEMA", 1) != APP_SCHEMA:
        st.error(
            "**model.py is out of date.** This app.py needs the two-model version of "
            "model.py (schema %d), but the one found is schema %d. Replace model.py in "
            "the repository and reboot the app."
            % (APP_SCHEMA, getattr(_m, "SCHEMA", 1)))
        st.stop()
    try:
        load("preoperative"); load("postoperative")
    except Exception as exc:                      # file spaiati o json vecchio
        st.error(
            "**The model files do not match.** %s\n\nCheck that app.py, model.py and "
            "model_coefficients.json all come from the same release, delete any "
            "__pycache__ folder from the repository, and reboot the app." % exc)
        st.stop()


THIS_YEAR = _dt.date.today().year

st.markdown("""
<div class="hero">
  <h1>Jejunoileal NET — outcome after intestinal resection</h1>
  <p>What is likely to happen over the next years, before the operation and after it.</p>
</div>""", unsafe_allow_html=True)

# --------------------------------------------------------------------------- #
#  Sidebar — the model comes first
# --------------------------------------------------------------------------- #
sb = st.sidebar
sb.markdown("### 1 · Which model?")
mode = sb.radio(
    "Choose according to the information you have",
    ["Before surgery (preoperative)", "After surgery (postoperative)"],
    index=0, label_visibility="collapsed",
    help="The preoperative model uses only what is known at the first consultation. "
         "The postoperative model adds grade and the nodal findings, which come from "
         "the resection specimen.",
)
PRE = mode.startswith("Before")
_check_files()
MODEL = load("preoperative" if PRE else "postoperative")

sb.markdown(
    f"""<div class="modebox">{'<b>Preoperative.</b> Six variables, available at the first '
    'consultation. It estimates what resection is expected to achieve; it cannot be used to '
    'decide whether to operate.' if PRE else
    '<b>Postoperative.</b> Ten variables, applied once the pathology report is available. '
    'In external validation the two models performed alike.'}</div>""",
    unsafe_allow_html=True)

sb.markdown("### 2 · Patient")
sb.caption("Enter the findings as recorded in the clinical, pathology and operative report.")
age = sb.number_input("Age at diagnosis, years", 18, 100, 62, 1,
                      help="Age when the tumor was diagnosed, not the current age.")
sex = sb.radio("Sex", ["Male", "Female"], horizontal=True)
year = sb.number_input("Year of diagnosis", 2000, THIS_YEAR, min(2023, THIS_YEAR), 1,
                       help="The model was developed on diagnoses from 2000 to 2023. "
                            "Later years extrapolate the calendar-period trend.")

sb.markdown("### 3 · Tumor")
size = sb.number_input(
    "Largest diameter of the primary, mm", 1, 200, 20, 1,
    help="Radiological size before the operation, pathological size afterwards. "
         "If the tumor is multifocal, enter the largest lesion.")
extent = sb.selectbox(
    "Disease extent", ["Localized", "Regional", "Distant"], index=1,
    help="Localized: confined to the bowel wall. Regional: through the wall and/or "
         "regional nodes involved. Distant: metastases beyond the regional field, "
         "liver included.")

grade, n_ex, n_pos = None, None, None
if not PRE:
    sb.markdown("### 4 · Pathology")
    grade = sb.selectbox(
        "Grade (WHO)", ["G1", "G2", "G3"],
        help="G1: Ki-67 below 3%. G2: Ki-67 3–20%. G3: Ki-67 above 20%, well "
             "differentiated. Poorly differentiated neuroendocrine carcinoma is outside "
             "the scope of this model.")
    n_ex = sb.number_input(
        "Lymph nodes examined, n", 0, 90, 12, 1,
        help="Total nodes retrieved and examined. Enter 0 if no lymphadenectomy was "
             "performed: this is a category of its own, not a missing value.")
    n_pos = sb.number_input("Positive lymph nodes, n", 0, 90, 3, 1,
                            help="Of the nodes examined, how many contained tumor.")

sb.markdown(f"### {'4' if PRE else '5'} · Surgery")
metx = sb.checkbox(
    "Surgery to a distant site (metastasectomy)", value=False,
    help="Resection or ablation of a distant metastasis, most often hepatic. "
         "Before the operation, tick it if such a procedure is planned.")

sb.markdown(f"### {'5' if PRE else '6'} · Setting")
setting = sb.radio(
    "Where is the patient treated?",
    ["General surgical practice", "High-volume referral center"],
    help="Patients treated at high-volume referral centers did better than the registry "
         "predicted, so the estimate is adjusted downwards for that setting.")
RECAL = setting.startswith("High-volume")

if (not PRE) and n_pos > n_ex:
    sb.error("Positive nodes cannot exceed the nodes examined.")
    st.stop()
if extent != "Distant" and metx:
    sb.warning("Metastasectomy without distant disease is unusual — check the entry.")

patient = Patient(age=age, year_of_diagnosis=int(year), size_mm=size,
                  female=(sex == "Female"), extent=extent, metastasectomy=metx,
                  grade=grade,
                  nodes_examined=None if PRE else int(n_ex),
                  nodes_positive=None if PRE else int(n_pos))

pred = MODEL.predict(patient, recalibrate=RECAL)
pred_alt = MODEL.predict(patient, recalibrate=not RECAL)

# --------------------------------------------------------------------------- #
tab_risk, tab_model, tab_help, tab_about = st.tabs(
    ["  Result  ", "  Models and validation  ", "  How to enter the data  ", "  About  "])

# =============================== 1. RESULT ================================== #
with tab_risk:
    c_mode, c_hor = st.columns([1.15, 2])
    c_mode.markdown(
        f"""<div style="padding:.45rem 0"><span class="pill"
        style="background:{TEAL}1f;color:{TEAL_DARK}">{MODEL.label}</span></div>""",
        unsafe_allow_html=True)
    with c_hor:
        horizon = st.radio("Time horizon since diagnosis", [36, 60, 120],
                           format_func=lambda m: f"{m // 12} years", index=1,
                           horizontal=True)

    r = MODEL.at(pred, horizon)
    r_alt = MODEL.at(pred_alt, horizon)
    group = MODEL.risk_group(patient)
    gcol = {"lower third": GREEN, "middle third": AMBER, "upper third": CORAL}[group]
    yrs = horizon // 12

    c1, c2, c3 = st.columns(3)
    for col, lab, val, sub, colour in [
        (c1, "Alive", r["alive"], f"free of both events at {yrs} years", GREEN),
        (c2, "Disease-related death", r["cancer"], "death from the tumor", CORAL),
        (c3, "Non-disease-related death", r["other"], "death from another cause", SLATE),
    ]:
        col.markdown(f"""<div class="card" style="border-left-color:{colour}">
              <div class="lab">{lab}</div>
              <div class="val" style="color:{colour}">{val:.1f}%</div>
              <div class="sub">{sub}</div></div>""", unsafe_allow_html=True)

    other_lab = "a general surgical practice" if RECAL else "a high-volume referral center"
    st.markdown(f"""<div class="note" style="margin-top:.9rem">
        Out of 100 patients like this one, about <b>{r['alive']:.0f}</b> are expected to be
        alive {yrs} years after diagnosis. The three figures cover every possibility and add
        up to 100%. Compared with the development cohort, this patient sits in the
        <span class="pill" style="background:{gcol}22;color:{gcol}">{group}</span> of predicted risk.
        <br><br><span style="color:#64748b">Setting selected: <b>{setting.lower()}</b>. In
        {other_lab} the disease-related figure would be {r_alt['cancer']:.1f}% instead of
        {r['cancer']:.1f}%. The choice of setting rescales the risk but does not change the
        ranking of patients.</span></div>""", unsafe_allow_html=True)

    st.markdown("#### What happens over ten years")
    t = pred["times"]; keep = t <= 120
    fig = go.Figure()
    for name, series, colour in [("Alive", pred["alive"], GREEN),
                                 ("Non-disease-related death", pred["other"], SLATE),
                                 ("Disease-related death", pred["cancer"], CORAL)]:
        fig.add_trace(go.Scatter(x=t[keep], y=100 * series[keep], name=name, mode="lines",
                                 stackgroup="one", line=dict(width=0.6, color=colour),
                                 fillcolor=colour,
                                 hovertemplate="%{y:.1f}%<extra>" + name + "</extra>"))
    fig.add_vline(x=horizon, line_dash="dot", line_color="#334155")
    fig.update_layout(height=360, margin=dict(l=10, r=10, t=10, b=10),
                      xaxis_title="Months since diagnosis", yaxis_title="Probability (%)",
                      yaxis_range=[0, 100], hovermode="x unified", plot_bgcolor="white",
                      legend=dict(orientation="h", y=-0.22))
    fig.update_xaxes(gridcolor="#eef2f7"); fig.update_yaxes(gridcolor="#eef2f7")
    st.plotly_chart(fig, width="stretch")

    st.markdown(f"""
    <div class="info">
    <h4>🧠 Model information</h4>
    This tool was developed on <b>2,496 patients</b> with a resected jejunoileal
    neuroendocrine tumor extracted from the <b>SEER</b> database (Surveillance, Epidemiology
    and End Results; 17 registries, 2000–2023), and was <b>externally validated</b> in an
    independent cohort of <b>261 consecutively resected patients</b> at the University of
    Bologna. It combines two cause-specific Cox proportional hazards models, one for death
    from the tumor and one for death from any other cause, into a cumulative incidence, so
    that the probability of dying of the tumor is estimated in a setting where the patient
    may also die of something else.
    <br><br>
    <b>Two models are provided.</b> The <b>preoperative</b> model uses the six variables
    available at the first consultation: age, sex, year of diagnosis, tumor size, disease
    extent and metastasectomy. The <b>postoperative</b> model adds grade, nodal status and
    the two nodal counts, which come from the resection specimen. On external validation the
    two were indistinguishable, with concordance indices of 0.823 and 0.817 and a paired
    difference of +0.006 (95% CI −0.025 to +0.042): most of what the model knows is already
    available before the operation.
    <br><br>
    <b>Notes.</b>
    <ul style="margin:.35rem 0 0 1rem; padding:0">
      <li>Typical resection includes segmental small-bowel resection, ileocaecal resection
          and right hemicolectomy. Polypectomy, local excision and local destruction are
          outside the scope of the model.</li>
      <li>Ten survival algorithms were compared before Cox regression was chosen, including
          penalized Cox, a random survival forest, gradient boosted trees and a neural
          network. <b>None outperformed ordinary Cox regression</b> (cross-validated
          C-index 0.775 against 0.777 for the best alternative).</li>
      <li>Discrimination was <b>C-index 0.775</b> in internal cross-validation and
          <b>0.817 (95% CI 0.744–0.882)</b> on external validation for the postoperative
          model; time-dependent AUC was 0.837 at 3 years and 0.820 at 5 years.</li>
      <li>Calibration slope on external validation was 1.18, but absolute risk was
          overpredicted (observed/expected 0.59), which is why the setting selector exists.</li>
      <li>Of the 26 disease-related deaths in the validation cohort, <b>20 occurred in the
          highest predicted-risk third</b> of the postoperative model and 23 of the
          preoperative model.</li>
    </ul></div>""", unsafe_allow_html=True)

    with st.expander("Why this is not simply one minus the survival curve"):
        gap = r["naive_cancer"] - r["cancer"]
        f2 = go.Figure()
        f2.add_trace(go.Scatter(x=t[keep], y=100 * pred["naive_cancer"][keep],
                                name="Conventional calculation", mode="lines",
                                line=dict(color=SLATE, dash="dash", width=2.4)))
        f2.add_trace(go.Scatter(x=t[keep], y=100 * pred["cancer"][keep], name="This model",
                                mode="lines", line=dict(color=CORAL, width=2.8)))
        f2.update_layout(height=300, margin=dict(l=10, r=10, t=10, b=10),
                         xaxis_title="Months since diagnosis",
                         yaxis_title="Disease-related death (%)", plot_bgcolor="white",
                         hovermode="x unified", legend=dict(orientation="h", y=-0.28))
        f2.update_xaxes(gridcolor="#eef2f7"); f2.update_yaxes(gridcolor="#eef2f7")
        st.plotly_chart(f2, width="stretch")
        st.markdown(f"""
Most prognostic tools treat death from other causes as if those patients were simply lost to
follow-up. That answers a different question, namely the risk of dying of this tumor if
nothing else could kill the patient, and it always gives too high a number, the more so the
older the patient and the longer the horizon.

For this patient at {yrs} years the conventional calculation gives
**{r['naive_cancer']:.1f}%** against **{r['cancer']:.1f}%** here, a difference of
**{gap:.1f} percentage points**.""")

    st.markdown("""<div class="warn" style="margin-top:.9rem">
        <b>How much weight to give the number.</b> External validation rests on 26
        disease-related deaths, so these percentages are an order of magnitude and not a
        precise figure. What the model does well is <i>rank</i> patients. Use it to decide
        how closely someone should be followed and what to say at the first consultation
        and at the first postoperative visit, not to choose treatment. In particular, the
        preoperative model estimates what is expected to happen <i>after</i> a resection:
        it was developed only in patients who were operated on and cannot be used to decide
        whether to operate.</div>""", unsafe_allow_html=True)

# ========================= 2. MODELS AND VALIDATION ========================= #
with tab_model:
    c1, c2 = st.columns(2)
    c1.markdown(f"""<div class="card">
        <div class="lab">Development</div>
        <div class="val" style="color:{TEAL_DARK};font-size:1.45rem">SEER, 17 registries</div>
        <div class="sub">2,496 patients · 334 disease-related deaths · 350 from other causes ·
        median follow-up 73 months</div></div>""", unsafe_allow_html=True)
    c2.markdown(f"""<div class="card" style="border-left-color:{AMBER}">
        <div class="lab">External validation</div>
        <div class="val" style="color:{AMBER};font-size:1.45rem">University of Bologna</div>
        <div class="sub">261 patients · 26 disease-related deaths · 13 from other causes ·
        median follow-up 43 months</div></div>""", unsafe_allow_html=True)

    st.markdown("#### The two models side by side")
    st.markdown("""<table class="tidy">
      <tr><th></th><th class="num">Preoperative</th><th class="num">Postoperative</th><th class="num">Difference</th></tr>
      <tr><td>Variables required</td><td class="num">6</td><td class="num">10</td><td class="num">—</td></tr>
      <tr><td>Estimated parameters</td><td class="num">7</td><td class="num">13</td><td class="num">—</td></tr>
      <tr><td>Cross-validated C-index</td><td class="num">0.772</td><td class="num">0.777</td><td class="num">−0.005</td></tr>
      <tr><td>External C-index</td><td class="num">0.823</td><td class="num">0.817</td><td class="num">+0.006</td></tr>
      <tr><td>External Uno C-index</td><td class="num">0.794</td><td class="num">0.787</td><td class="num">+0.007</td></tr>
      <tr><td>Time-dependent AUC, 3 years</td><td class="num">0.850</td><td class="num">0.837</td><td class="num">+0.013</td></tr>
      <tr><td>Calibration slope</td><td class="num">1.21</td><td class="num">1.18</td><td class="num">+0.03</td></tr>
      <tr><td>Observed/expected, 5 years</td><td class="num">0.62</td><td class="num">0.59</td><td class="num">+0.03</td></tr>
      <tr><td>Deaths in the highest risk third, of 26</td><td class="num">23</td><td class="num">20</td><td class="num">+3</td></tr>
      <tr><td>Deaths in the lowest risk third, of 26</td><td class="num">0</td><td class="num">1</td><td class="num">−1</td></tr>
    </table>
    <div style="font-size:.84rem;color:#64748b;margin-top:.6rem">
    The comparison used identical cross-validation partitions and identical bootstrap
    resamples of the validation cohort. The paired difference in external discrimination was
    +0.006, with a bootstrap interval from −0.025 to +0.042: the two models are
    indistinguishable. Grade and the nodal variables therefore add almost nothing once age,
    sex, calendar period, tumor size and disease extent are known.</div>""",
                unsafe_allow_html=True)

    st.markdown("#### The two cohorts are not alike, and that is the point")
    st.markdown("""<table class="tidy">
      <tr><th>Characteristic</th><th class="num">SEER (n = 2,496)</th><th class="num">Bologna (n = 261)</th></tr>
      <tr><td>Male</td><td class="num">52.4%</td><td class="num">60.2%</td></tr>
      <tr><td>Age, median</td><td class="num">60</td><td class="num">62</td></tr>
      <tr><td>Grade G2</td><td class="num">21.7%</td><td class="num">40.2%</td></tr>
      <tr><td>Tumor size, median mm</td><td class="num">18</td><td class="num">18</td></tr>
      <tr><td>Localized disease</td><td class="num">17.0%</td><td class="num">6.2%</td></tr>
      <tr><td>Regional disease</td><td class="num">59.3%</td><td class="num">45.1%</td></tr>
      <tr><td>Distant disease</td><td class="num">23.7%</td><td class="num">48.7%</td></tr>
      <tr><td>Nodes examined, median</td><td class="num">12</td><td class="num">9</td></tr>
      <tr><td>Metastasectomy, among those with distant disease</td><td class="num">31.5%</td><td class="num">52.8%</td></tr>
    </table>
    <div class="note" style="margin-top:.8rem">At the referral center, resection of the
    primary tumor was offered as a matter of policy to every patient fit for surgery,
    including those with distant metastases and irrespective of symptoms; liver surgery was
    reserved for selected patients discussed at the multidisciplinary board. That policy
    explains most of the difference in case mix. A model that keeps its discrimination
    across cohorts that differ this much has been tested properly.</div>""",
                unsafe_allow_html=True)

# ========================= 3. HOW TO ENTER THE DATA ========================= #
with tab_help:
    st.markdown("#### Choosing the model")
    st.markdown("""
**Before surgery (preoperative).** Use it at the first consultation, when the diagnosis is
made but the specimen does not yet exist. It asks for six variables and estimates what a
resection is expected to achieve. It does **not** tell you whether to operate: it was
developed only in patients who underwent resection, so a patient for whom surgery is being
withheld is not represented in the data behind it.

**After surgery (postoperative).** Use it at the first postoperative visit, once the
pathology report is available. It adds grade, nodal status and the two nodal counts. In
external validation it performed no better than the preoperative model, which is itself a
result worth knowing.
""")
    st.markdown("#### Field by field")
    st.markdown("""
**Age at diagnosis** — age when the tumor was diagnosed, not the age today. After disease
extent this is the strongest predictor, and it also drives the risk of dying of something else.

**Year of diagnosis** — the model was fitted on 2000–2023 and carries a calendar-period
effect: risk falls about 4% per later year of diagnosis, reflecting stage migration and
improving therapy. A year after 2023 extrapolates that trend.

**Largest diameter of the primary** — in millimetres. Before the operation this comes from
imaging, afterwards from the pathology report; the model was fitted on pathological
measurements, so the preoperative figure is slightly less precise. If the tumor is
multifocal, as jejunoileal NETs often are, enter the largest lesion.

**Disease extent** — the single most important field. *Localized*: confined to the bowel
wall, no nodal or distant involvement. *Regional*: extension beyond the wall and/or regional
lymph nodes involved. *Distant*: metastases beyond the regional nodal field, hepatic
metastases included.

**Metastasectomy** — tick if a distant metastasis, usually hepatic, was resected or ablated,
or if such a procedure is planned. The registry records whether the procedure was performed
but not its extent, so this variable says nothing about the completeness of cytoreduction.

**Grade** *(postoperative only)* — the WHO classification, from the Ki-67 index: G1 below
3%, G2 from 3 to 20%, G3 above 20% while still well differentiated. Poorly differentiated
neuroendocrine carcinoma is a different disease and is outside the scope of this model.

**Lymph nodes examined** *(postoperative only)* — the total retrieved and examined by the
pathologist. Enter **0** if no lymphadenectomy was performed. Zero is not a missing value
here: a patient in whom no node was removed has not been shown to be node negative, and the
model treats that as a category of its own.

**Positive lymph nodes** *(postoperative only)* — of those examined, how many contained
tumor. Cannot exceed the number examined.

**Setting** — choose *high-volume referral center* if liver surgery, somatostatin analogues
and peptide receptor radionuclide therapy are part of routine practice where the patient is
treated. In the validation cohort, treated in exactly that setting, the observed risk was
about 40% lower than the registry predicted.
""")
    st.markdown("""<div class="warn">
        <b>Who this model does not apply to.</b> Patients who did not undergo an intestinal
        resection; those treated by polypectomy or local excision alone; poorly
        differentiated neuroendocrine carcinoma; goblet cell and mixed tumors; primary sites
        other than jejunum and ileum. The model is applied once, and is not designed to be
        updated as follow-up accrues.</div>""", unsafe_allow_html=True)

# =============================== 4. ABOUT =================================== #
with tab_about:
    st.markdown(f"""
#### About this calculator

This application contains the coefficients of both models, their baseline cumulative hazards
and their recalibration factors — **no patient-level data**. Nothing entered here is
transmitted or stored.

**Model version** {MODEL.version} · **Development cohort** {MODEL.cohort}

##### Citation
Ricci C, D'Ambra V, Sissa L, Alberici L, Ingaldi C, Malvi D, Fichera M, Lamberti G,
Campana D, Mosconi C & Casadei R. *Predicting cancer-specific death after resection of
jejunoileal neuroendocrine tumors: competing-risks model development in SEER and external
validation.* (under revision)

##### Limitations
- External validation rests on **26 disease-related deaths**. Calibration is imprecise; the
  confidence interval of the calibration slope runs from 0.67 to 1.69.
- With only **13 deaths from other causes**, the model for non-cancer mortality could not be
  meaningfully validated externally. The probability of death from another cause reported
  here should be regarded as transported from SEER rather than confirmed.
- The adjustment applied in the referral-center setting was estimated in the same cohort in
  which it was assessed, so it is optimistic and needs confirmation elsewhere.
- Deaths in patients with distant disease were classified as cancer-specific even when
  recurrence was not documented, and distant disease is also the strongest predictor; the
  two are not independent.
- Neither cohort recorded the Ki-67 index as a continuous value, chromogranin A, carcinoid
  syndrome, mesenteric involvement, systemic treatment, or **comorbidity**.

##### Intended use
Counseling and planning the intensity of follow-up. **Not** for selecting treatment and
**not** for deciding whether to operate.

##### Disclaimer
For research and educational use. This is not a medical device and must not substitute for
clinical judgement. The authors accept no responsibility for decisions taken on the basis of
its output.
""")

st.markdown("""
<div class="foot">
  <b>Developed by Claudio Ricci, MD, PhD</b><br>
  Associate Professor of Surgery — University of Bologna<br>
  IRCCS Azienda Ospedaliero–Universitaria di Bologna (S. Orsola–Malpighi Hospital)<br>
  © 2026 — For research and educational purposes only. · app v2.0
</div>""", unsafe_allow_html=True)
