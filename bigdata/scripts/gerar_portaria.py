"""Gera a PORTARIA SIMULADA e a ESCALA SIMULADA a partir das posições REAIS da Olho Vivo.

Por que simular: não temos acesso à portaria nem à escala de veículos de uma garagem real.
O GTFS diz QUAIS viagens existem, mas não QUAL ônibus faz cada uma. Então derivamos os dois
registros das posições reais, com regras fixas e semente fixa (reprodutível).

REGRA DE GERAÇÃO (vai no relatório):
 1. Toda observação da Olho Vivo a até RAIO_PATIO_M do centro do terminal vira uma "estadia".
 2. Como a coleta é horária, a estadia é estimada em volta do instante observado (ta):
      entrada = ta - U(5, 40) min      saida = ta + U(3, 30) min
 3. Observações do mesmo prefixo com menos de 60 min entre si são a mesma estadia.
 4. Cada estadia recebe uma vaga V1..V12 aleatória.
 5. Ruído controlado (o que a conciliação precisa achar):
      8%  sem registro de saída na portaria       -> saida_sem_confirmacao
      5%  prefixo previsto na escala diferente   -> veiculo_trocado
      5%  vaga prevista diferente da registrada  -> parado_vaga_errada
      2%  saída digitada antes da entrada        -> barrada pela regra 3 da Prata
 6. Escala: saida_prevista = saida_real - atraso, atraso ~ Normal(2, 4) min.
 7. Motorista: matrícula e nome FICTÍCIOS (listas abaixo). A Ouro aplica SHA-256 neles.

Uso:  python gerar_portaria.py <pasta com olhovivo_*.json> <pasta de saída>
"""
import csv
import json
import math
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

SEMENTE = 2026
CENTRO = (-23.4889, -46.7262)
RAIO_PATIO_M = 250
NOMES_FICTICIOS = ["Motorista A", "Motorista B", "Motorista C", "Motorista D", "Motorista E",
                   "Motorista F", "Motorista G", "Motorista H"]


def dist_m(lat1, lon1, lat2, lon2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    return 2 * 6_371_000 * math.asin(math.sqrt(math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2))


def ler_observacoes(pasta: Path):
    obs = []
    for arq in sorted(pasta.glob("olhovivo_*.json")):
        for o in json.loads(arq.read_text(encoding="utf-8")):
            if o.get("prefixo") is None or o.get("lat") is None:
                continue
            if dist_m(CENTRO[0], CENTRO[1], o["lat"], o["lon"]) <= RAIO_PATIO_M:
                ta = datetime.fromisoformat(o["data_hora"].replace("Z", "+00:00"))
                obs.append((str(o["prefixo"]), o.get("letreiro"), ta))
    return sorted(obs, key=lambda x: (x[0], x[2]))


def agrupar_estadias(obs):
    estadias = []
    for pref, letreiro, ta in obs:
        if estadias and estadias[-1]["prefixo"] == pref and ta - estadias[-1]["ultima"] < timedelta(minutes=60):
            estadias[-1]["ultima"] = ta
        else:
            estadias.append({"prefixo": pref, "linha": letreiro, "primeira": ta, "ultima": ta})
    return estadias


def gerar(pasta_in: Path, pasta_out: Path):
    rnd = random.Random(SEMENTE)
    estadias = agrupar_estadias(ler_observacoes(pasta_in))
    prefixos = sorted({e["prefixo"] for e in estadias}) or ["00000"]
    portaria, escala = [], []
    for i, e in enumerate(estadias):
        entrada = e["primeira"] - timedelta(minutes=rnd.uniform(5, 40))
        saida = e["ultima"] + timedelta(minutes=rnd.uniform(3, 30))
        vaga = f"V{rnd.randint(1, 12)}"
        sorte = rnd.random()
        saida_reg = None if sorte < 0.08 else saida
        if 0.08 <= sorte < 0.10:  # erro de digitação: saída antes da entrada
            saida_reg = entrada - timedelta(minutes=rnd.uniform(1, 20))
        matricula = f"{rnd.randint(100000, 999999)}"
        portaria.append({
            "registro_id": f"R{i:06d}", "prefixo": e["prefixo"], "linha": e["linha"], "vaga": vaga,
            "entrada": entrada.isoformat(), "saida": saida_reg.isoformat() if saida_reg else "",
            "matricula_motorista": matricula, "nome_motorista": rnd.choice(NOMES_FICTICIOS), "simulado": "true",
        })
        troca = rnd.random() < 0.05
        vaga_errada = rnd.random() < 0.05
        escala.append({
            "viagem_id": f"{e['linha']}-{saida:%Y%m%d%H%M}-{i}", "linha": e["linha"],
            "prefixo_previsto": rnd.choice([p for p in prefixos if p != e["prefixo"]] or prefixos) if troca else e["prefixo"],
            "vaga_prevista": f"V{rnd.randint(1, 12)}" if vaga_errada else vaga,
            "saida_prevista": (saida - timedelta(minutes=rnd.gauss(2, 4))).isoformat(), "simulado": "true",
        })
    pasta_out.mkdir(parents=True, exist_ok=True)
    carimbo = datetime.now().strftime("%Y%m%d_%H%M")
    for nome, linhas in (("portaria", portaria), ("escala", escala)):
        destino = pasta_out / f"{nome}_{carimbo}.csv"
        with destino.open("w", newline="", encoding="utf-8") as f:
            if linhas:
                w = csv.DictWriter(f, fieldnames=list(linhas[0].keys()))
                w.writeheader()
                w.writerows(linhas)
        print(f"{destino}: {len(linhas)} linhas")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    gerar(Path(sys.argv[1]), Path(sys.argv[2]))
