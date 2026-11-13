# Databricks notebook source
# MAGIC %md
# MAGIC # 01 · Bronze: ingestão incremental dos arquivos de `chegada/`
# MAGIC Os arquivos do Airflow sobem manualmente para o Volume (o Databricks Free não conecta no Airflow).
# MAGIC `COPY INTO` é idempotente: arquivo já carregado não entra de novo. Isso é o que as contagens provam.

# COMMAND ----------

CATALOGO, SCHEMA = "workspace", "patio"
VOLUME = f"/Volumes/{CATALOGO}/{SCHEMA}/chegada"
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOGO}.{SCHEMA}")
spark.sql(f"CREATE VOLUME IF NOT EXISTS {CATALOGO}.{SCHEMA}.chegada")
spark.sql(f"USE {CATALOGO}.{SCHEMA}")

FONTES = {
    # tabela bronze: (padrão do arquivo, formato, opções)
    "bronze_posicoes": ("olhovivo_*.json", "JSON", "'multiLine' = 'true'"),
    "bronze_portaria": ("portaria_*.csv", "CSV", "'header' = 'true'"),
    "bronze_escala": ("escala_*.csv", "CSV", "'header' = 'true'"),
    "bronze_gtfs_trips": ("gtfs_trips_*.csv", "CSV", "'header' = 'true'"),
    "bronze_gtfs_stop_times": ("gtfs_stop_times_*.csv", "CSV", "'header' = 'true'"),
    "bronze_clima": ("clima_*.json", "JSON", "'multiLine' = 'true'"),
}

# COMMAND ----------

def contagens():
    out = {}
    for t in FONTES:
        try:
            out[t] = spark.table(t).count()
        except Exception:
            out[t] = 0
    return out

antes = contagens()
display(spark.createDataFrame(list(antes.items()), "tabela string, linhas_antes long"))

# COMMAND ----------

for tabela, (padrao, formato, opcoes) in FONTES.items():
    spark.sql(f"CREATE TABLE IF NOT EXISTS {tabela}")
    spark.sql(f"""
        COPY INTO {tabela}
        FROM (SELECT *, _metadata.file_name AS arquivo_origem, current_timestamp() AS ingerido_em FROM '{VOLUME}')
        FILEFORMAT = {formato}
        PATTERN = '{padrao}'
        FORMAT_OPTIONS ({opcoes}, 'inferSchema' = 'true')
        COPY_OPTIONS ('mergeSchema' = 'true')
    """)

# COMMAND ----------

# MAGIC %md
# MAGIC ### Evidência para o relatório (item 07)
# MAGIC Rode este notebook 3 vezes e tire print desta célula em cada uma:
# MAGIC 1. depois do 1º lote, 2. depois de subir o 2º lote (outro dia), 3. rodando de novo sem arquivo novo (o número não muda).

# COMMAND ----------

depois = contagens()
display(spark.createDataFrame([(t, antes[t], depois[t], depois[t] - antes[t]) for t in FONTES],
                              "tabela string, antes long, depois long, novas long"))
display(spark.sql("SELECT arquivo_origem, count(*) AS linhas FROM bronze_posicoes GROUP BY 1 ORDER BY 1"))
