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
LADO_REGIAO = 99.0

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
    arquivo="instancia_1.xlsx",
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
    arquivo="instancia_2.xlsx",
    num_escolas=15,
    ocupacao_min=0.80,
    ocupacao_max=0.95,
    num_clusters=3,
    desvio_cluster=8.0,
    pesos_tipos=None,
)


# ============================================================
# LOCALIZAÇÃO E DISTÂNCIA
# ============================================================

def sortear_centros(rng, num_clusters):
    return [
        (rng.uniform(10, LADO_REGIAO - 10), rng.uniform(10, LADO_REGIAO - 10))
        for _ in range(num_clusters)
    ]


def gerar_local(rng, centros, desvio):
    """Gera (x, y) e um CEP fictício derivado da posição."""
    if centros:
        cx, cy = rng.choice(centros)
        x = min(max(rng.gauss(cx, desvio), 0.0), LADO_REGIAO)
        y = min(max(rng.gauss(cy, desvio), 0.0), LADO_REGIAO)
    else:
        x = rng.uniform(0, LADO_REGIAO)
        y = rng.uniform(0, LADO_REGIAO)

    cep = CEP_BASE + int(y) * 1000 + int(x)
    return {"x": round(x, 2), "y": round(y, 2), "cep": f"{cep:08d}"}


def distancia(a, b):
    """Distância euclidiana (km) entre dois pontos."""
    return round(math.hypot(a["x"] - b["x"], a["y"] - b["y"]), 2)


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
    df_candidatos = pd.DataFrame(candidatos)[
        ["id_estudante", "cep", "x", "y", "tipo_prova"]
    ]

    df_escolas = pd.DataFrame([
        {
            "id_escola": e["id_escola"],
            "cep": e["cep"],
            "x": e["x"],
            "y": e["y"],
            "numero_salas": e["numero_salas"],
            "capacidade_total": e["capacidade_total"],
            "tipo_prova": e["tipo_prova"],
        }
        for e in escolas
    ])

    df_salas = pd.DataFrame([
        {
            "id_escola": e["id_escola"],
            "id_sala": f"{e['id_escola']}-S{j:02d}",
            "capacidade_sala": cap,
        }
        for e in escolas
        for j, cap in enumerate(e["capacidade_salas"], start=1)
    ])

    df_distancias = pd.DataFrame(matriz)

    # Resumo neutro: apenas os itens pedidos no enunciado
    df_resumo = pd.DataFrame(
        [
            ("Quantidade de candidatos", len(candidatos)),
            ("Quantidade de escolas", len(escolas)),
        ],
        columns=["Informação", "Valor"],
    )

    with pd.ExcelWriter(nome_arquivo, engine="openpyxl") as w:
        df_resumo.to_excel(w, sheet_name="Resumo", index=False)
        df_candidatos.to_excel(w, sheet_name="Candidatos", index=False)
        df_escolas.to_excel(w, sheet_name="Escolas", index=False)
        df_salas.to_excel(w, sheet_name="Salas", index=False)
        df_distancias.to_excel(w, sheet_name="Matriz_Distancias", index=False)


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
        if perfil["arquivo"] == "instancia_2.xlsx":
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
    gerar_instancia(PERFIL_2)


if __name__ == "__main__":
    main()