"""API do Pátio Monitor.

Endpoints combinados entre as disciplinas (contrato em docs/contrato-api.md):
  GET  /posicoes        estado atual de cada veículo (front 3D e lista acessível)
  POST /posicoes        evento do robô (Maker Lab), da câmera (Visão) ou do GPS
  GET  /conciliacao     resultado do robô de RPA
  POST /conciliacao     RPA grava um lote de viagens conciliadas
  GET  /alertas         pendências (status != ok)
  POST /assistente      pergunta ao assistente de GenAI
  GET  /permanencia     tabela Ouro (fato_permanencia) exportada do Databricks
  GET  /layout          vagas, plataformas e portão
  GET  /metrics         Prometheus (latência, tráfego, erros, saturação)
"""
import asyncio
import csv
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import assistente, config, demo
from .db import Conciliacao, EventoPosicao, VeiculoEstado, agora, criar_tabelas, get_db
from .layout import layout as obter_layout
from .schemas import AssistenteIn, AssistenteOut, ConciliacaoIn, ConciliacaoOut, PosicaoIn, PosicaoOut

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


@asynccontextmanager
async def lifespan(_: FastAPI):
    criar_tabelas()
    tarefa = None
    if config.DEMO:
        demo.popular()
        tarefa = asyncio.create_task(demo.loop_simulacao())
    yield
    if tarefa:
        tarefa.cancel()


app = FastAPI(title="Pátio Monitor API", version="0.1.0", lifespan=lifespan,
              description="Visão única do pátio para terminais e garagens de ônibus.")
app.add_middleware(CORSMiddleware, allow_origins=config.CORS_ORIGINS, allow_methods=["*"], allow_headers=["*"])
Instrumentator(excluded_handlers=["/metrics", "/api/metrics", "/health", "/api/health"]).instrument(app)
router = APIRouter()


@app.get("/metrics", include_in_schema=False)
def metrics(authorization: str | None = Header(default=None)):
    """Prometheus. Com METRICS_TOKEN definido (nuvem), exige 'Authorization: Bearer <token>'."""
    if config.METRICS_TOKEN and authorization != f"Bearer {config.METRICS_TOKEN}":
        raise HTTPException(status_code=401, detail="token de métricas inválido")
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


def exigir_chave(x_api_key: str | None = Header(default=None)) -> None:
    if config.INGEST_API_KEY and x_api_key != config.INGEST_API_KEY:
        raise HTTPException(status_code=401, detail="X-API-Key inválida")


def _utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt  # SQLite devolve sem fuso


def _status_por_prefixo(db: Session) -> dict[str, str]:
    """Pendência mais recente de cada prefixo (previsto ou registrado)."""
    out: dict[str, str] = {}
    for c in db.scalars(select(Conciliacao).where(Conciliacao.status != "ok").order_by(Conciliacao.atualizado_em)):
        for p in (c.prefixo_previsto, c.prefixo_registrado):
            if p:
                out[p] = c.status
    return out


def _posicao_out(v: VeiculoEstado, status: dict[str, str]) -> PosicaoOut:
    entrou = _utc(v.entrou_em)
    minutos = int((agora() - entrou).total_seconds() // 60) if entrou else None
    return PosicaoOut(prefixo=v.prefixo, linha=v.linha, local=v.local, estado=v.estado, fonte=v.fonte,
                      lat=v.lat, lon=v.lon, entrou_em=entrou, minutos_no_patio=minutos,
                      atualizado_em=_utc(v.atualizado_em), status_conciliacao=status.get(v.prefixo))


def _conc_out(c: Conciliacao) -> ConciliacaoOut:
    return ConciliacaoOut(viagem_id=c.viagem_id, linha=c.linha, prefixo_previsto=c.prefixo_previsto,
                          prefixo_registrado=c.prefixo_registrado, saida_prevista=_utc(c.saida_prevista),
                          saida_registrada=_utc(c.saida_registrada), status=c.status, detalhe=c.detalhe,
                          origem=c.origem, atualizado_em=_utc(c.atualizado_em))


@router.get("/health", tags=["infra"])
def health():
    return {"status": "ok", "demo": config.DEMO, "assistente_externo": bool(config.ASSISTENTE_URL)}


@router.get("/layout", tags=["pátio"])
def get_layout():
    return obter_layout()


@router.get("/posicoes", response_model=list[PosicaoOut], tags=["pátio"])
def listar_posicoes(db: Session = Depends(get_db)):
    status = _status_por_prefixo(db)
    return [_posicao_out(v, status) for v in db.scalars(select(VeiculoEstado).order_by(VeiculoEstado.prefixo))]


@router.get("/posicoes/{prefixo}/historico", tags=["pátio"])
def historico(prefixo: str, limite: int = Query(50, le=500), db: Session = Depends(get_db)):
    evs = db.scalars(select(EventoPosicao).where(EventoPosicao.prefixo == prefixo)
                     .order_by(EventoPosicao.registrado_em.desc()).limit(limite))
    return [{"local": e.local, "estado": e.estado, "fonte": e.fonte, "registrado_em": _utc(e.registrado_em)}
            for e in evs]


@router.post("/posicoes", response_model=PosicaoOut, status_code=201, tags=["ingestão"],
          dependencies=[Depends(exigir_chave)])
def registrar_posicao(p: PosicaoIn, db: Session = Depends(get_db)):
    t = p.registrado_em or agora()
    v = db.get(VeiculoEstado, p.prefixo)
    if v is None:
        v = VeiculoEstado(prefixo=p.prefixo)
        db.add(v)
    estava_fora = v.local in (None, "FORA")
    v.local, v.estado, v.fonte, v.atualizado_em = p.local, p.estado, p.fonte, t
    v.linha = p.linha or v.linha
    v.lat, v.lon = p.lat, p.lon
    if p.local == "FORA":
        v.entrou_em = None
    elif estava_fora or v.entrou_em is None:
        v.entrou_em = t
    db.add(EventoPosicao(prefixo=p.prefixo, local=p.local, estado=p.estado, fonte=p.fonte, registrado_em=t))
    db.commit()
    return _posicao_out(v, _status_por_prefixo(db))


@router.get("/conciliacao", response_model=list[ConciliacaoOut], tags=["conciliação"])
def listar_conciliacao(status: str | None = None, db: Session = Depends(get_db)):
    q = select(Conciliacao).order_by(Conciliacao.saida_prevista)
    if status:
        q = q.where(Conciliacao.status == status)
    return [_conc_out(c) for c in db.scalars(q)]


@router.post("/conciliacao", tags=["ingestão"], dependencies=[Depends(exigir_chave)])
def gravar_conciliacao(itens: list[ConciliacaoIn], db: Session = Depends(get_db)):
    for item in itens:
        db.merge(Conciliacao(**item.model_dump(), atualizado_em=agora()))
    db.commit()
    return {"gravados": len(itens)}


@router.get("/alertas", response_model=list[ConciliacaoOut], tags=["conciliação"])
def alertas(db: Session = Depends(get_db)):
    q = select(Conciliacao).where(Conciliacao.status != "ok").order_by(Conciliacao.saida_prevista)
    return [_conc_out(c) for c in db.scalars(q)]


@router.post("/assistente", response_model=AssistenteOut, tags=["assistente"])
async def perguntar(body: AssistenteIn, db: Session = Depends(get_db)):
    contexto = None
    if body.prefixo:
        v = db.get(VeiculoEstado, body.prefixo)
        if v:
            contexto = _posicao_out(v, _status_por_prefixo(db)).model_dump(mode="json")
    return await assistente.perguntar(body.pergunta, contexto)


@router.get("/permanencia", tags=["big data"])
def permanencia(limite: int = Query(200, le=5000)):
    """Lê o export da Ouro. Nunca expõe colunas de motorista (só o hash fica na Ouro)."""
    if not config.OURO_CSV.exists():
        return {"fonte": None, "linhas": []}
    with config.OURO_CSV.open(encoding="utf-8") as f:
        linhas = [{k: v for k, v in row.items() if "motorista" not in k} for _, row in zip(range(limite), csv.DictReader(f))]
    return {"fonte": config.OURO_CSV.name, "linhas": linhas}


# Mesmas rotas na raiz (Docker: nginx tira o /api) e em /api (App Service: front e API no mesmo app).
app.include_router(router)
app.include_router(router, prefix="/api", include_in_schema=False)
if config.FRONT_DIR.is_dir() and (config.FRONT_DIR / "index.html").exists():
    app.mount("/", StaticFiles(directory=config.FRONT_DIR, html=True), name="front")
