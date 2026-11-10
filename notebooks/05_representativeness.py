"""Representatividad: aprobados vs. rechazados (D8). Ventana del modelo 2013-2015.
Salidas: reports/repr_approval_rate.csv, reports/repr_psi.csv, reports/repr_policy.csv"""
import duckdb
import numpy as np
import pandas as pd

from credit_risk.validation import psi, psi_light

con = duckdb.connect("data/credit.duckdb")
con.execute(open("sql/06_applications.sql").read())

# 1) Tasa de aprobación por año (todas las solicitudes)
rate = con.sql("""
    select app_year, count(*) filter (where fuente='aprobado') aprobados,
           count(*) filter (where fuente='rechazado') rechazados,
           round(100.0 * count(*) filter (where fuente='aprobado') / count(*), 1) pct_aprobacion
    from applications where app_year between 2007 and 2018 group by 1 order by 1""").df()

df = con.sql("select * from applications where app_year between 2013 and 2015").df()
acc, rej = df[df.fuente == "aprobado"], df[df.fuente == "rechazado"]


def binned(s: pd.Series, edges) -> pd.Series:
    return pd.cut(s.dropna(), edges).astype(str)  # PSI solo sobre valores válidos; faltantes se reportan aparte


# 2) PSI rechazados vs aprobados (cortes = deciles de aprobados). Score: solo FICO (antes del 5-nov-2013, D10)
rows = []
for v in ["amount", "risk_score", "dti"]:
    q = np.unique(np.nanquantile(acc[v].dropna(), np.linspace(0, 1, 11)))
    edges = np.concatenate(([-np.inf], q[1:-1], [np.inf]))
    p = psi(binned(acc[v], edges), binned(rej[v], edges))
    rows.append({"variable": v, "mediana_aprob": acc[v].median(), "mediana_rech": rej[v].median(),
                 "pct_falt_aprob": 100 * acc[v].isna().mean(), "pct_falt_rech": 100 * rej[v].isna().mean(),
                 "psi": p, "semaforo": psi_light(p)})
p_state = psi(acc.state.fillna("MISSING"), rej.state.fillna("MISSING"))
rows.append({"variable": "state", "psi": p_state, "semaforo": psi_light(p_state)})
psi_t = pd.DataFrame(rows).set_index("variable")

# 3) ¿Cuántos rechazados caen dentro del "soporte" de los aprobados? (lo que el modelo sí conoce)
min_score = acc.risk_score.quantile(0.005)
max_dti = acc.dti.quantile(0.995)
r = rej.dropna(subset=["risk_score", "dti"])  # score válido = solo antes del 5-nov-2013
policy = pd.Series({
    "rechazados 2013-15": len(rej),
    "con score y dti válidos": len(r),
    f"score < p0,5 aprobados ({min_score:.0f})": (r.risk_score < min_score).mean() * 100,
    f"dti > p99,5 aprobados ({max_dti:.0f})": (r.dti > max_dti).mean() * 100,
    "dentro del soporte (ambos ok) %": ((r.risk_score >= min_score) & (r.dti <= max_dti)).mean() * 100,
}).round(1)

rate.to_csv("reports/repr_approval_rate.csv", index=False)
psi_t.round(3).to_csv("reports/repr_psi.csv")
policy.to_csv("reports/repr_policy.csv", header=["valor"])
pd.set_option("display.width", 140)
print(rate.to_string(index=False))
print("\n", psi_t.round(2).to_string())
print("\n", policy.to_string())
