"""Dados de DEMONSTRAÇÃO (simulados). Prefixos e linhas fictícios, sem nenhum dado pessoal.

A simulação só mexe em veículos com fonte="simulado". Quando o robô, a câmera ou o GPS
mandam um evento, aquele veículo passa a ter outra fonte e a simulação o deixa em paz.
"""
import asyncio
import logging
import random
from datetime import timedelta

from sqlalchemy import select

from . import config
from .db import Conciliacao, EventoPosicao, SessionLocal, VeiculoEstado, agora

log = logging.getLogger("patio.demo")

VAGAS = [f"V{i}" for i in range(1, 13)]
PLATAFORMAS = [f"P{i}" for i in range(1, 5)]

FROTA = [  # prefixo, linha, local inicial, estado inicial
    ("11201", "8696-10", "V1", "parado"), ("11202", "8696-10", "V2", "parado"),
    ("11203", "8622-10", "V3", "parado"), ("11204", "8622-10", "P1", "parado"),
    ("11205", "9301-10", "V5", "parado"), ("11206", "9301-10", "CIRCULACAO", "manobrando"),
    ("11207", "8615-10", "V8", "vaga_errada"), ("11208", "8615-10", "P3", "parado"),
    ("11209", "N531-11", "V10", "parado"), ("11210", "8696-10", "FORA", "em_viagem"),
]


def popular() -> None:
    with SessionLocal() as db:
        if db.scalar(select(VeiculoEstado).limit(1)):
            return
        t = agora()
        for i, (pref, linha, local, estado) in enumerate(FROTA):
            entrou = None if local == "FORA" else t - timedelta(minutes=8 + i * 7)
            db.add(VeiculoEstado(prefixo=pref, linha=linha, local=local, estado=estado,
                                 fonte="simulado", entrou_em=entrou, atualizado_em=t))
            db.add(EventoPosicao(prefixo=pref, local=local, estado=estado, fonte="simulado", registrado_em=t))
        viagens = [
            ("8696-10-0-A", "8696-10", "11210", "11210", -40, -38, "ok", None),
            ("8622-10-0-A", "8622-10", "11203", None, -15, None, "saida_sem_confirmacao",
             "Saída prevista há 15 min sem registro na portaria; GPS indica veículo na V3."),
            ("8615-10-0-A", "8615-10", "11207", None, 10, None, "parado_vaga_errada",
             "Escalado para V7, detectado na V8."),
            ("9301-10-0-A", "9301-10", "11205", "11206", -5, -4, "veiculo_trocado",
             "Escala previa 11205; portaria registrou 11206."),
            ("N531-11-0-A", "N531-11", "11209", None, -9, None, "atrasada",
             "Saída 9 min atrasada; veículo ainda na V10."),
            ("8696-10-0-B", "8696-10", "11201", None, 25, None, "ok", "Dentro do horário."),
        ]
        for vid, linha, pp, pr, prev_min, reg_min, status, det in viagens:
            db.add(Conciliacao(viagem_id=vid, linha=linha, prefixo_previsto=pp, prefixo_registrado=pr,
                               saida_prevista=t + timedelta(minutes=prev_min),
                               saida_registrada=None if reg_min is None else t + timedelta(minutes=reg_min),
                               status=status, detalhe=det, origem="simulado", atualizado_em=t))
        db.commit()
        log.info("banco populado com dados de demonstração")


def _passo() -> None:
    with SessionLocal() as db:
        simulados = db.scalars(select(VeiculoEstado).where(VeiculoEstado.fonte == "simulado")).all()
        if not simulados:
            return
        v = random.choice(simulados)
        ocupados = {x.local for x in db.scalars(select(VeiculoEstado)).all()}
        livres = [l for l in VAGAS + PLATAFORMAS if l not in ocupados]
        t = agora()
        if v.estado == "manobrando" and livres:      # termina a manobra numa vaga ou plataforma livre
            v.local, v.estado = random.choice(livres), "parado"
        elif v.local == "FORA":                       # volta da viagem pelo portão
            v.local, v.estado, v.entrou_em = "PORTAO", "manobrando", t
        elif v.local.startswith("P") and v.local != "PORTAO":  # sai para a viagem
            v.local, v.estado, v.entrou_em = "FORA", "em_viagem", None
        elif v.estado == "parado" and random.random() < 0.5:   # começa a manobrar
            v.local, v.estado = "CIRCULACAO", "manobrando"
        else:
            return
        v.atualizado_em = t
        db.add(EventoPosicao(prefixo=v.prefixo, local=v.local, estado=v.estado, fonte="simulado", registrado_em=t))
        db.commit()


async def loop_simulacao() -> None:
    while True:
        await asyncio.sleep(config.DEMO_INTERVALO_S)
        try:
            await asyncio.to_thread(_passo)
        except Exception:  # a demo nunca derruba a API
            log.exception("falha no passo da simulação")
