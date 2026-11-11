"""API de scoring del modelo PD oficial (D23).
Ejecutar local: uv run uvicorn main:app --app-dir api --reload  ·  Docs: http://localhost:8000/docs"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel, Field

from scorer import Scorecard

MODEL_PATH = Path(os.getenv("MODEL_PATH", Path(__file__).resolve().parents[1] / "models" / "scorecard_v1.json"))
scorecard = Scorecard.load(MODEL_PATH)

app = FastAPI(title="Credit Risk PD API", version=scorecard.spec["version"],
              description="PD de originación (préstamos a 36 meses) con dominio de aplicación y motivos de rechazo.")


# Valores válidos de Lending Club; un valor fuera de la lista -> error 422 (no se asigna en silencio a OTHER)
HomeOwnership = Literal["MORTGAGE", "OWN", "RENT", "OTHER", "NONE", "ANY"]
Purpose = Literal["debt_consolidation", "credit_card", "home_improvement", "other", "major_purchase",
                  "small_business", "car", "medical", "moving", "vacation", "house", "wedding",
                  "renewable_energy", "educational"]


class Applicant(BaseModel):
    """Datos de la solicitud y del buró al momento de originar. Los campos faltantes se tratan como 'MISSING'."""
    fico_low: float = Field(..., ge=300, le=850, description="FICO (límite inferior del rango)")
    dti: float = Field(..., ge=0, le=100, description="Deuda / ingreso mensual (%)")
    annual_inc: float | None = Field(None, gt=0, description="Ingreso anual (USD)")
    avg_cur_bal: float | None = Field(None, ge=0, description="Saldo promedio de las cuentas actuales")
    acc_open_past_24mths: int | None = Field(None, ge=0, description="Cuentas abiertas en 24 meses")
    num_tl_op_past_12m: int | None = Field(None, ge=0, description="Cuentas abiertas en 12 meses")
    mo_sin_rcnt_tl: int | None = Field(None, ge=0, description="Meses desde la cuenta más reciente")
    mo_sin_old_rev_tl_op: int | None = Field(None, ge=0, description="Meses desde la cuenta rotativa más antigua")
    mths_since_recent_inq: int | None = Field(None, ge=0, description="Meses desde la última consulta")
    percent_bc_gt_75: float | None = Field(None, ge=0, le=100, description="% de tarjetas con uso > 75%")
    revol_util: float | None = Field(None, ge=0, description="Uso del cupo rotativo (%)")
    home_ownership: HomeOwnership | None = Field(None, description="Tipo de vivienda (valores de Lending Club)")
    purpose: Purpose | None = Field(None, description="Propósito del préstamo (valores de Lending Club)")

    model_config = {"json_schema_extra": {"example": {
        "fico_low": 690, "dti": 18.5, "annual_inc": 65000, "avg_cur_bal": 9000, "acc_open_past_24mths": 4,
        "num_tl_op_past_12m": 2, "mo_sin_rcnt_tl": 6, "mo_sin_old_rev_tl_op": 150, "mths_since_recent_inq": 5,
        "percent_bc_gt_75": 40, "revol_util": 55, "home_ownership": "RENT", "purpose": "debt_consolidation"}}}


class Reason(BaseModel):
    variable: str
    points_lost: float
    missing: bool = Field(description="True si el dato no se envió (se puntuó como faltante)")


class ScoreResponse(BaseModel):
    in_domain: bool = Field(description="False: fuera del dominio del modelo (FICO < 660 o DTI > 34,99) -> sin PD")
    pd: float | None = Field(description="PD de vida del préstamo (36 meses), recalibrada")
    score: int | None = Field(description="Puntos del scorecard (600 = odds 50:1, PDO 20)")
    reasons: list[Reason] = Field(description="Variables que más puntos restan (motivos de rechazo)")
    model_version: str


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/model")
def model_info() -> dict:
    s = scorecard.spec
    return {"version": s["version"], "description": s["description"], "domain": s["domain"],
            "variables": list(s["variables"]), "scaling": s["scaling"]}


@app.post("/score", response_model=ScoreResponse)
def score(applicant: Applicant) -> dict:
    return scorecard.score(applicant.model_dump())
