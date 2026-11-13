import os

os.environ["DATABASE_URL"] = "sqlite:///./test_patio.db"
os.environ["DEMO"] = "true"
os.environ["DEMO_INTERVALO_S"] = "3600"
os.environ["INGEST_API_KEY"] = "chave-de-teste"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

H = {"X-API-Key": "chave-de-teste"}


@pytest.fixture(scope="module")
def cli():
    if os.path.exists("test_patio.db"):
        os.remove("test_patio.db")
    with TestClient(app) as c:
        yield c


def test_health(cli):
    assert cli.get("/health").json()["status"] == "ok"


def test_posicoes_demo(cli):
    dados = cli.get("/posicoes").json()
    assert len(dados) >= 10
    assert {"prefixo", "local", "estado", "status_conciliacao"} <= dados[0].keys()


def test_post_posicao_exige_chave(cli):
    r = cli.post("/posicoes", json={"prefixo": "22001", "local": "V4", "fonte": "robo"})
    assert r.status_code == 401


def test_robo_move_onibus(cli):
    r = cli.post("/posicoes", headers=H, json={"prefixo": "22001", "local": "v4", "estado": "parado", "fonte": "robo"})
    assert r.status_code == 201, r.text
    assert r.json()["local"] == "V4"
    assert any(p["prefixo"] == "22001" for p in cli.get("/posicoes").json())


def test_regras_de_validacao(cli):
    assert cli.post("/posicoes", headers=H, json={"prefixo": "12", "local": "V1"}).status_code == 422
    assert cli.post("/posicoes", headers=H, json={"prefixo": "12345", "local": "X9"}).status_code == 422


def test_conciliacao_e_alertas(cli):
    r = cli.post("/conciliacao", headers=H, json=[{
        "viagem_id": "T-1", "linha": "8696-10", "prefixo_previsto": "22001",
        "saida_prevista": "2026-11-12T10:00:00Z", "status": "saida_sem_confirmacao"}])
    assert r.json() == {"gravados": 1}
    assert any(a["viagem_id"] == "T-1" for a in cli.get("/alertas").json())
    pos = {p["prefixo"]: p for p in cli.get("/posicoes").json()}
    assert pos["22001"]["status_conciliacao"] == "saida_sem_confirmacao"


def test_assistente_fallback(cli):
    r = cli.post("/assistente", json={"pergunta": "O ônibus não confirmou saída. O que faço?", "prefixo": "22001"})
    body = r.json()
    assert body["modo"] == "fallback_regras" and body["fonte"] and body["contexto_veiculo"]["prefixo"] == "22001"


def test_assistente_nao_consta(cli):
    body = cli.post("/assistente", json={"pergunta": "Qual a previsão do tempo amanhã?"}).json()
    assert body["acao"] == "nao_consta"


def test_metrics(cli):
    assert "http_request" in cli.get("/metrics").text


def test_rotas_tambem_em_api(cli):
    assert cli.get("/api/posicoes").json() == cli.get("/posicoes").json()


def test_front_servido_na_raiz(cli):
    r = cli.get("/")
    assert r.status_code == 200 and "Pátio Monitor" in r.text


def test_metrics_com_token(cli, monkeypatch):
    from app import config
    monkeypatch.setattr(config, "METRICS_TOKEN", "segredo")
    assert cli.get("/metrics").status_code == 401
    assert cli.get("/metrics", headers={"Authorization": "Bearer segredo"}).status_code == 200
