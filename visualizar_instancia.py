import pandas as pd
import matplotlib.pyplot as plt


def gerar_visualizacao(nome_excel, nome_imagem):
    candidatos = pd.read_excel(
        nome_excel,
        sheet_name="Candidatos"
    )

    escolas = pd.read_excel(
        nome_excel,
        sheet_name="Escolas"
    )

    plt.figure(figsize=(9, 7))

    # Candidatos
    plt.scatter(
        candidatos["x"],
        candidatos["y"],
        s=8,
        alpha=0.35,
        label="Candidatos"
    )

    # Escolas
    plt.scatter(
        escolas["x"],
        escolas["y"],
        s=80,
        marker="^",
        label="Escolas"
    )

    # Identificação das escolas
    for _, escola in escolas.iterrows():
        plt.annotate(
            escola["id_escola"],
            (escola["x"], escola["y"]),
            xytext=(5, 5),
            textcoords="offset points",
            fontsize=8
        )

    plt.xlabel("Posição X (km)")
    plt.ylabel("Posição Y (km)")
    plt.title(f"Distribuição - {nome_excel}")
    plt.xlim(0, 99)
    plt.ylim(0, 99)
    plt.grid(True, alpha=0.25)
    plt.legend()
    plt.tight_layout()

    plt.savefig(nome_imagem, dpi=200)
    plt.close()

    print(f"Visualização criada: {nome_imagem}")


def main():
    # Este arquivo NÃO gera nem altera os arquivos Excel.
    # Apenas lê as instâncias existentes e cria as imagens.

    gerar_visualizacao(
        "instancia_1.xlsx",
        "visualizacao_instancia_1.png"
    )

    gerar_visualizacao(
        "instancia_2.xlsx",
        "visualizacao_instancia_2.png"
    )


if __name__ == "__main__":
    main()
