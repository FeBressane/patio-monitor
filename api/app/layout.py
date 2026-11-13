"""Layout do pátio de referência (Terminal Pirituba, simplificado para a maquete e o 3D).

Coordenadas em metros num plano local: x para leste, z para sul, origem no centro do pátio.
O mesmo código de local (V1, P2, PORTAO...) é usado pela portaria, pelo robô (tag RFID),
pela visão (zona/polígono) e pelo front 3D.
"""

# Centro aproximado do Terminal Pirituba. Conferir no mapa antes de usar no filtro de raio do pipeline.
CENTRO = {"lat": -23.4889, "lon": -46.7262, "raio_m": 250}

LOCAIS = (
    [{"codigo": "PORTAO", "tipo": "portao", "nome": "Portão de acesso", "x": -28.0, "z": 0.0, "w": 4.0, "d": 10.0}]
    + [
        {"codigo": f"V{i + 1}", "tipo": "vaga", "nome": f"Vaga {i + 1}",
         "x": -16.0 + (i % 6) * 5.5, "z": -12.0 if i < 6 else -3.0, "w": 4.0, "d": 7.0}
        for i in range(12)
    ]
    + [
        {"codigo": f"P{i + 1}", "tipo": "plataforma", "nome": f"Plataforma {i + 1}",
         "x": -14.0 + i * 9.0, "z": 11.0, "w": 7.0, "d": 4.0}
        for i in range(4)
    ]
)

CODIGOS = {l["codigo"] for l in LOCAIS} | {"FORA", "CIRCULACAO"}


def layout() -> dict:
    return {"centro": CENTRO, "locais": LOCAIS}
