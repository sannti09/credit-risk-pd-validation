"""Provisión según el Modelo de Referencia de Consumo de la SFC (MRCO) vs. ECL NIIF 9 (D25).

Fuentes (documentos de la SFC, citados con enlace en docs/decisiones.md D25):
- Matrices A y B de PI y fórmula: CE 047 de 2016, Anexo 5 del Cap. II CBCF (verificado en el texto).
- Factor K (CE 026 de 2022): solo créditos originados desde 2023 -> no aplica a esta cartera (2015-2018).
- Incumplimiento consumo: mora > 90 días (cap02riesgocrediticio.doc).
- PDI sin garantía 75% -> 85% (30 días en incumplimiento) -> 100% (90 días): FUENTE SECUNDARIA, sin verificar.
- Ajuste por plazo AP = 1 (plazo pactado < 72 meses).
Aproximación: el puntaje del MRCO usa variables del buró colombiano que Lending Club no tiene; la calificación se
asigna con la PD a 12 meses del modelo propio, al nivel de la Matriz A más cercano. Segmento: General-Otros.
Salida: reports/sfc_mrco_comparison.csv"""
import duckdb
import numpy as np
import pandas as pd

RATINGS = ["AA", "A", "BB", "B", "CC"]
MATRIZ_A = {"AA": 0.0210, "A": 0.0388, "BB": 0.1268, "B": 0.1416, "CC": 0.2257}  # General-Otros
MATRIZ_B = {"AA": 0.0388, "A": 0.0567, "BB": 0.2172, "B": 0.2320, "CC": 0.3640}

con = duckdb.connect("data/credit.duckdb", read_only=True)
d = con.sql("""select p.id, p.saldo, p.etapa, p.meses_sin_pago, p.loan_status, q.pd_12m
               from ifrs9_portfolio p join ifrs9_pd q using (id)""").df()

# Calificación: incumplimiento si mora > 90 días (≈ etapa 3); si no, nivel de Matriz A más cercano a la PD 12m
pa = np.array([MATRIZ_A[r] for r in RATINGS])
cuts = (pa[:-1] + pa[1:]) / 2  # puntos medios entre niveles consecutivos
d["calificacion"] = np.where(d.etapa == 3, "Incumplimiento",
                             np.array(RATINGS)[np.searchsorted(cuts, d.pd_12m.to_numpy())])
# PDI: 75% antes del incumplimiento; en incumplimiento sube con los días (mora - 90).
# Sin fecha de último pago (84 préstamos en etapa 3, US$ 1,1 M): se asume >= 90 días en incumplimiento -> PDI 100%
# (conservador; impacto ≈ US$ 0,3 M en la Matriz A).
dias_incump = np.clip((d.meses_sin_pago.fillna(6) - 3) * 30, 0, None)
d["pdi"] = np.where(d.etapa == 3, np.select([dias_incump >= 90, dias_incump >= 30], [1.0, 0.85], 0.75), 0.75)
for m, mat in (("A", MATRIZ_A), ("B", MATRIZ_B)):
    d[f"pi_{m}"] = d.calificacion.map({**mat, "Incumplimiento": 1.0})
    d[f"pe_{m}"] = d[f"pi_{m}"] * d.pdi * d.saldo  # AP = 1

g = d.groupby("calificacion").agg(prestamos=("id", "size"), saldo=("saldo", "sum"), pd12_modelo=("pd_12m", "mean"),
                                  pe_A=("pe_A", "sum"), pe_B=("pe_B", "sum"))
g = g.reindex(RATINGS + ["Incumplimiento"]).dropna(how="all")
g.loc["total"] = g.sum(numeric_only=True)
g.loc["total", "pd12_modelo"] = np.average(d.pd_12m, weights=d.saldo)
g["pct_saldo"] = 100 * g.saldo / d.saldo.sum()
for c in ("saldo", "pe_A", "pe_B"):
    g[c] = g[c] / 1e6
ecl = pd.read_csv("reports/ifrs9_scenarios.csv", index_col=0).ecl_musd
g.round(3).to_csv("reports/sfc_mrco_comparison.csv")

pd.set_option("display.width", 140)
print(g.round(3).to_string())
tot = d.saldo.sum() / 1e6
print(f"\nSFC Matriz A: {g.loc['total', 'pe_A']:.1f} M ({100 * g.loc['total', 'pe_A'] / tot:.2f}%) · "
      f"Matriz B: {g.loc['total', 'pe_B']:.1f} M ({100 * g.loc['total', 'pe_B'] / tot:.2f}%)")
print(f"NIIF 9: base {ecl['base']:.1f} M ({100 * ecl['base'] / tot:.2f}%) · ponderada {ecl['ponderado']:.1f} M "
      f"({100 * ecl['ponderado'] / tot:.2f}%)")

# ---- Descomposición: de la provisión SFC (Matriz A) a la ECL NIIF 9 base, un factor a la vez ----
LGD = float(pd.read_csv("reports/ifrs9_lgd_param.csv").set_index("parametro").valor["lgd"])
q = con.sql("select id, pd_aplicable from ifrs9_pd").df()
d = d.merge(q, on="id")
e0 = d.pe_A.sum()
e1 = (d.pi_A * LGD * d.saldo).sum()                              # 1) PDI regulatoria -> LGD observada
e2 = (np.where(d.etapa == 3, 1.0, d.pd_12m) * LGD * d.saldo).sum()  # 2) PI de la matriz -> PD 12m del modelo
e3 = (d.pd_aplicable * LGD * d.saldo).sum()                      # 3) etapa 2 a vida restante (NIIF 9)
comp = pd.read_csv("reports/ifrs9_ecl_components.csv").set_index("componente").musd * 1e6
e4 = comp["ecl_base_sin_descuento"]                              # 4) saldo amortizado mes a mes (sin descuento)
e5 = comp["ecl_base"]                                            # 5) descuento a la tasa efectiva
steps = pd.DataFrame({"paso": ["SFC Matriz A", "PDI 75% -> LGD observada", "PI matriz -> PD 12m del modelo",
                               "Etapa 2 a vida restante", "Amortización del saldo", "Descuento a tasa efectiva",
                               "NIIF 9 base"],
                      "efecto_musd": [e0, e1 - e0, e2 - e1, e3 - e2, e4 - e3, e5 - e4, e5]})
assert abs(e5 - ecl["base"] * 1e6) < 1e3, "el puente no termina en la ECL base reportada"
steps["efecto_musd"] /= 1e6
steps.round(2).to_csv("reports/sfc_vs_ifrs9_bridge.csv", index=False)
print("\nPUENTE SFC (Matriz A) -> NIIF 9 base (US$ M)\n", steps.round(1).to_string(index=False))
