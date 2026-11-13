# Databricks notebook source
# MAGIC %md
# MAGIC # 02 · Prata: limpeza, 3 regras de qualidade e MERGE sem duplicar
# MAGIC Chave das posições: (`prefixo_veiculo`, `data_hora`). Cada regra conta quantas linhas barrou.

# COMMAND ----------

spark.sql("USE workspace.patio")
LAT0, LON0, RAIO_PATIO_M = -23.4889, -46.7262, 250  # mesmo centro/raio da API e do gerador

# Distância em metros (haversine) em SQL, reaproveitada nas regras
DIST = f"""2 * 6371000 * asin(sqrt(pow(sin(radians(lat - {LAT0}) / 2), 2)
          + cos(radians({LAT0})) * cos(radians(lat)) * pow(sin(radians(lon - {LON0}) / 2), 2)))"""

# COMMAND ----------

# MAGIC %md ## Posições (Olho Vivo)

# COMMAND ----------

spark.sql(f"""
CREATE OR REPLACE TEMP VIEW posicoes_tipadas AS
SELECT
  CAST(prefixo AS STRING)                         AS prefixo_veiculo,
  CAST(letreiro AS STRING)                        AS linha,
  CAST(cod_linha AS INT)                          AS cod_linha,
  CAST(sentido AS INT)                            AS sentido,
  to_timestamp(data_hora)                         AS data_hora,
  CAST(lat AS DOUBLE)                             AS lat,
  CAST(lon AS DOUBLE)                             AS lon,
  arquivo_origem
FROM bronze_posicoes
""")

spark.sql(f"""
CREATE OR REPLACE TEMP VIEW posicoes_avaliadas AS
SELECT *,
  CASE
    WHEN prefixo_veiculo IS NULL OR NOT prefixo_veiculo RLIKE '^[0-9]{{5}}$' THEN 'R2_prefixo_invalido'
    WHEN lat IS NULL OR lon IS NULL OR {DIST} > {RAIO_PATIO_M}           THEN 'R1_fora_do_raio'
  END AS regra_violada
FROM posicoes_tipadas
""")

spark.sql("""
CREATE TABLE IF NOT EXISTS prata_posicoes (
  prefixo_veiculo STRING, linha STRING, cod_linha INT, sentido INT,
  data_hora TIMESTAMP, lat DOUBLE, lon DOUBLE, arquivo_origem STRING, atualizado_em TIMESTAMP)
""")

spark.sql("""
MERGE INTO prata_posicoes AS p
USING (
  SELECT * EXCEPT (regra_violada, rn) FROM (
    SELECT *, row_number() OVER (PARTITION BY prefixo_veiculo, data_hora ORDER BY arquivo_origem DESC) AS rn
    FROM posicoes_avaliadas WHERE regra_violada IS NULL) WHERE rn = 1
) AS n
ON p.prefixo_veiculo = n.prefixo_veiculo AND p.data_hora = n.data_hora
WHEN MATCHED THEN UPDATE SET linha = n.linha, lat = n.lat, lon = n.lon, arquivo_origem = n.arquivo_origem,
                             atualizado_em = current_timestamp()
WHEN NOT MATCHED THEN INSERT (prefixo_veiculo, linha, cod_linha, sentido, data_hora, lat, lon, arquivo_origem, atualizado_em)
  VALUES (n.prefixo_veiculo, n.linha, n.cod_linha, n.sentido, n.data_hora, n.lat, n.lon, n.arquivo_origem, current_timestamp())
""")

# COMMAND ----------

# MAGIC %md ## Portaria e escala (simuladas, regra em `bigdata/scripts/gerar_portaria.py`)

# COMMAND ----------

spark.sql("""
CREATE OR REPLACE TEMP VIEW portaria_avaliada AS
SELECT
  CAST(registro_id AS STRING) AS registro_id, CAST(prefixo AS STRING) AS prefixo_veiculo,
  CAST(linha AS STRING) AS linha, CAST(vaga AS STRING) AS vaga,
  to_timestamp(entrada) AS entrada, to_timestamp(nullif(CAST(saida AS STRING), '')) AS saida,
  CAST(matricula_motorista AS STRING) AS matricula_motorista, CAST(nome_motorista AS STRING) AS nome_motorista,
  CASE
    WHEN prefixo IS NULL OR NOT CAST(prefixo AS STRING) RLIKE '^[0-9]{5}$' THEN 'R2_prefixo_invalido'
    WHEN to_timestamp(nullif(CAST(saida AS STRING), '')) < to_timestamp(entrada) THEN 'R3_saida_antes_da_entrada'
  END AS regra_violada
FROM bronze_portaria
""")

spark.sql("""
CREATE OR REPLACE TABLE prata_portaria AS
SELECT * EXCEPT (regra_violada) FROM portaria_avaliada WHERE regra_violada IS NULL
QUALIFY row_number() OVER (PARTITION BY registro_id ORDER BY entrada) = 1
""")

spark.sql("""
CREATE OR REPLACE TABLE prata_escala AS
SELECT CAST(viagem_id AS STRING) AS viagem_id, CAST(linha AS STRING) AS linha,
       CAST(prefixo_previsto AS STRING) AS prefixo_previsto, CAST(vaga_prevista AS STRING) AS vaga_prevista,
       to_timestamp(saida_prevista) AS saida_prevista
FROM bronze_escala
QUALIFY row_number() OVER (PARTITION BY viagem_id ORDER BY saida_prevista) = 1
""")

# COMMAND ----------

# MAGIC %md ### Linhas barradas por regra (evidência do requisito de qualidade)

# COMMAND ----------

display(spark.sql("""
SELECT 'posicoes' AS origem, regra_violada AS regra, count(*) AS linhas_barradas
FROM posicoes_avaliadas WHERE regra_violada IS NOT NULL GROUP BY 1, 2
UNION ALL
SELECT 'portaria', regra_violada, count(*) FROM portaria_avaliada WHERE regra_violada IS NOT NULL GROUP BY 1, 2
ORDER BY 1, 2
"""))
display(spark.sql("SELECT count(*) AS linhas_prata_posicoes FROM prata_posicoes"))
