# DS-A3 | Regression Baseline and Diagnostics

Predicting bulk ∑REY in the Early Cambrian Kakul Garlaniyan phosphorites from non-REY trace elements, using a naive baseline, a leakage-free frozen split,
OLS / ridge / lasso candidates tuned without the test set, diagnostics, and an explicit claim boundary.

**Course:** Data Science, DS-A3.

## Question

Can bulk ∑REY (ppm) in 29 samples from one section be predicted from non-REY trace and minor elements, and where does that prediction stop being reliable?

## Result in brief

The model chosen by the rule fixed in advance (lowest cross-validation error on the training samples) is the lasso. Errors are RMSE in ppm.

| Model | Predictors used | CV RMSE (mean ± SD) | Test RMSE [95% bootstrap interval] |
|---|---|---|---|
| Naive: training mean | 0 | 181 ± 47 | 169 [116, 211] |
| Naive: mean per layer | 0 | 183 ± 47 | 143 [86, 183] |
| OLS, all 35 predictors | 35 | 80 ± 31 | 101 [30, 168] |
| OLS on the k best predictors (k = 8) | 8 | 56 ± 19 | 87 [33, 137] |
| Ridge | 35 | 62 ± 15 | 43 [19, 62] |
| **Lasso (selected)** | 8 | 52 ± 17 | 82 [32, 118] |

- Any of the regression models cuts the cross-validation error to about a third of the naive error. The mean per layer adds nothing, so the layer alone does not predict ∑REY here.
- Ridge has a lower test RMSE than the selected lasso, but the test set has only six samples and the intervals overlap. The test set was not used to choose, so the selection stands.
- Lasso is not clearly better than the simpler OLS on 8 predictors (difference 3.6 ppm against a fold-to-fold SD of about 17 ppm).
- Two of the six test samples (KG-1 and KG-22) account for 86% of the squared test error.
- Leave-one-layer-out RMSE of the lasso is 49 to 102 ppm, worst when layer LPL is held out. All three chert-bearing samples are in LPL.
- Heteroscedasticity is not detected (Breusch-Pagan p = 0.28), but with 23 samples the test has little power. Cook's D flags KG-12, KG-25 and KG-28.
- The calibration slope of observed on out-of-fold predicted ∑REY is 1.07 (95% interval 0.92 to 1.21).
- Coefficients are not stable or unique: Be is selected in 99% of 200 bootstrap fits, but the next predictors only in about half, and removing Be raises the lasso CV RMSE from 52 to 67 ppm while correlated elements take over.

## Data and provenance

The data are Table S1 (bulk rock) of the published supplementary workbook of Ali et al., *Journal of Asian Earth Sciences*, DOI 10.1016/j.jseaes.2025.106927.

The workbook is **not included** in this repository. To reproduce the analysis, obtain it from the article's supplementary material and save it as `data/raw/Supplementary file.xlsx`.
It is never edited: all cleaning is in code. The notebook prints its SHA-256 and stores it in `results/run_info.json`. Mine is `17343594cd7317c950a5ab7fd713c0928859a0a333ac20798d9da6ce645dd18b`.
Some saved result files (for example the test-set predictions and error cases) contain observed ∑REY values of individual samples, taken from that published table. No data were generated or altered.

## Method

∑REY equals the sum of the 15 REY columns, so those columns and the ratios computed from them are excluded as predictors. Major oxides (recorded for only 14 of 29 samples) and the columns with below-detection entries (Ag, Tl, Hf) are excluded too.
The remaining 35 trace and minor elements are log10-transformed and standardised inside each cross-validation fold. The target stays on its raw scale (log10 made its skew worse).

A split stratified by layer (23 training, 6 test samples, seed 42) is frozen before any model is scored. The candidates are the training mean, the mean per layer, OLS on all predictors, OLS on the k best predictors, ridge and lasso.
They are tuned by 5-fold x 10-repeat cross-validation on the training samples only. The model with the lowest mean CV RMSE is selected, and the test set is scored once.

Diagnostics use out-of-fold residuals: residual plots, a Breusch-Pagan test, leave-one-out refits and Cook's distance, a learning curve, error slices by layer, lithology and observed level, a calibration slope, and a leave-one-layer-out check.

## Decisions and disclosures

- All 29 samples were profiled (missing values, skewness, correlations with ∑REY) before the split was frozen. No model was fitted or selected from that, but the test set is blind to model fitting, not to exploratory analysis.
- The grid for k in "OLS on the k best predictors" was first limited to k <= 8 and later widened to k <= 22, after a trial run showed the best k at the old edge. That trial run also displayed test-set scores, so the decision was not made blind to them.
- The split is not stratified by lithology: all three chert-bearing samples are in the training set, so the test set says nothing about cherts. It was not re-drawn to fix this.
- The model was not switched to ridge after ridge scored better on the test set.
- Weak results are kept: OLS on all 35 predictors fits the 23 training samples exactly (training RMSE 0) and generalises worse.
- An early reading of the residual plot called the under-prediction of high values "shrinkage". A calibration check (slope 1.07) showed that this was overstated, and the text was corrected.

## Reproduce

Environment of my run: Windows, Python 3.13.9, numpy 2.5.4, pandas 3.1.0, scipy 1.18.1, scikit-learn 1.9.1, statsmodels 0.15.0, matplotlib 3.11.2 (full list in `requirements-lock.txt`, details in `results/run_info.json`).

Windows (PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

If PowerShell blocks the activation script, run `Set-ExecutionPolicy -Scope Process RemoteSigned` first.
macOS / Linux: `python -m venv .venv && source .venv/bin/activate && python -m pip install -r requirements.txt`.

1. Put the workbook at `data/raw/Supplementary file.xlsx` and check its fingerprint:
   `Get-FileHash "data\raw\Supplementary file.xlsx" -Algorithm SHA256`
2. Open the project folder in VS Code, open `DS-A3_regression_baseline.ipynb`, select the `.venv` kernel and run all cells from the top.
3. Compare with the values above. The workbook hash should match, the six test samples should be KG-1, KG-15, KG-21, KG-22, KG-27 and KG-7, the selected model should be lasso (CV RMSE 51.9 ppm, test RMSE 82.1 ppm), and the notebook should print no errors.
4. 4. Optional: run `python src/build_report.py` to regenerate `docs/DS-A3_report.pdf` and `docs/platform_summary.md` from the saved results.
All randomness uses seed 42. Small numerical differences across library versions are possible. The notebook was executed from a restarted kernel on my machine without errors. Reproduction on a second computer has not been tested.

## Claim boundary

What the analysis supports: in these 29 samples, ∑REY can be predicted from a handful of trace elements with much lower error than the training mean, and the signal is shared by several correlated elements.

What it does not support:
- **Causation.** No coefficient shows that an element controls REY enrichment. Apatite hosts REY, Sr and U together, so a shared mineral control is a more natural explanation than any element-to-element effect.
- **Generalisation.** One section in one basin; nothing here supports other phosphorites, basins or ages.
- **Fine model ranking.** With 6 test and 23 training samples, differences of a few tens of ppm between candidates are within noise.
- **Cherts.** The test set has none, and the training set has three.
- **Independence.** Neighbouring samples in a section are similar, so the within-layer split and cross-validation are optimistic. The leave-one-layer-out check is more honest, but also uncertain.
- **Pre-registration.** The analysis is retrospective and exploratory.

## AI assistance

I used Claude (Anthropic) coding assistant. Claude drafted the code and I entered into the VS notebook. I ran every cell on my own computer, and made the Git commits.
The tasks, the advice accepted or rejected, and my independent checks are recorded in `docs/AI_use_log.md`.