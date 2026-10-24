import matplotlib.pyplot as plt


def ler_instancia_txt(nome_arquivo):
    candidatos = []
    escolas = []

    secao = None

    with open(nome_arquivo, "r", encoding="utf-8") as arquivo:
        for linha in arquivo:

            linha = linha.strip()

            # Ignora linhas vazias
            if not linha:
                continue

            # Identifica a seção atual
            if linha.startswith("# CANDIDATOS"):
                secao = "candidatos"
                continue

            if linha.startswith("# ESCOLAS"):
                secao = "escolas"
                continue

            if linha.startswith("# MATRIZ_DISTANCIAS"):
                secao = "distancias"
                continue

            # Ignora comentários
            if linha.startswith("#"):
                continue

            # ====================================================
            # CANDIDATOS
            # ====================================================

            if secao == "candidatos":
                partes = [p.strip() for p in linha.split(",")]

                candidato = {
                    "id_estudante": partes[0],
                    "cep": partes[1],
                    "tipo_prova": partes[2],
                    "latitude": float(partes[3]),
                    "longitude": float(partes[4])
                }

                candidatos.append(candidato)

            # ====================================================
            # ESCOLAS
            # ====================================================

            elif secao == "escolas":
                partes = [p.strip() for p in linha.split(",")]

                escola = {
                    "id_escola": partes[0],
                    "cep": partes[1],
                    "latitude": float(partes[2]),
                    "longitude": float(partes[3]),
                    "numero_salas": int(partes[4])
                }

                escolas.append(escola)

    return candidatos, escolas


def gerar_visualizacao(nome_txt, nome_imagem):

    candidatos, escolas = ler_instancia_txt(nome_txt)

    if not candidatos and not escolas:
        raise ValueError(f"A instância '{nome_txt}' não contém candidatos nem escolas.")

    plt.figure(figsize=(9, 7))

    # ============================================================
    # CANDIDATOS
    # ============================================================

    plt.scatter(
        [c["longitude"] for c in candidatos],
        [c["latitude"] for c in candidatos],
        s=8,
        alpha=0.35,
        label="Candidatos"
    )

    # ============================================================
    # ESCOLAS
    # ============================================================

    plt.scatter(
        [e["longitude"] for e in escolas],
        [e["latitude"] for e in escolas],
        s=80,
        marker="^",
        label="Escolas"
    )

    # Identificação das escolas
    for escola in escolas:
        plt.annotate(
            escola["id_escola"],
            (escola["longitude"], escola["latitude"]),
            xytext=(5, 5),
            textcoords="offset points",
            fontsize=8
        )

    # ============================================================
    # CONFIGURAÇÃO DO GRÁFICO
    # ============================================================

    plt.xlabel("Longitude")
    plt.ylabel("Latitude")
    plt.title(f"Distribuição - {nome_txt}")

    longitudes = (
        [c["longitude"] for c in candidatos]
        + [e["longitude"] for e in escolas]
    )
    latitudes = (
        [c["latitude"] for c in candidatos]
        + [e["latitude"] for e in escolas]
    )

    # As instâncias usam latitude/longitude reais, não mais a antiga
    # grade fictícia de 0 a 99.
    margem_longitude = max((max(longitudes) - min(longitudes)) * 0.05, 0.001)
    margem_latitude = max((max(latitudes) - min(latitudes)) * 0.05, 0.001)

    plt.xlim(
        min(longitudes) - margem_longitude,
        max(longitudes) + margem_longitude
    )
    plt.ylim(
        min(latitudes) - margem_latitude,
        max(latitudes) + margem_latitude
    )

    plt.grid(True, alpha=0.25)
    plt.legend()
    plt.tight_layout()

    plt.savefig(nome_imagem, dpi=200)
    plt.close()

    print(f"Visualização criada: {nome_imagem}")


def main():

    gerar_visualizacao(
        "instancias/instancia_1.txt",
        "visualizacoes/visualizacao_instancia_1.png"
    )

    gerar_visualizacao(
        "instancias/instancia_2.txt",
        "visualizacoes/visualizacao_instancia_2.png"
    )


if __name__ == "__main__":
    main()