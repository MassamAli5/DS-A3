# DS-A3 | AI-use log

## Tool and tasks
I used Claude (Anthropic) as a coding assistant. Claude drafted the code and the written text (README, explanations of the results). I entered the code into the VS Code notebook step by step, ran every cell on my own computer, and made the Git commits.

Claude also ran trial versions in its own environment. In those trials it saw the test-set scores. It fixed a bug in an early script version, and widened the k grid (k <= 8 to k <= 22) after the best k was at the edge. This is also noted in the README and the notebook.

## Advice accepted or rejected
- **Accepted:** use the bulk-rock table (Table S1); exclude the REY columns, their ratios and the major oxides from the predictors; keep ∑REY on its raw scale and log10 the predictors; select the model by lowest cross-validation error and score the test set once; keep lasso even though ridge scored better on the six test samples.
- **Rejected:** the ready-made zip package. I built the notebook myself, step by step. I also wanted to delete the derived-ratio list; Claude explained that it is the exclusion list used by the leakage audit, so I kept it.
- **Corrected:** Claude's "shrinkage" sentence was replaced after a calibration check (slope 1.07).

## Independent checks
I restarted the kernel and ran all cells from the top without errors. 

Not done: hand-recalculation in Excel, and a run on a second computer.

## Reflection
∑REY is the sum of the REY columns, so they cannot be predictors. A test set of six samples should not decide which model is chosen. 

## Responsibility
I am responsible for the final work in this repository.