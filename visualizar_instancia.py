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
                    "x": float(partes[3]),
                    "y": float(partes[4])
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
                    "x": float(partes[2]),
                    "y": float(partes[3]),
                    "numero_salas": int(partes[4])
                }

                escolas.append(escola)

    return candidatos, escolas


def gerar_visualizacao(nome_txt, nome_imagem):

    candidatos, escolas = ler_instancia_txt(nome_txt)

    plt.figure(figsize=(9, 7))

    # ============================================================
    # CANDIDATOS
    # ============================================================

    plt.scatter(
        [c["x"] for c in candidatos],
        [c["y"] for c in candidatos],
        s=8,
        alpha=0.35,
        label="Candidatos"
    )

    # ============================================================
    # ESCOLAS
    # ============================================================

    plt.scatter(
        [e["x"] for e in escolas],
        [e["y"] for e in escolas],
        s=80,
        marker="^",
        label="Escolas"
    )

    # Identificação das escolas
    for escola in escolas:
        plt.annotate(
            escola["id_escola"],
            (escola["x"], escola["y"]),
            xytext=(5, 5),
            textcoords="offset points",
            fontsize=8
        )

    # ============================================================
    # CONFIGURAÇÃO DO GRÁFICO
    # ============================================================

    plt.xlabel("Posição X (km)")
    plt.ylabel("Posição Y (km)")
    plt.title(f"Distribuição - {nome_txt}")

    plt.xlim(0, 99)
    plt.ylim(0, 99)

    plt.grid(True, alpha=0.25)
    plt.legend()
    plt.tight_layout()

    plt.savefig(nome_imagem, dpi=200)
    plt.close()

    print(f"Visualização criada: {nome_imagem}")


def main():

    gerar_visualizacao(
        "instancia_1.txt",
        "visualizacao_instancia_1.png"
    )

    gerar_visualizacao(
        "instancia_2.txt",
        "visualizacao_instancia_2.png"
    )


if __name__ == "__main__":
    main()