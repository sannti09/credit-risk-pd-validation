# Independent validation report — PD scorecard (Lending Club, 36-month loans)

*Generated automatically by `notebooks/08_validation_report.py` on 2026-11-11. Do not edit by hand.
Spanish version: [`informe_validacion.md`](informe_validacion.md).*

## 1. Scope
- **Model:** logistic scorecard on WoE, 13 application and bureau variables; scale 600 = 50:1 odds, PDO 20.
- **Intended use:** origination PD (36-month loan lifetime) for applicants within Lending Club's policy (**FICO ≥ 660,
  DTI ≤ 34.99**, the ranges seen in development). Outside that domain the model issues no PD.
- **Samples:** development 2013 · validation 2014 · out-of-time (OOT) 2015 · stability 2016–2018 (no outcomes yet).
- **Out of scope:** 60-month loans. The IFRS 9 expected credit loss is documented separately (README).

## 2. Traffic-light summary
Thresholds: green / amber / red. 6 🟢 · 5 🟡 · 2 🔴

| Dimension | Test | Result | Threshold (green / amber / red) | Status |
|---|---|---|---|---|
| Discrimination | Gini OOT 2015 | 0.325 | ≥ 0.40 / 0.25–0.40 / < 0.25 | 🟡 amber |
| Discrimination | KS OOT 2015 | 0.237 | ≥ 0.30 / 0.20–0.30 / < 0.20 | 🟡 amber |
| Discrimination | Gini drop, train → OOT | 0.3% | < 10% / 10–20% / > 20% | 🟢 green |
| Benchmark | Own Gini − LC grade Gini (OOT) | -3.2 pts | ≥ 0 / down to −5 / < −5 pts | 🟡 amber |
| Stability | Score PSI, max. 2014–2018 | 0.081 (2018) | < 0.10 / 0.10–0.25 / > 0.25 | 🟢 green |
| Stability | Max. variable CSI, OOT 2015 | 0.060 | < 0.10 / 0.10–0.25 / > 0.25 | 🟢 green |
| Stability | Max. variable CSI, 2018 | 0.382 (revol_util) | < 0.10 / 0.10–0.25 / > 0.25 | 🔴 red |
| Calibration (original) | Relative gap PD vs. default rate, OOT | 13.1% | < 10% / 10–20% / > 20% | 🟡 amber |
| Calibration (original) | Bands significantly under-predicted (binomial) | 9 of 10 | 0 / 1–2 / ≥ 3 | 🔴 red |
| Calibration (recalibrated + MoC) | Relative gap PD vs. default rate, OOT | 1.1% | < 10% / 10–20% / > 20% | 🟢 green |
| Calibration (recalibrated + MoC) | Bands significantly under-predicted (binomial) | 1 of 10 | 0 / 1–2 / ≥ 3 | 🟡 amber |
| Official model (in domain) | Relative gap PD vs. default rate, OOT | 1.7% | < 10% / 10–20% / > 20% | 🟢 green |
| Official model (in domain) | Bands significantly under-predicted (binomial) | 0 of 10 | 0 / 1–2 / ≥ 3 | 🟢 green |
| Domain | % of applications out of domain (2015 → 2018) | 3.4% → 6.4% | informative: no PD is issued; 2015 out-of-domain default rate = 22.6% | ℹ️ info |
| Calibration | Hosmer-Lemeshow OOT (p-value) | 0.000 → 0.000 | informative: with n ≈ 283k it rejects tiny gaps | ℹ️ info |
| Representativeness | PSI approved vs. rejected (FICO) | 0.89 | informative: expected given LC's credit policy | ℹ️ info |

## 3. Findings
| # | Severity | Finding | Recommendation |
|---|---|---|---|
| F1 | High | **PD under-estimation:** the original model predicts 13.0% against 14.9% observed out of time; 9 of 10 bands are significantly under-predicted. Cause: the default rate rises ~1.4 points per year. | **Implemented:** official model recalibrated with a margin of conservatism; within its domain it predicts 14.9% vs. 14.6% observed, with no band significantly under-predicted. Re-estimate the margin yearly. |
| F2 | Medium | **Moderate discriminatory power:** OOT Gini 0.325, 3.2 points below Lending Club's grade. | Acceptable given public data only. The regularized gradient-boosting challenger reaches 0.340: assess whether the gain justifies lower explainability. |
| F3 | Medium | **Population drift in 2017–2018:** CSI of `revol_util` = 0.38 and of `percent_bc_gt_75` = 0.37 in 2018; the score PSI stays green. | Quarterly CSI monitoring; trigger a review if the score PSI exceeds 0.10. |
| F4 | Medium | **Selection bias and domain:** the model only observes approved loans (59% of rejected applicants with a valid FICO are below 660). Lending Club also raised its DTI cap from 35 to 40 in 2014: in 2015, 3.4% of loans have DTI > 35, with a 22.6% default rate. | **Implemented:** out of domain the model returns no PD. Those cases need a separate policy or a model retrained with DTI > 35. |
| F5 | Low | **OOT not fully blind:** the idea of the margin of conservatism came after observing the 2015 gap. | Confirm calibration on the next mature cohort. |

## 4. Limitations
- 2013–2015 data from a US peer-to-peer platform: demonstrative purposes only.
- The 2014 validation sample is optimistic (it was used for modeling decisions); the reference is OOT 2015.
- Full decision log (in Spanish): `docs/decisiones.md`.

## 5. Conclusion
**Approved with conditions — conditions implemented** (`src/credit_risk/model.py`, `models/pd_model_final.pkl`):
1. The PD is always recalibrated with the margin of conservatism (intercept adjustment +0.184).
2. Outside the domain (FICO ≥ 660, DTI ≤ 34.99) the model issues no PD.
3. Cohort monitoring in `notebooks/09_monitoring.py` (PSI, CSI, % out of domain, calibration).

To follow up: `revol_util` CSI red in 2018 and the rise in out-of-domain applications
(6.4% in 2018) → candidate retraining triggers.
