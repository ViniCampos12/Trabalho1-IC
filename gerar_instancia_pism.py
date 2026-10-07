import math
import random
import pandas as pd


# ============================================================
# PARÂMETROS FIXOS (iguais para as duas instâncias)
# ============================================================

CAPACIDADE_ESCOLA_MIN = 200
CAPACIDADE_ESCOLA_MAX = 500

SALAS_MIN = 4
SALAS_MAX = 10

CAPACIDADE_SALA_MIN = 30
CAPACIDADE_SALA_MAX = 50

TIPOS_PROVA = ["M1", "M2", "M3e", "M3s", "M3h", "M3d"]

# Região fictícia: grade de 100 x 100 km
# LADO_REGIAO = 99.0

# ============================================================
# REGIÃO GEOGRÁFICA
# ============================================================

# Região aproximada de Juiz de Fora
LATITUDE_MIN = -21.81
LATITUDE_MAX = -21.73

LONGITUDE_MIN = -43.40
LONGITUDE_MAX = -43.27

LATITUDE_CENTRO = (LATITUDE_MIN + LATITUDE_MAX) / 2
LONGITUDE_CENTRO = (LONGITUDE_MIN + LONGITUDE_MAX) / 2

# O CEP fictício é derivado da posição (x, y)
CEP_BASE = 36000000

MAX_TENTATIVAS = 2000


# ============================================================
# PERFIS DAS INSTÂNCIAS
# Os dois perfis usam exatamente o mesmo código gerador.
# Altere apenas os valores abaixo.
#
#   num_clusters : 0 = posições uniformes na região;
#                  N > 0 = posições concentradas em N aglomerados
#   desvio_cluster: dispersão (km) em torno do centro de cada aglomerado
#   pesos_tipos  : None = tipos de prova equiprováveis;
#                  ou lista de 6 pesos (na ordem de TIPOS_PROVA)
# ============================================================

PERFIL_1 = dict(
    semente=42,
    arquivo="instancia_1.txt",
    num_escolas=15,
    ocupacao_min=0.80,
    ocupacao_max=0.95,
    num_clusters=0,
    desvio_cluster=8.0,
    pesos_tipos=None,
)

# EXEMPLO: troque pela característica que o grupo escolher.
PERFIL_2 = dict(
    semente=2024,
    arquivo="instancia_2.txt",
    num_escolas=15,
    ocupacao_min=0.80,
    ocupacao_max=0.95,
    num_clusters=1,
    desvio_cluster=1.0,
    pesos_tipos=None,
)


# ============================================================
# LOCALIZAÇÃO E DISTÂNCIA
# ============================================================

# def sortear_centros(rng, num_clusters):
#     return [
#         (rng.uniform(10, LADO_REGIAO - 10), rng.uniform(10, LADO_REGIAO - 10))
#         for _ in range(num_clusters)
#     ]
def sortear_centros(rng, num_clusters):
    if num_clusters == 1:
        return [
            (
                LATITUDE_CENTRO,
                LONGITUDE_CENTRO
            )
        ]

    return [
        (
            rng.uniform(LATITUDE_MIN, LATITUDE_MAX),
            rng.uniform(LONGITUDE_MIN, LONGITUDE_MAX)
        )
        for _ in range(num_clusters)
    ]


# def gerar_local(rng, centros, desvio):
#     """Gera (x, y) e um CEP fictício derivado da posição."""
#     if centros:
#         cx, cy = rng.choice(centros)
#         x = min(max(rng.gauss(cx, desvio), 0.0), LADO_REGIAO)
#         y = min(max(rng.gauss(cy, desvio), 0.0), LADO_REGIAO)
#     else:
#         x = rng.uniform(0, LADO_REGIAO)
#         y = rng.uniform(0, LADO_REGIAO)

#     cep = CEP_BASE + int(y) * 1000 + int(x)
#     return {"x": round(x, 2), "y": round(y, 2), "cep": f"{cep:08d}"}

def gerar_local(rng, centros, desvio):
    """
    Gera latitude e longitude.
    O desvio é informado em quilômetros.
    """

    # Aproximação:
    # 1 grau de latitude ≈ 111 km
    # 1 grau de longitude depende da latitude.
    
    if centros:
        latitude_centro, longitude_centro = rng.choice(centros)

        latitude = (
            latitude_centro
            + rng.gauss(0, desvio) / 111
        )

        longitude = (
            longitude_centro
            + rng.gauss(0, desvio) /
              (111 * math.cos(math.radians(latitude_centro)))
        )

    else:
        latitude = rng.uniform(
            LATITUDE_MIN,
            LATITUDE_MAX
        )

        longitude = rng.uniform(
            LONGITUDE_MIN,
            LONGITUDE_MAX
        )

    # Garante que o ponto permaneça dentro da região
    latitude = min(
        max(latitude, LATITUDE_MIN),
        LATITUDE_MAX
    )

    longitude = min(
        max(longitude, LONGITUDE_MIN),
        LONGITUDE_MAX
    )

    # CEP fictício
    cep = (
        CEP_BASE
        + int(abs(latitude * 100))
        + int(abs(longitude * 100)) * 100
    )

    return {
        "latitude": round(latitude, 6),
        "longitude": round(longitude, 6),
        "cep": f"{cep:08d}"
    }


def distancia(a, b):
    """
    Calcula a distância entre dois pontos geográficos
    utilizando a fórmula de Haversine.

    Retorna a distância em quilômetros.
    """

    raio_terra = 6371.0

    lat1 = math.radians(a["latitude"])
    lat2 = math.radians(b["latitude"])

    delta_lat = math.radians(
        b["latitude"] - a["latitude"]
    )

    delta_lon = math.radians(
        b["longitude"] - a["longitude"]
    )

    valor = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1)
        * math.cos(lat2)
        * math.sin(delta_lon / 2) ** 2
    )

    distancia_km = (
        2
        * raio_terra
        * math.asin(math.sqrt(valor))
    )

    return round(distancia_km, 4)


# ============================================================
# ESCOLAS
# ============================================================

def gerar_salas(rng):
    """Sorteia as salas até a capacidade total ficar entre 200 e 500."""
    while True:
        n = rng.randint(SALAS_MIN, SALAS_MAX)
        salas = [
            rng.randint(CAPACIDADE_SALA_MIN, CAPACIDADE_SALA_MAX)
            for _ in range(n)
        ]
        if CAPACIDADE_ESCOLA_MIN <= sum(salas) <= CAPACIDADE_ESCOLA_MAX:
            return salas


def gerar_escolas(rng, num_escolas, centros, desvio):
    escolas = []
    for i in range(1, num_escolas + 1):
        salas = gerar_salas(rng)
        escola = {
            "id_escola": f"E{i:03d}",
            "numero_salas": len(salas),
            "capacidade_total": sum(salas),
            "capacidade_salas": salas,
            "tipo_prova": None,  # definido depois da geração dos candidatos
        }
        escola.update(gerar_local(rng, centros, desvio))
        escolas.append(escola)
    return escolas


def calcular_capacidade_total(escolas):
    return sum(e["capacidade_total"] for e in escolas)


# ============================================================
# CANDIDATOS
# ============================================================

def gerar_candidatos(rng, escolas, ocupacao_min, ocupacao_max,
                     pesos_tipos, centros, desvio):
    capacidade_total = calcular_capacidade_total(escolas)
    percentual = rng.uniform(ocupacao_min, ocupacao_max)
    numero_candidatos = math.floor(capacidade_total * percentual)

    candidatos = []
    for i in range(1, numero_candidatos + 1):
        candidato = {
            "id_estudante": f"C{i:04d}",
            "tipo_prova": rng.choices(TIPOS_PROVA, weights=pesos_tipos)[0],
        }
        candidato.update(gerar_local(rng, centros, desvio))
        candidatos.append(candidato)
    return candidatos


# ============================================================
# TIPOS DAS ESCOLAS E FACTIBILIDADE
# ============================================================

def calcular_demanda_por_tipo(candidatos):
    demanda = {t: 0 for t in TIPOS_PROVA}
    for c in candidatos:
        demanda[c["tipo_prova"]] += 1
    return demanda


def calcular_capacidade_por_tipo(escolas):
    capacidade = {t: 0 for t in TIPOS_PROVA}
    for e in escolas:
        capacidade[e["tipo_prova"]] += e["capacidade_total"]
    return capacidade


def verificar_capacidade_por_tipo(candidatos, escolas):
    demanda = calcular_demanda_por_tipo(candidatos)
    capacidade = calcular_capacidade_por_tipo(escolas)
    return all(demanda[t] <= capacidade[t] for t in TIPOS_PROVA)


def atribuir_tipos_escolas(rng, escolas, candidatos):
    """
    Atribui um tipo de prova a cada escola de forma construtiva:
    para cada tipo (do mais demandado ao menos), reserva escolas
    aleatórias até a capacidade cobrir a demanda. As escolas que
    sobram recebem um tipo aleatório.
    Retorna True se conseguiu; False se o sorteio não foi factível.
    """
    demanda = calcular_demanda_por_tipo(candidatos)
    tipos = sorted(
        (t for t in TIPOS_PROVA if demanda[t] > 0),
        key=lambda t: -demanda[t],
    )

    livres = escolas.copy()
    rng.shuffle(livres)

    for tipo in tipos:
        cap = 0
        while cap < demanda[tipo]:
            if not livres:
                return False
            e = livres.pop()
            e["tipo_prova"] = tipo
            cap += e["capacidade_total"]

    for e in livres:
        e["tipo_prova"] = rng.choice(TIPOS_PROVA)

    return verificar_capacidade_por_tipo(candidatos, escolas)


# ============================================================
# MATRIZ DE DISTÂNCIAS
# ============================================================

def gerar_matriz_distancias(candidatos, escolas):
    matriz = []
    for c in candidatos:
        linha = {"id_estudante": c["id_estudante"]}
        for e in escolas:
            linha[e["id_escola"]] = distancia(c, e)
        matriz.append(linha)
    return matriz


# ============================================================
# VALIDAÇÃO
# ============================================================

def validar_instancia(candidatos, escolas, perfil):
    erros = []
    cap_total = calcular_capacidade_total(escolas)
    ocupacao = len(candidatos) / cap_total

    if not (10 <= len(escolas) <= 20):
        erros.append("Número de escolas fora de 10-20.")

    for e in escolas:
        if not (CAPACIDADE_ESCOLA_MIN <= e["capacidade_total"]
                <= CAPACIDADE_ESCOLA_MAX):
            erros.append(f"{e['id_escola']}: capacidade fora de 200-500.")
        if e["capacidade_total"] != sum(e["capacidade_salas"]):
            erros.append(f"{e['id_escola']}: soma das salas inconsistente.")
        if e["tipo_prova"] not in TIPOS_PROVA:
            erros.append(f"{e['id_escola']}: tipo inválido.")

    if not (0.80 <= ocupacao <= 0.95):
        erros.append(f"Ocupação {ocupacao:.2%} fora de 80%-95%.")

    if not verificar_capacidade_por_tipo(candidatos, escolas):
        erros.append("Capacidade insuficiente para algum tipo de prova.")

    ids = [c["id_estudante"] for c in candidatos]
    if len(ids) != len(set(ids)):
        erros.append("Identificadores de candidatos duplicados.")

    return erros


# ============================================================
# EXPORTAÇÃO
# ============================================================
def salvar_instancia(candidatos, escolas, matriz, nome_arquivo):
    """
    Salva a instância em um único arquivo TXT seguindo o modelo fornecido.
    """

    with open(nome_arquivo, "w", encoding="utf-8") as arquivo:

        # ========================================================
        # INFORMAÇÕES GERAIS
        # ========================================================

        arquivo.write(f"NUM_CANDIDATOS: {len(candidatos)}\n")
        arquivo.write(f"NUM_ESCOLAS: {len(escolas)}\n\n")

        # ========================================================
        # CANDIDATOS
        # ========================================================

        arquivo.write(
            "# CANDIDATOS (id, CEP, tipo_prova, latitude, longitude)\n"
        )

        for candidato in candidatos:
            arquivo.write(
                f"{candidato['id_estudante']}, "
                f"{candidato['cep']}, "
                f"{candidato['tipo_prova']}, "
                f"{candidato['latitude']}, "
                f"{candidato['longitude']}\n"
            )

        arquivo.write("\n")

        # ========================================================
        # ESCOLAS
        # ========================================================

        arquivo.write(
            "# ESCOLAS (id, CEP, latitude, longitude, "
            "num_salas, capacidades_salas)\n"
        )

        for escola in escolas:

            capacidades = ";".join(
                str(capacidade)
                for capacidade in escola["capacidade_salas"]
            )

            arquivo.write(
                f"{escola['id_escola']}, "
                f"{escola['cep']}, "
                f"{escola['latitude']}, "
                f"{escola['longitude']}, "
                f"{escola['numero_salas']}, "
                f"{capacidades}\n"
            )

        arquivo.write("\n")

        # ========================================================
        # MATRIZ DE DISTÂNCIAS
        # ========================================================

        arquivo.write(
            "# MATRIZ_DISTANCIAS "
            "(linhas=candidatos, colunas=escolas, em km)\n"
        )

        for linha in matriz:

            distancias = [
                str(linha[escola["id_escola"]])
                for escola in escolas
            ]

            arquivo.write(
                ", ".join(distancias) + "\n"
            )


# ============================================================
# GERAÇÃO DE UMA INSTÂNCIA
# ============================================================
def gerar_instancia(perfil):
    rng = random.Random(perfil["semente"])

    centros = sortear_centros(rng, perfil["num_clusters"])
    desvio = perfil["desvio_cluster"]

    for _ in range(MAX_TENTATIVAS):

        # Na Instância 2, as escolas ficam espalhadas.
        # Na Instância 1, mantém o comportamento original.
        if perfil["arquivo"] == "instancia_2.txt":
            centros_escolas = []
        else:
            centros_escolas = centros

        escolas = gerar_escolas(
            rng,
            perfil["num_escolas"],
            centros_escolas,
            desvio
        )

        candidatos = gerar_candidatos(
            rng,
            escolas,
            perfil["ocupacao_min"],
            perfil["ocupacao_max"],
            perfil["pesos_tipos"],
            centros,
            desvio
        )

        if atribuir_tipos_escolas(rng, escolas, candidatos):
            break
    else:
        raise RuntimeError(
            "Não foi possível gerar uma instância factível com este perfil."
        )

    erros = validar_instancia(candidatos, escolas, perfil)

    if erros:
        raise RuntimeError(
            "Instância inválida:\n" + "\n".join(erros)
        )

    matriz = gerar_matriz_distancias(candidatos, escolas)
    salvar_instancia(
        candidatos,
        escolas,
        matriz,
        perfil["arquivo"]
    )

    cap = calcular_capacidade_total(escolas)

    print(
        f"{perfil['arquivo']}: {len(candidatos)} candidatos, "
        f"{len(escolas)} escolas, capacidade {cap} "
        f"({len(candidatos) / cap:.1%}) - validada."
    )


def main():
    # for perfil in (PERFIL_1, PERFIL_2):
    #     gerar_instancia(perfil)
    gerar_instancia(PERFIL_1)


if __name__ == "__main__":
    main()