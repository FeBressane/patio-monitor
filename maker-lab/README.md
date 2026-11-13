# Project-Based Maker Lab

O protótipo físico do Pátio Monitor fica num repositório próprio:

🔗 **[SmartBusGate_PatioMonitorGS26](https://github.com/camilapadalino/SmartBusGate_PatioMonitorGS26)**: o Smart Bus Gate, uma cancela inteligente com ESP32, sensor ultrassônico HC-SR04, sensor PIR, servomotor e modelo de Machine Learning, simulada no Wokwi.

**Integração com este repositório:** cada evento da cancela pode virar um `POST /api/posicoes` (por exemplo, `"local": "PORTAO"`) com o header `X-API-Key`.
Detalhes em [`docs/contrato-api.md`](../docs/contrato-api.md).
