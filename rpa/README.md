# RPA

Pasta do robô de conciliação (escala prevista × portaria × rastreamento).

**O que vai aqui:** fluxo/robô de RPA, entradas de exemplo, logs de amostra (`logs/amostra.log`) e o PDF da disciplina.
O `.gitignore` já bloqueia `rpa/logs/*.log` (menos a amostra) e `rpa/quarentena/`.

**Integração com a API:** o robô envia lotes para `POST /api/conciliacao` com o header `X-API-Key`.
Formato e valores de `status` em [`docs/contrato-api.md`](../docs/contrato-api.md#robô-de-rpa-post-conciliacao).
A portaria e a escala simuladas saem de `bigdata/scripts/gerar_portaria.py`.

> Pendente: código desta disciplina.
