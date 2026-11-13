# Robotic Process Automation

A automação de RPA do Pátio Monitor fica num repositório próprio:

🔗 **[RPABusGate_PatioMonitorGS2026](https://github.com/camilapadalino/RPABusGate_PatioMonitorGS2026)**: workflows no n8n que recebem, auditam e disponibilizam os eventos do Smart Bus Gate.

**Integração com este repositório:** a automação pode gravar no MVP pela API (`POST /api/conciliacao` ou `POST /api/posicoes`, com o header `X-API-Key`).
Formato em [`docs/contrato-api.md`](../docs/contrato-api.md).
