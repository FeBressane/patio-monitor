"""Contrato JSON da API. Ver docs/contrato-api.md: é o que visão, GenAI, RPA e o robô consomem."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from .layout import CODIGOS

Estado = Literal["parado", "manobrando", "em_viagem", "vaga_errada", "obstaculo"]
Fonte = Literal["gps", "robo", "camera", "portaria", "simulado", "manual"]
StatusConciliacao = Literal["ok", "atrasada", "saida_sem_confirmacao", "veiculo_trocado", "parado_vaga_errada"]

PREFIXO_REGEX = r"^\d{5}$"  # prefixo SPTrans: 5 dígitos (mesma regra de qualidade da Prata)


class PosicaoIn(BaseModel):
    prefixo: str = Field(pattern=PREFIXO_REGEX, examples=["12345"])
    local: str = Field(examples=["V3"], description="Código do layout (PORTAO, V1..V12, P1..P4, CIRCULACAO, FORA)")
    estado: Estado = "parado"
    fonte: Fonte = "robo"
    linha: str | None = Field(default=None, examples=["8696-10"])
    lat: float | None = None
    lon: float | None = None
    registrado_em: datetime | None = Field(default=None, description="Hora do evento na origem; vazio = agora")

    @field_validator("local")
    @classmethod
    def local_valido(cls, v: str) -> str:
        v = v.upper()
        if v not in CODIGOS:
            raise ValueError(f"local desconhecido: {v}")
        return v


class PosicaoOut(BaseModel):
    prefixo: str
    linha: str | None
    local: str
    estado: str
    fonte: str
    lat: float | None
    lon: float | None
    entrou_em: datetime | None
    minutos_no_patio: int | None
    atualizado_em: datetime
    status_conciliacao: str | None = None


class ConciliacaoIn(BaseModel):
    viagem_id: str = Field(examples=["8696-10-0-0615"])
    linha: str | None = None
    prefixo_previsto: str | None = None
    prefixo_registrado: str | None = None
    saida_prevista: datetime
    saida_registrada: datetime | None = None
    status: StatusConciliacao
    detalhe: str | None = None
    origem: str = "rpa"


class ConciliacaoOut(ConciliacaoIn):
    atualizado_em: datetime


class AssistenteIn(BaseModel):
    pergunta: str = Field(min_length=3, max_length=1000,
                          examples=["O ônibus 12345 não confirmou saída há 15 min. O que faço?"])
    prefixo: str | None = Field(default=None, pattern=PREFIXO_REGEX)


class AssistenteOut(BaseModel):
    """Formato combinado com GenAI. Quando a base não cobre o caso, acao = "nao_consta"."""
    acao: str
    justificativa: str
    fonte: str | None
    confianca: float = Field(ge=0, le=1)
    modo: str = Field(description="llm_rag (serviço de GenAI) ou fallback_regras")
    contexto_veiculo: dict | None = None
