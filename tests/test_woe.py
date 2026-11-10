import numpy as np
import pandas as pd

from credit_risk.woe import MISSING, WoEBinner


def _data(n=5000, seed=0):
    rng = np.random.default_rng(seed)
    x = rng.normal(size=n)
    y = (rng.random(n) < 1 / (1 + np.exp(2 + 1.5 * x))).astype(int)  # x alto -> menos riesgo
    noise = rng.normal(size=n)
    cat = rng.choice(["A", "B", "C"], size=n)
    x_nan = x.copy()
    x_nan[:500] = np.nan
    return pd.DataFrame({"x": x, "noise": noise, "cat": cat, "x_nan": x_nan, "y": y})


def test_woe_direction_and_iv_ranking():
    df = _data()
    b = WoEBinner(n_bins=5).fit(df, "y", ["x", "noise", "cat"])
    t = b.tables_["x"]
    assert t["woe"].iloc[-1] > t["woe"].iloc[0]  # último bin (x alto) = menor riesgo = WoE mayor
    iv = b.iv_summary()["iv"]
    assert iv["x"] > 0.3 and iv["noise"] < 0.02


def test_missing_is_own_bin_and_transform_uses_train_bins():
    df = _data()
    b = WoEBinner(n_bins=5).fit(df.iloc[:4000], "y", ["x_nan"])
    assert MISSING in b.tables_["x_nan"].index
    w = b.transform(df.iloc[4000:])
    assert w["x_nan"].notna().all() and w.shape == (1000, 1)


def test_coarse_classing_is_monotonic():
    df = _data(20000)
    b = WoEBinner(n_bins=20).fit(df, "y", ["x"])
    t = b.tables_["x"].drop(index="MISSING", errors="ignore")
    assert t["woe"].is_monotonic_increasing  # x alto -> menos riesgo
    assert (t["n"] / t["n"].sum()).min() >= 0.05
