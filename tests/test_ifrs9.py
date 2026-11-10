import numpy as np
import pandas as pd

from credit_risk.ifrs9 import amortization, assign_stage, ecl, marginal_pd


def test_amortization_pays_off_and_starts_at_balance():
    bal = amortization(np.array([1000.0]), np.array([12.0]), np.array([12]), horizon=14)
    assert bal[0, 0] == 1000.0 and bal[0, 11] > 0 and bal[0, 12] == 0


def test_marginal_pd_sums_to_remaining_lifetime():
    f = np.full(36, 1 / 36)
    p, mob = np.array([0.2]), np.array([12])
    mpd = marginal_pd(p, mob, f)
    expected = 0.2 * (1 - 12 / 36) / (1 - 0.2 * 12 / 36)
    assert abs(mpd.sum() - expected) < 1e-12


def test_stage_rules_and_ecl_ordering():
    port = pd.DataFrame({"loan_status": ["Current", "Current", "Late (31-120 days)"],
                         "fico_low": [700.0, 700.0, 700.0], "fico_actual": [700.0, 640.0, 650.0]})
    st = assign_stage(port)
    assert st.tolist() == [1, 2, 3]
    f = np.full(36, 1 / 36)
    r = ecl(st, np.full(3, 0.15), np.full(3, 6), np.full(3, 10000.0), np.full(3, 12.0), np.full(3, 30), f, 0.9)
    assert r.ecl.iloc[0] < r.ecl.iloc[1] < r.ecl.iloc[2] == 9000.0
