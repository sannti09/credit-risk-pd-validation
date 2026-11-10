import numpy as np
import pandas as pd

from credit_risk.validation import binomial_by_band, hosmer_lemeshow, psi, psi_light


def test_psi_zero_for_same_and_red_for_shift():
    a = pd.Series(list("AABBCC") * 100)
    assert psi(a, a) < 1e-9
    assert psi_light(psi(a, pd.Series(list("AAAAAC") * 100))) == "rojo"


def test_calibration_ok_when_pd_is_true():
    rng = np.random.default_rng(1)
    p = pd.Series(rng.uniform(0.02, 0.4, 20000))
    y = pd.Series((rng.random(20000) < p).astype(int))
    assert hosmer_lemeshow(y, p)[1] > 0.01
    t = binomial_by_band(pd.qcut(p, 5, labels=False), y, p)
    assert (t.p_valor > 0.001).all()
    # Si la PD real es el doble, el binomial debe detectar subestimación
    t2 = binomial_by_band(pd.qcut(p, 5, labels=False), y, p / 2)
    assert (t2.semaforo == "rojo").all()


def test_psi_new_category_is_large_but_finite():
    base = pd.Series(list("AB") * 500)
    new = pd.Series(list("ABC") * 333)  # categoría C no existe en la base
    v = psi(base, new)
    assert np.isfinite(v) and v > 0.25


def test_hosmer_lemeshow_degrees_of_freedom():
    from scipy import stats

    rng = np.random.default_rng(2)
    p = pd.Series(rng.uniform(0.05, 0.3, 5000))
    y = pd.Series((rng.random(5000) < p).astype(int))
    stat, pval = hosmer_lemeshow(y, p, g=10)
    assert abs(pval - stats.chi2.sf(stat, 8)) < 1e-12  # gl = g - 2
