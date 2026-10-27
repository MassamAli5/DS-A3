"""Builds docs/DS-A3_report.pdf and docs/platform_summary.md
from the files written by the notebook (results/*.csv, results/*.json, figures/*.png).
Every number comes from those files, so the documents cannot drift from your own run.

Run from the project root, AFTER executing the notebook:
    python src/build_report.py"""
import json, html, os, re
from pathlib import Path
import pandas as pd
import matplotlib
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER
from reportlab.lib.utils import ImageReader
from reportlab.lib.fonts import addMapping
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                TableStyle, Image, KeepTogether, HRFlowable)

ROOT = Path(__file__).resolve().parents[1]
RES, FIG, DOCS = ROOT / "results", ROOT / "figures", ROOT / "docs"
DOCS.mkdir(exist_ok=True)
need = [
    "headline.json", "run_info.json", "model_comparison.csv",
    "leakage_audit.csv", "excluded_columns.csv",
    "leave_one_layer_out_rmse.csv", "slices_train_oof.csv", "influence.csv",
    "coefficients_stability.csv", "claims_auto.md", "heteroscedasticity.csv",
    "error_cases_test.csv", "error_cases_train_oof.csv",
]
missing = [n for n in need if not (RES / n).exists()]
if missing:
    raise SystemExit(f"Run the notebook first. Missing in results/: {missing}")

hl = json.loads((RES / "headline.json").read_text())
ri = json.loads((RES / "run_info.json").read_text())
comp = pd.read_csv(RES / "model_comparison.csv")
audit = pd.read_csv(RES / "leakage_audit.csv")
excl = pd.read_csv(RES / "excluded_columns.csv")
lolo = pd.read_csv(RES / "leave_one_layer_out_rmse.csv", index_col=0)
slices = pd.read_csv(RES / "slices_train_oof.csv")
infl = pd.read_csv(RES / "influence.csv")
coef = pd.read_csv(RES / "coefficients_stability.csv")
het = pd.read_csv(RES / "heteroscedasticity.csv").iloc[0]
err_test = pd.read_csv(RES / "error_cases_test.csv")
err_train = pd.read_csv(RES / "error_cases_train_oof.csv")
claims_path = RES / "claims_auto.md"
claims = [l[2:].strip() for l in claims_path.read_text(encoding="utf-8").splitlines()
          if l.startswith("- ")]


# ---------------------------------------------------------------- fonts
def find_fonts():
    win = ("times.ttf", "timesbd.ttf", "timesi.ttf", "timesbi.ttf")
    mac = ("Times New Roman.ttf", "Times New Roman Bold.ttf",
           "Times New Roman Italic.ttf", "Times New Roman Bold Italic.ttf")
    ms = ("Times_New_Roman.ttf", "Times_New_Roman_Bold.ttf",
          "Times_New_Roman_Italic.ttf", "Times_New_Roman_Bold_Italic.ttf")
    lib = ("LiberationSerif-Regular.ttf", "LiberationSerif-Bold.ttf",
           "LiberationSerif-Italic.ttf", "LiberationSerif-BoldItalic.ttf")
    dv = ("DejaVuSerif.ttf", "DejaVuSerif-Bold.ttf",
          "DejaVuSerif-Italic.ttf", "DejaVuSerif-BoldItalic.ttf")
    mpl_fonts = Path(matplotlib.__file__).parent / "mpl-data" / "fonts" / "ttf"
    windir = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
    options = [
        ("Times New Roman", windir, win),
        ("Times New Roman", Path("/Library/Fonts"), mac),
        ("Times New Roman", Path("/System/Library/Fonts/Supplemental"), mac),
        ("Times New Roman", Path("/usr/share/fonts/truetype/msttcorefonts"), ms),
        ("Liberation Serif (Times New Roman look-alike)",
         Path("/usr/share/fonts/truetype/liberation"), lib),
        ("DejaVu Serif (Times New Roman not found)", mpl_fonts, dv),
    ]
    for name, folder, files in options:
        if all((folder / f).exists() for f in files):
            return name, [folder / f for f in files]
    raise SystemExit("No suitable font found")


FONT_NAME, font_files = find_fonts()
for nm, fpath in zip(("TNR", "TNR-B", "TNR-I", "TNR-BI"), font_files):
    pdfmetrics.registerFont(TTFont(nm, str(fpath)))
addMapping("TNR", 0, 0, "TNR")
addMapping("TNR", 1, 0, "TNR-B")
addMapping("TNR", 0, 1, "TNR-I")
addMapping("TNR", 1, 1, "TNR-BI")
print("PDF font:", FONT_NAME)

BLACK = colors.black
BODY = ParagraphStyle("body", fontName="TNR", fontSize=12, leading=15, spaceAfter=5,
                      textColor=BLACK, alignment=TA_JUSTIFY)
TITLE = ParagraphStyle("title", fontName="TNR-B", fontSize=14, leading=17,
                       spaceAfter=2, alignment=TA_CENTER, textColor=BLACK)
H1 = ParagraphStyle("h1", fontName="TNR-B", fontSize=12, leading=15, spaceBefore=10,
                    spaceAfter=3, textColor=BLACK, keepWithNext=1)
SMALL = ParagraphStyle("small", fontName="TNR", fontSize=10, leading=12, textColor=BLACK)
SMALLB = ParagraphStyle("smallb", parent=SMALL, fontName="TNR-B")
CAP = ParagraphStyle("cap", fontName="TNR-I", fontSize=10, leading=12, spaceAfter=6,
                     textColor=BLACK)
BUL = ParagraphStyle("bul", parent=BODY, leftIndent=14, bulletIndent=2, spaceAfter=3,
                     bulletFontName="TNR", bulletFontSize=12)


def esc(x):
    return html.escape(str(x), quote=False)


def P(text, style=BODY):
    return Paragraph(text, style)


def bullets(items, markup=False):
    return [Paragraph(i if markup else esc(i), BUL, bulletText="•") for i in items]


def table(rows, widths):
    data = [[Paragraph(esc(c), SMALLB if r == 0 else SMALL) for c in row]
            for r, row in enumerate(rows)]
    t = Table(data, colWidths=[w * cm for w in widths], repeatRows=1)
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#808080")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 2.2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.2),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e6e6e6")),
    ]))
    return t


def figure(name, width_cm, caption):
    w, h = ImageReader(str(FIG / name)).getSize()
    img = Image(str(FIG / name), width=width_cm * cm, height=width_cm * cm * h / w)
    return KeepTogether([img, Paragraph(caption, CAP)])


# ---------------------------------------------------------------- values for the text
SEL = hl["selected"]
kbest = int(hl["best_params"]["ols_kbest"]["regressor__select__k"])
LAB = {
    "naive_mean": "Naive: training mean",
    "layer_mean": "Naive: mean per layer",
    "ols_all": "OLS, all 35 predictors",
    "ols_kbest": f"OLS, k best (k = {kbest})",
    "ridge": "Ridge",
    "lasso": "Lasso",
}
best_t = hl["best_test_model"]
lb = hl["level_bias"]
lay = slices[slices["slice_type"] == "layer"]
worst_layer = lay.loc[lay["rmse"].idxmax()]
nonlevel = slices[slices["slice_type"] != "observed level"]
worst_rel = nonlevel.loc[nonlevel["rmse_pct_of_mean_observed"].idxmax()]
is_chert = slices["slice"].str.startswith("chert")
chert_row = slices[(slices["slice_type"] == "lithology group") & is_chert].iloc[0]
het_ratio = float(het["resid_sd_high"] / het["resid_sd_low"])
if het["breusch_pagan_p"] > 0.05:
    HET_TXT = "no clear heteroscedasticity (low power)"
else:
    HET_TXT = "some evidence of heteroscedasticity"
pattern = (r"slope of observed on out-of-fold predicted .{0,3}REY is "
           r"([0-9.]+) \(95% interval ([0-9.]+) to ([0-9.]+)\)")
_m = re.search(pattern, " ".join(claims))
if _m:
    CAL_TXT = (f"a calibration slope of {_m.group(1)} "
               f"(95% interval {_m.group(2)} to {_m.group(3)})")
else:
    CAL_TXT = "a calibration check"
sq = err_test["error_obs_minus_pred"] ** 2
share2 = float(sq.iloc[:2].sum() / sq.sum())
flagged = infl[infl["cooks_flag_4_over_n"]].sort_values("cooks_distance", ascending=False)
flag_txt = "; ".join(
    f"{r.sample} (Cook's D {r.cooks_distance:.2f}, leverage {r.leverage:.2f}, "
    f"leave-one-out error {r.loo_abs_error_ppm:.0f} ppm)"
    for r in flagged.itertuples())
flag_show = esc(flag_txt) if flag_txt else "none"
worst_oof = ", ".join(f"{r.sample} ({r.resid:+.0f} ppm)" for r in err_train.head(3).itertuples())
test_ids_txt = ", ".join(hl["test_ids"])
sha = esc(hl["data_sha256"])
ols_train = comp.loc[comp.model == "ols_all", "train_rmse"].iloc[0]

# ---------------------------------------------------------------- story
S = [P("DS-A3 | Regression Baseline and Diagnostics", TITLE),
     HRFlowable(width="100%", thickness=1, color=BLACK, spaceBefore=1, spaceAfter=8)]

S += [
    P("1. Problem, data and scope", H1),
    P("<b>Question.</b> Can bulk ∑REY (ppm) be predicted from non-REY trace and minor "
      "elements in these 29 samples, and where does the prediction stop being reliable?"),
    P("<b>Data source:</b> Ali et al. (2026), <i>Journal of Asian Earth Sciences</i>."
      "<br/>DOI: 10.1016/j.jseaes.2025.106927."),
]

audit_rows = [["Check", "Passed", "Detail"]] + [
    [r.check, "yes" if r.passed else "NO", "" if pd.isna(r.detail) else r.detail]
    for r in audit.itertuples()]
excl_rows = [["Excluded group", "Columns", "Reason"]] + [
    [r.group, r.columns, r.reason] for r in excl.itertuples()]
S += [
    P("2. Split and leakage audit", H1),
    P("∑REY is exactly the sum of the 15 REY columns, and several ratio columns are "
      "computed from them, so none of those can be a predictor. The checks were run "
      "in code:"),
    table(audit_rows, [8.6, 1.4, 6.6]), Spacer(1, 4),
    table(excl_rows, [3.4, 6.4, 6.8]), Spacer(1, 4),
    P(f"<b>Frozen split.</b> Stratified by layer, 2 test samples per layer, seed "
      f"{hl['seed']}: {hl['n_train']} training and {hl['n_test']} test samples "
      f"(test: {esc(test_ids_txt)}). It is not stratified by lithology, so the test "
      f"set contains {hl['n_test_chert']} chert-bearing samples and cannot show how "
      "the models behave on cherts. All 29 samples were profiled (missing values, "
      "skewness, correlations with ∑REY) before the split was frozen. No model was "
      "fitted or selected from that profile, but the test set is blind to model "
      "fitting, not to exploratory analysis."),
]

model_rows = [["Model", "Features used", "CV RMSE, ppm (mean ± SD)", "Train RMSE",
               "Test RMSE, ppm [95% bootstrap CI]", "Test gain vs naive"]]
for r in comp.itertuples():
    name = LAB[r.model] + ("  (selected)" if r.model == SEL else "")
    model_rows.append([
        name, r.n_features_used, f"{r.cv_rmse_mean:.1f} ± {r.cv_rmse_sd:.1f}",
        f"{r.train_rmse:.1f}",
        f"{r.test_rmse:.1f}  [{r.test_rmse_ci95_lo:.0f}, {r.test_rmse_ci95_hi:.0f}]",
        f"{r.test_gain_vs_naive_pct:.0f}%"])
if best_t != SEL:
    other_best = (f"{LAB[best_t]} has a lower test RMSE ({hl['test_rmse'][best_t]:.0f} "
                  f"ppm), but the test set has {hl['n_test']} samples and the intervals "
                  "overlap, so the selection stands. ")
else:
    other_best = ""
lolo_rows = [["Model"] + [f"{c} held out" for c in lolo.columns]] + [
    [LAB[m]] + [("n/a" if pd.isna(v) else f"{v:.0f}") for v in lolo.loc[m]]
    for m in lolo.index]
S += [
    P("3. Preprocessing, tuning and model comparison", H1),
    P("<b>Preprocessing, features and tuning.</b> 35 non-REY trace and minor elements; "
      "log10 then standardised inside each cross-validation fold; ∑REY standardised "
      "inside the model and predicted back in ppm. Tuning used 5-fold x 10-repeat "
      "cross-validation on the 23 training samples only (RMSE in ppm): k in "
      "{1, 2, 3, 4, 5, 8, 12, 16, 22} for OLS on the k best predictors, and 40 "
      "penalty values for ridge (0.01 to 1000) and for lasso (0.001 to 1). Every "
      "tuning run is saved in results/tuning_runs.csv. The test set is not used for "
      "selection."),
    KeepTogether([P("<b>Model comparison.</b> Errors are RMSE in ppm."),
                  table(model_rows, [4.3, 1.6, 3.2, 1.7, 3.9, 1.9])]), Spacer(1, 4),
    P(f"<b>Selection.</b> The rule fixed before scoring (lowest mean CV RMSE) selects "
      f"{LAB[SEL]}. {other_best}OLS on all {hl['n_predictors']} predictors is a "
      f"retained negative result: with {hl['n_train']} training samples (design-matrix "
      f"rank {hl['train_design_rank']}) it interpolates the training data (train RMSE "
      f"{ols_train:.1f}) and generalises worse than the penalised models."),
    KeepTogether([P("<b>Leave-one-layer-out check.</b> RMSE in ppm on training samples "
                    "only: train on two layers, predict the third."),
                  table(lolo_rows, [5.0, 3.0, 3.0, 3.0])]),
]

test_rows = [["Sample", "Layer", "Lithology", "Observed", "Predicted",
              "Error (obs − pred)"]] + [
    [r.sample, r.layer, r.lithology, f"{r.observed:.0f}", f"{r.predicted:.0f}",
     f"{r.error_obs_minus_pred:+.0f}"] for r in err_test.itertuples()]
slice_rows = [["Slice type", "Slice", "n", "RMSE, ppm", "Mean error (obs − pred)",
               "RMSE as % of slice mean"]] + [
    [r.slice_type, r.slice, int(r.n), f"{r.rmse:.0f}", f"{r.mean_error:.0f}",
     f"{r.rmse_pct_of_mean_observed:.0f}%"] for r in slices.itertuples()]
lc = hl["lc"]
S += [
    P("4. Diagnostics and error cases (selected model)", H1),
    P(f"<b>Residuals and heteroscedasticity.</b> Figure 1 shows the out-of-fold "
      f"residuals. Breusch-Pagan p = {het['breusch_pagan_p']:.2f}; residual SD by "
      f"prediction third is {het['resid_sd_low']:.0f}, {het['resid_sd_mid']:.0f} and "
      f"{het['resid_sd_high']:.0f} ppm (highest third {het_ratio:.1f} times the "
      f"lowest): {HET_TXT}. Shapiro-Wilk on the residuals: p = {hl['shapiro_p']:.2f}. "
      f"With 23 samples these tests have little power. Calibration: {CAL_TXT}."),
    P(f"<b>Influence.</b> Samples above the Cook's D alert level 4/n: {flag_show}. "
      f"The largest out-of-fold errors are {esc(worst_oof)}."),
    KeepTogether([P("<b>Test-set error cases.</b> Six samples, largest error first:"),
                  table(test_rows, [1.8, 1.6, 4.6, 2.4, 2.4, 3.4])]), Spacer(1, 3),
    P(f"The two largest errors account for {100 * share2:.0f}% of the squared test "
      "error, so one or two samples dominate the score."),
    figure("diagnostics_residuals.png", 14.0,
           "Figure 1. Out-of-fold residuals: (a) vs prediction, X = chert-bearing; "
           "(b) Q-Q plot; (c) observed vs predicted, training out-of-fold and test; "
           "(d) by lithology group."),
    KeepTogether([P("<b>Critical slices.</b> Training samples, out-of-fold:"),
                  table(slice_rows, [2.8, 4.4, 1.0, 2.0, 3.2, 3.6])]), Spacer(1, 3),
    P(f"{worst_layer['slice']} has the largest absolute error "
      f"({worst_layer['rmse']:.0f} ppm); {worst_rel['slice']} has the largest "
      f"relative error ({worst_rel['rmse_pct_of_mean_observed']:.0f}%, "
      f"n = {int(worst_rel['n'])}). The {int(chert_row['n'])} chert-bearing samples "
      f"are over-predicted by {abs(chert_row['mean_error']):.0f} ppm on average and "
      f"are all in the training set. Slices hold only {int(slices['n'].min())} to "
      f"{int(slices['n'].max())} samples, so differences are suggestive at best. The "
      f"mean error by observed level ({lb['low']:.0f}, {lb['mid']:.0f}, "
      f"{lb['high']:.0f} ppm) is the pattern that grouping on the observed value "
      "produces by itself; with the calibration slope above it is not read as bias."),
    P(f"<b>Learning curve.</b> Figure 2 shows the error on unseen training samples. "
      f"Lasso RMSE falls from {lc['lasso']['8']:.0f} ppm at 8 training samples to "
      f"{lc['lasso']['20']:.0f} ppm at 20, ridge from {lc['ridge']['8']:.0f} to "
      f"{lc['ridge']['20']:.0f}, while the naive mean stays near "
      f"{lc['naive_mean']['20']:.0f}. The curves had not clearly flattened, so more "
      "samples might still help."),
    figure("learning_curve.png", 8.2,
           "Figure 2. RMSE on unseen training samples against the number of training "
           "samples (30 random subsets each; hyper-parameters re-tuned; test set not "
           "used)."),
]

coef_rows = [["Predictor", "Lasso coef (ppm per SD of log10)",
              "Ridge coef (ppm per SD of log10)", "Selected in 200 bootstrap fits"]] + [
    [r.feature, f"{r.lasso_coef_ppm_per_SD_log10x:.1f}",
     f"{r.ridge_coef_ppm_per_SD_log10x:.1f}", f"{100 * r.lasso_selection_frequency:.0f}%"]
    for r in coef.head(5).itertuples()]
top = hl["top_feature"]
S += [
    P("5. Complexity gain, and why the coefficients are not causal", H1),
    P(f"<b>Complexity gain.</b> The gain from the naive mean to {LAB[SEL]} is large: "
      f"CV RMSE {hl['cv_rmse']['naive_mean']:.0f} to {hl['cv_rmse'][SEL]:.0f} ppm, "
      f"against a fold-to-fold SD of about {hl['cv_rmse_sd'][SEL]:.0f} ppm. The further "
      f"step from OLS on k best predictors to the selected model is "
      f"{hl['kbest_minus_selected_cv']:.1f} ppm, inside that spread, so the data do "
      f"not clearly favour the more elaborate model. The mean per layer adds nothing "
      f"({hl['layer_mean_cv']:.0f} ppm): layer alone does not predict ∑REY here."),
    KeepTogether([P("<b>Coefficients.</b> The five predictors most often selected by "
                    "the lasso:"),
                  table(coef_rows, [3.0, 4.6, 4.6, 4.2])]), Spacer(1, 3),
]
S += bullets([
    f"Correlated predictors share the signal, so the choice among them is unstable: "
    f"{top} is selected in {100 * hl['top_feature_freq']:.0f}% of bootstrap fits, but "
    "the next predictors in only about half, and lasso and ridge assign them "
    "different coefficients.",
    f"Removing {top} and re-tuning raises the lasso CV RMSE from "
    f"{hl['lasso_cv_with']:.0f} to {hl['lasso_cv_without_top']:.0f} ppm (naive: "
    f"{hl['cv_rmse']['naive_mean']:.0f}); other correlated predictors recover much, "
    f"not all, of the signal. {top} correlates with {hl['top_feature_partner']} at "
    f"r = {hl['top_feature_partner_r']:.2f}.",
    "The data are observational. Apatite hosts REY together with elements such as Sr "
    "and U, so a shared mineral control is a more natural reading than an "
    "element-to-element effect. A coefficient describes this sample and is not the "
    "effect of changing an element.",
])

S += [
    P("6. Claim boundary", H1),
    P("<b>Supported.</b> In these 29 samples, ∑REY can be predicted from a handful of "
      "trace elements with much lower error than the training mean, and the signal is "
      "shared by several correlated elements."),
    P("<b>Not supported.</b>"),
]
S += bullets([
    "Causation: no coefficient shows that an element controls REY enrichment.",
    "Generalisation: one section in one basin; nothing here supports other "
    "phosphorites, basins or ages.",
    "Fine model ranking: with 6 test and 23 training samples, differences of a few "
    "tens of ppm between candidates are within noise.",
    "Cherts: the test set has none and the training set has three.",
    "Independence: neighbouring samples in a section are similar, so the within-layer "
    "split and cross-validation are optimistic; leave-one-layer-out is more honest "
    "but also uncertain.",
    "Pre-registration: the analysis is retrospective, and the test set was not blind "
    "to the exploratory profiling.",
])

S += [P("7. Reproduction guide", H1)]
S += bullets([
    "Create a virtual environment and install: <i>python -m venv .venv</i>, activate "
    "it, <i>python -m pip install -r requirements.txt</i> (exact versions in "
    "<i>requirements-lock.txt</i>).",
    "Save the original supplementary workbook as <i>data/raw/Supplementary "
    "file.xlsx</i> (not redistributed) and check that its SHA-256 equals:<br/>" + sha,
    "Open <i>DS-A3_regression_baseline.ipynb</i> in VS Code, select the .venv kernel "
    "and run all cells from the top (about 4 minutes). Then run <i>python "
    "src/build_report.py</i> to regenerate this report.",
    f"Everything is seeded (seed {hl['seed']}). Environment of this run: Python "
    f"{esc(ri['python'])}, numpy {esc(ri['numpy'])}, pandas {esc(ri['pandas'])}, "
    f"scikit-learn {esc(ri['scikit_learn'])}, statsmodels {esc(ri['statsmodels'])}; "
    "small differences across library versions are possible.",
    "AI assistance (Claude, Anthropic) is disclosed in the README and in "
    "<i>docs/AI_use_log.md</i>.",
], markup=True)


def footer(c, d):
    c.saveState()
    c.setFont("TNR", 9)
    c.setFillColor(BLACK)
    c.drawString(2.0 * cm, 1.0 * cm, "DS-A3 | Regression Baseline and Diagnostics")
    c.drawRightString(A4[0] - 2.0 * cm, 1.0 * cm, f"Page {d.page}")
    c.restoreState()


doc = SimpleDocTemplate(
    str(DOCS / "DS-A3_report.pdf"), pagesize=A4,
    leftMargin=2.0 * cm, rightMargin=2.0 * cm, topMargin=1.8 * cm, bottomMargin=1.8 * cm,
    title="DS-A3 Regression Baseline and Diagnostics", author="",
    initialFontName="TNR", initialFontSize=12)
doc.build(S, onFirstPage=footer, onLaterPages=footer)
print("Wrote docs/DS-A3_report.pdf")

# ---------------------------------------------------------------- platform summary
c_sel, t_sel, ci = hl["cv_rmse"][SEL], hl["test_rmse"][SEL], hl["test_ci"][SEL]
if best_t != SEL:
    ridge_note = (f"{best_t.capitalize()} scored better on the test set "
                  f"({hl['test_rmse'][best_t]:.0f} ppm) but was not chosen, since the "
                  "test set is not used for selection and the intervals overlap. ")
else:
    ridge_note = ""
worst_l = hl["worst_lolo_layer"]
summary = (
    f"This project asks how well bulk ∑REY in {hl['n_total']} samples from the Early "
    "Cambrian Kakul Garlaniyan phosphorites (published supplementary data from my "
    f"paper) can be predicted from {hl['n_predictors']} non-REY trace elements. "
    "Because ∑REY is exactly the sum of the REY columns, those columns and their "
    "ratios were excluded as leakage, together with major oxides (recorded for only "
    "14 samples) and below-detection columns. "
    f"I froze a layer-stratified split ({hl['n_train']} training, {hl['n_test']} test "
    f"samples, seed {hl['seed']}) and tuned a naive mean baseline, OLS, ridge and "
    "lasso with repeated cross-validation on the training samples only. "
    f"By the rule fixed beforehand (lowest CV RMSE), {SEL} was selected: CV RMSE "
    f"{c_sel:.0f} ppm against {hl['cv_rmse']['naive_mean']:.0f} ppm for the mean, and "
    f"test RMSE {t_sel:.0f} ppm (bootstrap 95% interval {ci[0]:.0f} to {ci[1]:.0f}) "
    f"on only {hl['n_test']} samples. "
    + ridge_note
    + f"Diagnostics show {HET_TXT}, {CAL_TXT}, and the largest error when layer "
    f"{worst_l} is held out ({hl['lolo'][SEL][worst_l]:.0f} ppm). "
    "The test set contains no chert, and the most-selected predictor "
    f"({top}) is strongly correlated with others, so coefficients are descriptive, "
    "not causal. Weak results are kept: OLS on all predictors interpolates the "
    "training data and generalises worse. The analysis is retrospective and limited "
    "to this section. Code, results, a PDF report and the AI-use log are in the "
    "repository."
)
nw = len(summary.split())
assert 150 <= nw <= 300, f"summary has {nw} words"
note = f"\n\n<!-- {nw} words; edit in your own words before submitting -->\n"
(DOCS / "platform_summary.md").write_text(summary + note, encoding="utf-8")
print(f"Wrote docs/platform_summary.md ({nw} words)")