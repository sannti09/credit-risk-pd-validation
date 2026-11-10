"""Fase 2a: coarse classing + selección de variables. Ver docs/decisiones.md (D5).
Salidas: reports/iv_train_oot.csv, reports/selected_features.txt, reports/woe_tables.csv"""
import duckdb
import numpy as np
import pandas as pd

from credit_risk.woe import WoEBinner, iv_strength

LC_SCORE = {"grade", "sub_grade", "int_rate"}  # score de Lending Club: solo benchmark
EXCLUDE = {"id", "issue_date", "issue_year", "loan_status", "target", "split", "term_months",
           "fico_high"} | LC_SCORE  # fico_high = fico_low + 4 (redundante)
IV_MIN, CORR_MAX, IV_DROP_MAX = 0.02, 0.7, 0.5  # IV_DROP_MAX: caída relativa de IV tolerada en OOT

df = duckdb.connect("data/credit.duckdb", read_only=True).sql("select * from model_sample").df()
train, oot = df[df.split == "train"], df[df.split == "oot"]
features = [c for c in df.columns if c not in EXCLUDE]

b = WoEBinner().fit(train, "target", features)


def iv_fixed_bins(data: pd.DataFrame, f: str) -> float:
    """IV en otra muestra usando los cortes y WoE aprendidos en train."""
    g = pd.DataFrame({"bin": b._assign(data[f]), "y": data["target"]}).groupby("bin")["y"]
    bad, good = g.sum() + 0.5, g.size() - g.sum() + 0.5
    pb, pg = bad / bad.sum(), good / good.sum()
    return float(((pg - pb) * np.log(pg / pb)).sum())


s = b.iv_summary().rename(columns={"iv": "iv_train"})
s["iv_oot"] = [iv_fixed_bins(oot, f) for f in s.index]
s["caida_rel"] = 1 - s["iv_oot"] / s["iv_train"]
s["motivo"] = ""
s.loc[s.iv_train < IV_MIN, "motivo"] = "IV < 0.02"
s.loc[(s.motivo == "") & (s.caida_rel > IV_DROP_MAX), "motivo"] = "inestable en OOT"

# Redundancia: entre pares con |corr(WoE)| > 0.7 se queda la de mayor IV
cand = list(s[s.motivo == ""].index)  # ya ordenado por IV desc
corr = b.transform(train)[cand].corr().abs()
kept = []
for f in cand:
    hit = [k for k in kept if corr.loc[f, k] > CORR_MAX]
    if hit:
        s.loc[f, "motivo"] = f"corr > {CORR_MAX} con {hit[0]}"
    else:
        kept.append(f)
s["seleccionada"] = s.motivo == ""
s["fuerza"] = s.iv_train.map(iv_strength)

s.round(4).to_csv("reports/iv_train_oot.csv")
open("reports/selected_features.txt", "w").write("\n".join(kept) + "\n")
pd.concat(b.tables_, names=["feature", "bin"]).round(4).to_csv("reports/woe_tables.csv")
print(s[["iv_train", "iv_oot", "n_bins", "motivo"]].round(3).to_string())
print(f"\nSeleccionadas ({len(kept)}):", ", ".join(kept))
