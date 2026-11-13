"""Ponte para o assistente de GenAI.

Se ASSISTENTE_URL estiver configurada, a pergunta (com o estado real do veículo, como no modo
"agente" do plano) vai para o serviço de LLM local + RAG. Senão, ou se ele cair, a API
responde com regras simples tiradas do POP SIMULADO, para a tela nunca ficar sem resposta.
A decisão é sempre do controlador: a resposta é só sugestão.
"""
import logging
import unicodedata

import httpx

from . import config

log = logging.getLogger("patio.assistente")

FONTE_POP = "POP do pátio (SIMULADO, escrito pela equipe)"

# (palavras-chave, ação, justificativa, seção do POP, confiança)
REGRAS = [
    (("saida", "confirm"), "Contatar o portão por rádio e conferir se o veículo passou sem registro. "
     "Se não saiu, acionar o motorista escalado e registrar o atraso.",
     "Saída prevista sem registro na portaria pode ser falha de registro ou atraso real; o POP manda "
     "confirmar fisicamente antes de reprogramar.", "§1 Saída sem confirmação", 0.7),
    (("vaga", "errad"), "Orientar o motorista a manobrar para a vaga escalada ou atualizar a escala "
     "se a troca for intencional.",
     "Veículo em vaga diferente da escalada atrasa a próxima saída e confunde a localização.",
     "§2 Veículo na vaga errada", 0.7),
    (("troc",), "Confirmar com o fiscal o motivo da troca e registrar o prefixo que realmente saiu.",
     "A portaria registrou um prefixo diferente do escalado; sem o registro a conciliação do turno fica errada.",
     "§3 Troca de carro", 0.65),
    (("atras",), "Avisar a plataforma e o CCO sobre o atraso estimado e priorizar a próxima saída.",
     "O passageiro na plataforma precisa da informação enquanto ainda dá tempo de agir.",
     "§4 Atraso na plataforma", 0.6),
]


def _normalizar(txt: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", txt.lower()) if unicodedata.category(c) != "Mn")


def fallback(pergunta: str, contexto: dict | None) -> dict:
    texto = _normalizar(pergunta + " " + str((contexto or {}).get("status_conciliacao") or ""))
    texto = texto.replace("_", " ")
    for chaves, acao, just, secao, conf in REGRAS:
        if all(k in texto for k in chaves):
            return {"acao": acao, "justificativa": just, "fonte": f"{FONTE_POP} {secao}",
                    "confianca": conf, "modo": "fallback_regras", "contexto_veiculo": contexto}
    return {"acao": "nao_consta", "justificativa": "A base de procedimentos não cobre este caso. "
            "Decisão do controlador.", "fonte": None, "confianca": 0.0,
            "modo": "fallback_regras", "contexto_veiculo": contexto}


async def perguntar(pergunta: str, contexto: dict | None) -> dict:
    if config.ASSISTENTE_URL:
        try:
            async with httpx.AsyncClient(timeout=config.ASSISTENTE_TIMEOUT_S) as cli:
                r = await cli.post(config.ASSISTENTE_URL, json={"pergunta": pergunta, "contexto": contexto})
                r.raise_for_status()
                dados = r.json()
                dados.setdefault("modo", "llm_rag")
                dados["contexto_veiculo"] = contexto
                return dados
        except (httpx.HTTPError, ValueError) as e:
            log.warning("assistente externo indisponível (%s); usando fallback", type(e).__name__)
    return fallback(pergunta, contexto)
