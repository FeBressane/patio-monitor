"""Modelo relacional da API (Postgres em produção, SQLite para rodar local sem Docker)."""
import os
from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from . import config

_args = {}
if config.DATABASE_URL.startswith("sqlite"):
    _args = {"check_same_thread": False}
    _arquivo = config.DATABASE_URL.split("sqlite:///", 1)[-1]
    if _arquivo and _arquivo != ":memory:":
        os.makedirs(os.path.dirname(os.path.abspath(_arquivo)), exist_ok=True)  # ex.: /home/data no App Service
engine = create_engine(config.DATABASE_URL, connect_args=_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def agora() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class VeiculoEstado(Base):
    """Último estado conhecido de cada veículo (o que o pátio 3D desenha)."""
    __tablename__ = "veiculo_estado"

    prefixo: Mapped[str] = mapped_column(String(10), primary_key=True)
    linha: Mapped[str | None] = mapped_column(String(20))
    local: Mapped[str] = mapped_column(String(20), default="FORA")
    estado: Mapped[str] = mapped_column(String(20), default="parado")
    fonte: Mapped[str] = mapped_column(String(20), default="simulado")
    lat: Mapped[float | None]
    lon: Mapped[float | None]
    entrou_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=agora)


class EventoPosicao(Base):
    """Histórico de eventos (robô, câmera, GPS, portaria). Sem dado pessoal."""
    __tablename__ = "evento_posicao"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    prefixo: Mapped[str] = mapped_column(String(10), index=True)
    local: Mapped[str] = mapped_column(String(20))
    estado: Mapped[str] = mapped_column(String(20))
    fonte: Mapped[str] = mapped_column(String(20))
    registrado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=agora, index=True)


class Conciliacao(Base):
    """Resultado do robô de RPA: viagem prevista x portaria x GPS."""
    __tablename__ = "conciliacao"

    viagem_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    linha: Mapped[str | None] = mapped_column(String(20))
    prefixo_previsto: Mapped[str | None] = mapped_column(String(10))
    prefixo_registrado: Mapped[str | None] = mapped_column(String(10))
    saida_prevista: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    saida_registrada: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(30), index=True)
    detalhe: Mapped[str | None] = mapped_column(Text)
    origem: Mapped[str] = mapped_column(String(20), default="rpa")
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=agora)


def criar_tabelas() -> None:
    Base.metadata.create_all(engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
