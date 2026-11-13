# Computer Vision — Gabriel Teixeira (RM 551570)

Pasta do detector YOLO de veículos no pátio.

**O que vai aqui:** notebook/script de treino, dataset (ou link, se for grande), pesos do modelo (ou link), script de inferência e o PDF da disciplina.

**Integração com a API:** cada detecção vira um `POST /api/posicoes` com `"fonte": "camera"` e o header `X-API-Key`.
Códigos de local (`PORTAO`, `V1`–`V12`, `P1`–`P4`, `CIRCULACAO`, `FORA`) em [`docs/contrato-api.md`](../docs/contrato-api.md).

> Pendente: código do Gabriel. Base reaproveitável: tracker YOLO do CP4 de ACV.
