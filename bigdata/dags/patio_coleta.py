"""DAG patio_coleta: coleta horária das fontes do Pátio Monitor.

- Olho Vivo (SPTrans): posições atuais, filtradas por raio em volta do Terminal Pirituba.
  A API só devolve o "agora", por isso @hourly e catchup=False (não existe histórico para reprocessar).
- GTFS (SPTrans): trips e stop_times, 1x por dia (o arquivo muda pouco).
- Open-Meteo: chuva e temperatura por hora no terminal, 1x por dia (fonte complementar).
As três coletas rodam em paralelo e depois conferir_chegada valida o que caiu em chegada/.

Variables do Airflow (nada de token no código nem no repositório):
  sptrans_token        token gratuito do portal do desenvolvedor da SPTrans
  gtfs_zip_url         URL (ou caminho local) do GTFS baixado do portal da SPTrans
  patio_chegada_dir    pasta de destino (padrão: /opt/airflow/chegada)
"""
from __future__ import annotations

import io
import json
import math
import zipfile
from datetime import datetime, timedelta
from pathlib import Path

import pendulum
import requests
from airflow.decorators import dag, task
from airflow.exceptions import AirflowSkipException
from airflow.models import Variable

TZ = pendulum.timezone("America/Sao_Paulo")
CENTRO = (-23.4889, -46.7262)  # Terminal Pirituba (aproximado, conferir)
RAIO_M = 1500                  # raio da coleta; a Prata aplica o raio menor do pátio
OLHO_VIVO = "https://api.olhovivo.sptrans.com.br/v2.1"


def _dir() -> Path:
    d = Path(Variable.get("patio_chegada_dir", default_var="/opt/airflow/chegada"))
    d.mkdir(parents=True, exist_ok=True)
    return d


def _nome(fonte: str, ext: str, ts: datetime) -> Path:
    return _dir() / f"{fonte}_{ts.astimezone(TZ):%Y%m%d_%H%M}.{ext}"


def _dist_m(lat1, lon1, lat2, lon2) -> float:
    r = 6_371_000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    return 2 * r * math.asin(math.sqrt(math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2))


def _ja_coletado_hoje(fonte: str, ts: datetime) -> bool:
    """Fontes diárias: a primeira execução do dia coleta, as outras pulam."""
    return any(_dir().glob(f"{fonte}_{ts.astimezone(TZ):%Y%m%d}_*"))


@dag(
    dag_id="patio_coleta",
    schedule="@hourly",
    start_date=pendulum.datetime(2026, 11, 10, tz=TZ),
    catchup=False,
    max_active_runs=1,
    default_args={"retries": 2, "retry_delay": timedelta(minutes=3)},
    tags=["patio-monitor", "gs2026"],
)
def patio_coleta():

    @task
    def coletar_olho_vivo(data_interval_end=None) -> str:
        s = requests.Session()
        r = s.post(f"{OLHO_VIVO}/Login/Autenticar", params={"token": Variable.get("sptrans_token")}, timeout=20)
        r.raise_for_status()
        if r.text.strip().lower() != "true":
            raise RuntimeError("Falha na autenticação da Olho Vivo (confira a Variable sptrans_token)")
        r = s.get(f"{OLHO_VIVO}/Posicao", timeout=60)
        r.raise_for_status()
        dados = r.json()
        linhas = []
        for linha in dados.get("l", []):
            for v in linha.get("vs", []):
                if _dist_m(CENTRO[0], CENTRO[1], v["py"], v["px"]) <= RAIO_M:
                    linhas.append({
                        "hr_consulta": dados.get("hr"), "letreiro": linha.get("c"), "cod_linha": linha.get("cl"),
                        "sentido": linha.get("sl"), "prefixo": v.get("p"), "acessivel": v.get("a"),
                        "data_hora": v.get("ta"), "lat": v.get("py"), "lon": v.get("px"),
                    })
        destino = _nome("olhovivo", "json", data_interval_end or pendulum.now(TZ))
        destino.write_text(json.dumps(linhas, ensure_ascii=False), encoding="utf-8")
        return str(destino)

    @task
    def coletar_gtfs(data_interval_end=None) -> str:
        ts = data_interval_end or pendulum.now(TZ)
        if _ja_coletado_hoje("gtfs_trips", ts):
            raise AirflowSkipException("GTFS já coletado hoje (fonte diária)")
        origem = Variable.get("gtfs_zip_url")
        if not origem.startswith("http") and not Path(origem).exists():
            # O GTFS exige login no portal da SPTrans e é baixado à mão. Sem ele, a coleta de posições
            # (que não tem histórico e não pode esperar) continua; o aviso fica no log da tarefa.
            raise AirflowSkipException(f"GTFS ainda não disponível em {origem}: baixe no portal da SPTrans")
        conteudo = Path(origem).read_bytes() if Path(origem).exists() else requests.get(origem, timeout=120).content
        with zipfile.ZipFile(io.BytesIO(conteudo)) as z:
            for arq in ("trips.txt", "stop_times.txt", "routes.txt"):
                _nome(f"gtfs_{arq.removesuffix('.txt')}", "csv", ts).write_bytes(z.read(arq))
        return str(_dir())

    @task
    def coletar_clima(data_interval_end=None) -> str:
        ts = data_interval_end or pendulum.now(TZ)
        if _ja_coletado_hoje("clima", ts):
            raise AirflowSkipException("Clima já coletado hoje (fonte diária)")
        r = requests.get("https://api.open-meteo.com/v1/forecast", timeout=30, params={
            "latitude": CENTRO[0], "longitude": CENTRO[1], "timezone": "America/Sao_Paulo",
            "hourly": "precipitation,temperature_2m", "past_days": 1, "forecast_days": 1})
        r.raise_for_status()
        destino = _nome("clima", "json", ts)
        destino.write_text(r.text, encoding="utf-8")
        return str(destino)

    @task(trigger_rule="none_failed")
    def conferir_chegada(data_interval_end=None) -> dict:
        ts = (data_interval_end or pendulum.now(TZ)).astimezone(TZ)
        sufixo = f"{ts:%Y%m%d_%H%M}"
        arquivos = sorted(p.name for p in _dir().glob(f"*_{sufixo}.*"))
        ov = _dir() / f"olhovivo_{sufixo}.json"
        if not ov.exists() or ov.stat().st_size == 0:
            raise ValueError(f"Arquivo da Olho Vivo ausente ou vazio: {ov.name}")
        n = len(json.loads(ov.read_text(encoding="utf-8")))
        print(f"chegada OK: {arquivos} | posições no raio: {n}")
        return {"arquivos": arquivos, "posicoes": n}

    [coletar_olho_vivo(), coletar_gtfs(), coletar_clima()] >> conferir_chegada()


patio_coleta()
