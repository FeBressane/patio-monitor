# Contrato da API do Pátio Monitor

Este é o contrato que as outras disciplinas usam. Mudanças nele precisam ser combinadas com a equipe.
A documentação interativa fica em `/api/docs` na URL pública e em `http://localhost:8000/docs` quando a API roda localmente.

**Autenticação dos POSTs de ingestão:** header `X-API-Key: <INGEST_API_KEY>`. A chave é passada à equipe em canal privado e nunca vai para o Git.

**Códigos de local** (os mesmos para tag RFID, zona da câmera, portaria e 3D):
`PORTAO`, `V1` a `V12` (vagas), `P1` a `P4` (plataformas), `CIRCULACAO` (manobrando na faixa), `FORA` (em viagem).

**Prefixo:** 5 dígitos, como na SPTrans (ex.: `"11204"`). Um prefixo fora desse formato recebe `422`.

---

## Robô do Maker Lab e Visão: `POST /posicoes`

```json
{
  "prefixo": "11204",
  "local": "V3",
  "estado": "parado",
  "fonte": "robo",
  "linha": "8622-10",
  "registrado_em": "2026-11-15T14:02:00-03:00"
}
```

| Campo | Valores |
|---|---|
| `estado` | `parado`, `manobrando`, `em_viagem`, `vaga_errada`, `obstaculo` |
| `fonte` | `robo` (Maker Lab), `camera` (Visão), `gps`, `portaria`, `manual` |
| `registrado_em` | opcional; se vier vazio, a API usa a hora em que recebeu o evento |

A resposta é `201` com o estado atualizado do veículo. O ônibus se move no pátio 3D em até 3 s.

**Robô sem Wi-Fi:** guarde os eventos numa fila local com `registrado_em` preenchido e reenvie quando a conexão voltar.

```bash
curl -X POST https://<URL>/api/posicoes -H "Content-Type: application/json" -H "X-API-Key: $CHAVE" \
  -d '{"prefixo":"11204","local":"V3","estado":"parado","fonte":"camera"}'
```

## Robô de RPA: `POST /conciliacao`

Envie um lote (lista). Se o `viagem_id` já existir, o registro é substituído (upsert), então reenviar não duplica.

```json
[
  {
    "viagem_id": "8622-10-202611151400-3",
    "linha": "8622-10",
    "prefixo_previsto": "11203",
    "prefixo_registrado": null,
    "saida_prevista": "2026-11-15T14:00:00-03:00",
    "saida_registrada": null,
    "status": "saida_sem_confirmacao",
    "detalhe": "Sem registro na portaria 15 min após o previsto"
  }
]
```

`status`: `ok`, `atrasada`, `saida_sem_confirmacao`, `veiculo_trocado`, `parado_vaga_errada`.
A resposta é `{"gravados": N}`. Tudo que não for `ok` aparece em `GET /alertas` e pinta o ônibus de laranja no 3D.

## Assistente de GenAI: `POST /assistente`

O front chama a API. A API repassa ao serviço de GenAI quando `ASSISTENTE_URL` está configurada.

**O que a API envia ao serviço de GenAI** (`POST ASSISTENTE_URL`):

```json
{
  "pergunta": "Por que o ônibus 11203 está com alerta de Saída sem confirmação? O que faço?",
  "contexto": {
    "prefixo": "11203", "linha": "8622-10", "local": "V3", "estado": "parado",
    "minutos_no_patio": 42, "status_conciliacao": "saida_sem_confirmacao"
  }
}
```

**O que o serviço de GenAI devolve:**

```json
{
  "acao": "Contatar o portão por rádio e conferir se o veículo passou sem registro.",
  "justificativa": "…",
  "fonte": "POP do pátio §1",
  "confianca": 0.82
}
```

Quando a base não cobre o caso, a resposta é `"acao": "nao_consta"`. Se o serviço cair ou demorar mais de 20 s, a API responde com regras do POP simulado e marca `"modo": "fallback_regras"`. Os logs não guardam o nome do motorista.

## Leitura (front, Grafana, pitch)

| Endpoint | O que devolve |
|---|---|
| `GET /posicoes` | estado atual de cada veículo, com `minutos_no_patio` e `status_conciliacao` |
| `GET /posicoes/{prefixo}/historico` | últimos eventos do veículo |
| `GET /alertas` | pendências (status diferente de `ok`) |
| `GET /conciliacao?status=atrasada` | conciliação completa, com filtro opcional |
| `GET /permanencia` | export da tabela Ouro `fato_permanencia` (sem colunas de motorista) |
| `GET /layout` | vagas, plataformas e portão, com as coordenadas do 3D |
| `GET /health` | status da API |
