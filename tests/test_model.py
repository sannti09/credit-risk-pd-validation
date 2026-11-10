import numpy as np
import pandas as pd
import statsmodels.api as sm

from credit_risk.model import PDModel
from credit_risk.woe import WoEBinner


def _toy():
    rng = np.random.default_rng(0)
    df = pd.DataFrame({"fico_low": rng.integers(660, 800, 4000).astype(float),
                       "dti": rng.uniform(0, 35, 4000)})
    df["target"] = (rng.random(4000) < 0.1 + 0.004 * df.dti - 0.0005 * (df.fico_low - 660)).astype(int)
    b = WoEBinner(n_bins=5).fit(df, "target", ["fico_low", "dti"])
    m = sm.Logit(df.target, sm.add_constant(b.transform(df))).fit(disp=0)
    return df, b, m


def test_out_of_domain_gets_nan_and_delta_raises_pd():
    df, b, m = _toy()
    dom = {"fico_low": (660, None), "dti": (None, 35)}
    base = PDModel(b, m, ["fico_low", "dti"], delta=0.0, domain=dom)
    moc = PDModel(b, m, ["fico_low", "dti"], delta=0.2, domain=dom)
    new = pd.DataFrame({"fico_low": [700.0, 640.0, 700.0], "dti": [20.0, 20.0, 50.0]})
    p = base.predict_pd(new)
    assert p.notna().tolist() == [True, False, False]
    assert moc.predict_pd(new).iloc[0] > p.iloc[0]
    assert base.score(new).isna().tolist() == [False, True, True]
