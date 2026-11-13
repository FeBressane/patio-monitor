-- Databricks notebook source
-- MAGIC %md
-- MAGIC # 04 · As 5 consultas do relatório (item 08). Cada uma tem resultado + interpretação no PDF.

-- COMMAND ----------
USE workspace.patio;

-- COMMAND ----------
-- 1. Tempo médio de permanência por linha
SELECT linha, count(*) AS estadias, round(avg(minutos_parado), 1) AS media_min,
       round(percentile_approx(minutos_parado, 0.9), 1) AS p90_min
FROM fato_permanencia
WHERE entrada IS NOT NULL
GROUP BY linha
ORDER BY media_min DESC;

-- COMMAND ----------
-- 2. Viagens sem saída confirmada por dia
SELECT data, count_if(status_conciliacao = 'saida_sem_confirmacao') AS sem_confirmacao, count(*) AS viagens,
       round(100 * count_if(status_conciliacao = 'saida_sem_confirmacao') / count(*), 1) AS pct
FROM fato_permanencia
GROUP BY data
ORDER BY data;

-- COMMAND ----------
-- 3. Veículos parados há mais de X minutos (X = 45; ajuste no widget)
CREATE WIDGET TEXT x_minutos DEFAULT '45';

SELECT prefixo_veiculo, linha, vaga_registrada, entrada, minutos_parado
FROM fato_permanencia
WHERE saida IS NULL AND entrada IS NOT NULL AND minutos_parado > CAST(getArgument('x_minutos') AS DOUBLE)
ORDER BY minutos_parado DESC;

-- COMMAND ----------
-- 4. Divergências entre escala e portaria, por tipo
SELECT status_conciliacao AS tipo, count(*) AS ocorrencias,
       round(100 * count(*) / sum(count(*)) OVER (), 1) AS pct_do_total
FROM fato_permanencia
WHERE status_conciliacao <> 'ok'
GROUP BY status_conciliacao
ORDER BY ocorrencias DESC;

-- COMMAND ----------
-- 5. Impacto: % de partidas no horário antes e depois da data em que os alertas foram ligados
CREATE WIDGET TEXT inicio_alertas DEFAULT '2026-11-15';

SELECT CASE WHEN data < CAST(getArgument('inicio_alertas') AS DATE) THEN '1_antes' ELSE '2_depois' END AS periodo,
       count(*) AS partidas,
       round(100 * count_if(status_conciliacao = 'ok') / count(*), 1) AS pct_no_horario
FROM fato_permanencia
GROUP BY 1
ORDER BY 1;

-- COMMAND ----------
-- Complementar: chuva x atraso (Open-Meteo só como fonte de apoio, não como exemplo sem adaptação)
WITH chuva AS (
  SELECT to_timestamp(h.time) AS hora, h.precipitation AS chuva_mm
  FROM (SELECT explode(arrays_zip(hourly.time, hourly.precipitation)) AS h FROM bronze_clima)
)
SELECT CASE WHEN c.chuva_mm > 0.5 THEN 'com chuva' ELSE 'sem chuva' END AS condicao,
       count(*) AS partidas, round(avg(f.atraso_min), 1) AS atraso_medio_min
FROM fato_permanencia f
JOIN chuva c ON date_trunc('HOUR', f.saida_prevista) = c.hora
WHERE f.atraso_min IS NOT NULL
GROUP BY 1;
