-- Limpieza: tipos explícitos, definición de default y variables disponibles al otorgar el crédito.
-- Entrada: loans_raw (01). Salida: loans.
--
-- DEFINICIÓN DE DEFAULT (target)
--   1 = Charged Off, Default, Late (31-120 days)   -> pérdida o mora > 30 días (camino a 90+)
--   0 = Fully Paid
--   NULL = resultado aún desconocido: Current, In Grace Period, Late (16-30 days)
--   Excluidos: 'Does not meet the credit policy' (otra política de aprobación) y filas sin id válido.
--
-- FUGA DE INFORMACIÓN: se excluyen columnas que solo existen después de la originación
--   (pagos, recuperaciones, saldos pendientes, last_*, hardship_*, settlement_*, debt_settlement_flag).
-- Se excluyen también: texto libre / identificadores (url, desc, title, emp_title, member_id),
--   zip_code (proxy geográfico de variables sensibles) y columnas de co-deudor (casi todas vacías).
-- OJO: grade, sub_grade e int_rate son salidas del modelo de Lending Club. Se guardan para comparar,
--   pero usarlas como predictores significa "aprender el score de otro". Decisión en la fase de modelo.

CREATE OR REPLACE TABLE loans AS
WITH base AS (
    SELECT *, strptime(issue_d, '%b-%Y')::DATE AS issue_date
    FROM loans_raw
    WHERE try_cast(id AS BIGINT) IS NOT NULL
      AND loan_status NOT LIKE 'Does not meet the credit policy%'
)
SELECT
    -- Identificación y tiempo
    id::BIGINT                                              AS id,
    issue_date,
    year(issue_date)                                        AS issue_year,
    loan_status,
    CASE
        WHEN loan_status IN ('Charged Off', 'Default', 'Late (31-120 days)') THEN 1
        WHEN loan_status = 'Fully Paid' THEN 0
    END                                                     AS target,

    -- Condiciones del préstamo
    try_cast(loan_amnt AS DOUBLE)                           AS loan_amnt,
    try_cast(regexp_extract(term, '\d+') AS INTEGER)        AS term_months,
    try_cast(installment AS DOUBLE)                         AS installment,
    purpose,
    application_type,
    initial_list_status,

    -- Precio / score de Lending Club (ver nota arriba)
    grade,
    sub_grade,
    try_cast(replace(int_rate, '%', '') AS DOUBLE)          AS int_rate,

    -- Solicitante
    CASE
        WHEN emp_length = '< 1 year' THEN 0
        WHEN emp_length = '10+ years' THEN 10
        ELSE try_cast(regexp_extract(emp_length, '\d+') AS INTEGER)
    END                                                     AS emp_length_years,
    home_ownership,
    nullif(try_cast(annual_inc AS DOUBLE), 0)               AS annual_inc,   -- 0 = inválido (D4)
    verification_status,
    addr_state,
    CASE WHEN try_cast(dti AS DOUBLE) BETWEEN 0 AND 100
         THEN try_cast(dti AS DOUBLE) END                   AS dti,          -- <0 o >100 = inválido (D4)

    -- Buró de crédito (fotografía al momento de la solicitud)
    try_cast(fico_range_low AS DOUBLE)                      AS fico_low,
    try_cast(fico_range_high AS DOUBLE)                     AS fico_high,
    date_diff('month', strptime(earliest_cr_line, '%b-%Y')::DATE, issue_date)
                                                            AS credit_history_months,
    try_cast(delinq_2yrs AS INTEGER)                        AS delinq_2yrs,
    try_cast(inq_last_6mths AS INTEGER)                     AS inq_last_6mths,
    try_cast(mths_since_last_delinq AS INTEGER)             AS mths_since_last_delinq,
    try_cast(mths_since_last_record AS INTEGER)             AS mths_since_last_record,
    try_cast(open_acc AS INTEGER)                           AS open_acc,
    try_cast(total_acc AS INTEGER)                          AS total_acc,
    try_cast(pub_rec AS INTEGER)                            AS pub_rec,
    try_cast(pub_rec_bankruptcies AS INTEGER)               AS pub_rec_bankruptcies,
    try_cast(revol_bal AS DOUBLE)                           AS revol_bal,
    try_cast(replace(revol_util, '%', '') AS DOUBLE)        AS revol_util,
    try_cast(total_rev_hi_lim AS DOUBLE)                    AS total_rev_hi_lim,
    try_cast(tot_cur_bal AS DOUBLE)                         AS tot_cur_bal,
    try_cast(avg_cur_bal AS DOUBLE)                         AS avg_cur_bal,
    try_cast(bc_util AS DOUBLE)                             AS bc_util,
    try_cast(mort_acc AS INTEGER)                           AS mort_acc,
    try_cast(acc_open_past_24mths AS INTEGER)               AS acc_open_past_24mths,
    try_cast(num_tl_op_past_12m AS INTEGER)                 AS num_tl_op_past_12m,
    try_cast(percent_bc_gt_75 AS DOUBLE)                    AS percent_bc_gt_75,
    try_cast(pct_tl_nvr_dlq AS DOUBLE)                      AS pct_tl_nvr_dlq,
    try_cast(mths_since_recent_inq AS INTEGER)              AS mths_since_recent_inq,
    try_cast(mo_sin_old_rev_tl_op AS INTEGER)               AS mo_sin_old_rev_tl_op,
    try_cast(mo_sin_rcnt_tl AS INTEGER)                     AS mo_sin_rcnt_tl,
    try_cast(collections_12_mths_ex_med AS INTEGER)         AS collections_12_mths_ex_med,
    try_cast(tax_liens AS INTEGER)                          AS tax_liens
FROM base;
