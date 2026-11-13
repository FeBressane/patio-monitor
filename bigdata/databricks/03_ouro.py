# Databricks notebook source
# MAGIC %md
# MAGIC # 03 · Ouro: modelo estrela do pátio
# MAGIC `fato_permanencia` + `dim_veiculo`, `dim_linha`, `dim_tempo`, `dim_local`.
# MAGIC LGPD: matrícula e nome do motorista só entram como SHA-256; o texto original não sai da Prata.

# COMMAND ----------

spark.sql("USE workspace.patio")
TOLERANCIA_ATRASO_MIN = 5

# COMMAND ----------

spark.sql("""
CREATE OR REPLACE TABLE dim_veiculo AS
SELECT prefixo_veiculo, min(primeira) AS visto_primeiro_em, max(ultima) AS visto_ultimo_em
FROM (
  SELECT prefixo_veiculo, min(data_hora) AS primeira, max(data_hora) AS ultima FROM prata_posicoes GROUP BY 1
  UNION ALL
  SELECT prefixo_veiculo, min(entrada), max(coalesce(saida, entrada)) FROM prata_portaria GROUP BY 1
) GROUP BY 1
""")

spark.sql("""
CREATE OR REPLACE TABLE dim_linha AS
SELECT DISTINCT linha FROM (SELECT linha FROM prata_posicoes UNION SELECT linha FROM prata_escala)
WHERE linha IS NOT NULL
""")

spark.sql("""
CREATE OR REPLACE TABLE dim_local AS
SELECT codigo, tipo FROM VALUES
  ('PORTAO', 'portao'),
  ('V1','vaga'),('V2','vaga'),('V3','vaga'),('V4','vaga'),('V5','vaga'),('V6','vaga'),
  ('V7','vaga'),('V8','vaga'),('V9','vaga'),('V10','vaga'),('V11','vaga'),('V12','vaga'),
  ('P1','plataforma'),('P2','plataforma'),('P3','plataforma'),('P4','plataforma') AS t(codigo, tipo)
""")

spark.sql("""
CREATE OR REPLACE TABLE dim_tempo AS
SELECT d AS data, year(d) AS ano, month(d) AS mes, day(d) AS dia, date_format(d, 'EEEE') AS dia_semana,
       dayofweek(d) IN (1, 7) AS fim_de_semana
FROM (SELECT explode(sequence(DATE'2026-11-01', DATE'2026-12-31')) AS d)
""")

# COMMAND ----------

spark.sql(f"""
CREATE OR REPLACE TABLE fato_permanencia AS
WITH base AS (
  SELECT e.viagem_id, e.linha, e.prefixo_previsto, e.vaga_prevista, e.saida_prevista,
         p.registro_id, p.prefixo_veiculo AS prefixo_registrado, p.vaga AS vaga_registrada,
         p.entrada, p.saida, p.matricula_motorista, p.nome_motorista
  FROM prata_escala e
  LEFT JOIN prata_portaria p
    ON p.linha = e.linha
   AND p.entrada <= e.saida_prevista + INTERVAL 30 MINUTES
   AND coalesce(p.saida, e.saida_prevista) >= e.saida_prevista - INTERVAL 60 MINUTES
  QUALIFY row_number() OVER (PARTITION BY e.viagem_id
          ORDER BY abs(unix_timestamp(coalesce(p.saida, p.entrada)) - unix_timestamp(e.saida_prevista))) = 1
)
SELECT
  viagem_id, linha, prefixo_previsto, prefixo_registrado,
  coalesce(prefixo_registrado, prefixo_previsto) AS prefixo_veiculo,
  vaga_prevista, vaga_registrada, entrada, saida, saida_prevista,
  CAST(to_date(saida_prevista) AS DATE) AS data,
  round((unix_timestamp(coalesce(saida, current_timestamp())) - unix_timestamp(entrada)) / 60, 1) AS minutos_parado,
  round((unix_timestamp(saida) - unix_timestamp(saida_prevista)) / 60, 1) AS atraso_min,
  CASE
    WHEN registro_id IS NULL OR saida IS NULL                            THEN 'saida_sem_confirmacao'
    WHEN prefixo_registrado <> prefixo_previsto                           THEN 'veiculo_trocado'
    WHEN vaga_registrada <> vaga_prevista                                 THEN 'parado_vaga_errada'
    WHEN saida > saida_prevista + INTERVAL {TOLERANCIA_ATRASO_MIN} MINUTES THEN 'atrasada'
    ELSE 'ok'
  END AS status_conciliacao,
  sha2(matricula_motorista, 256) AS motorista_matricula_hash,
  sha2(nome_motorista, 256)      AS motorista_nome_hash
FROM base
""")

display(spark.sql("SELECT status_conciliacao, count(*) AS viagens FROM fato_permanencia GROUP BY 1 ORDER BY 2 DESC"))

# COMMAND ----------

# MAGIC %md
# MAGIC ### Export para o MVP
# MAGIC Baixe o resultado abaixo como CSV e salve em `data/ouro/fato_permanencia.csv` e faça commit (o deploy leva o arquivo ao App Service).
# MAGIC A API serve esse arquivo em `GET /permanencia` (as colunas de hash do motorista não são expostas).

# COMMAND ----------

display(spark.sql("""
SELECT viagem_id, linha, prefixo_veiculo, prefixo_previsto, prefixo_registrado, vaga_prevista, vaga_registrada,
       entrada, saida, saida_prevista, minutos_parado, atraso_min, status_conciliacao
FROM fato_permanencia ORDER BY saida_prevista DESC
"""))
