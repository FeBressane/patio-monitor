# Maker Lab

Pasta do robô físico da maquete (ESP32 + leitor RFID nas vagas).

**O que vai aqui:** firmware (`.ino`/PlatformIO), esquema elétrico, lista de materiais, fotos da maquete e o PDF da disciplina
(com nome completo e RM de todos — sem isso a nota zera).

**Integração com a API:** cada leitura de tag vira um `POST /api/posicoes` com `"fonte": "robo"` e o header `X-API-Key`.
Sem Wi-Fi, guardar os eventos em fila local com `registrado_em` e reenviar depois.
Detalhes em [`docs/contrato-api.md`](../docs/contrato-api.md#robô-do-maker-lab-e-visão-post-posicoes).

> Pendente: código desta disciplina.
