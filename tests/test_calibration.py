import numpy as np

from credit_risk.calibration import apply_platt, apply_shift, fit_intercept_shift, fit_platt


def test_shift_matches_observed_rate_and_platt_recovers_params():
    rng = np.random.default_rng(0)
    logit = rng.normal(-2, 1, 50000)
    y = (rng.random(50000) < 1 / (1 + np.exp(-(0.5 + 1.2 * logit)))).astype(int)
    d = fit_intercept_shift(logit, y)
    assert abs(apply_shift(logit, d).mean() - y.mean()) < 1e-6
    a, b = fit_platt(logit, y)
    assert abs(a - 0.5) < 0.1 and abs(b - 1.2) < 0.05
    assert apply_platt(logit, a, b).shape == logit.shape
