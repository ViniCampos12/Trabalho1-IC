import argparse
import time
import math
from pathlib import Path
from algoritmo_construtivo import SolucaoConstrutiva
from busca_local import BuscaLocal
from avaliacao import AvaliacaoSolucao

def ler_instancia_txt(caminho_arquivo):
    """
    Seções esperadas:
      # CANDIDATOS: id, CEP, tipo_prova, latitude, longitude
      # ESCOLAS: id, CEP, latitude, longitude, numero_salas, capacidades_salas
      # MATRIZ_DISTANCIAS: cabeçalho com id_estudante e IDs das escolas; 
                           depois uma linha por candidato com as distâncias em km.
    Retorna candidatos, escolas e matriz_distancias no formato esperado pela classe.
    """
    candidatos = []
    escolas = []
    matriz_distancias = {}
    secao = None
    ids_escolas_matriz = []
    indice_linha_matriz = 0
    matriz_sem_identificadores = False

    with open(caminho_arquivo, "r", encoding="utf-8") as arquivo:
        for numero_linha, linha_original in enumerate(arquivo, start=1):
            linha = linha_original.strip()
            if not linha:
                continue
            if linha.startswith("# CANDIDATOS"):
                secao = "candidatos"
                continue
            if linha.startswith("# ESCOLAS"):
                secao = "escolas"
                continue
            if linha.startswith("# MATRIZ_DISTANCIAS"):
                secao = "matriz"
                continue
            if linha.startswith("#"):
                continue

            partes = [parte.strip() for parte in linha.split(",")]
            try:
                if secao == "candidatos":
                    if partes[0].lower() == "id_estudante":
                        continue
                    if len(partes) < 5:
                        raise ValueError("esperados 5 campos para o candidato")
                    candidatos.append({
                        "id_estudante": partes[0],
                        "cep": partes[1],
                        "tipo_prova": partes[2],
                        "latitude": float(partes[3]),
                        "longitude": float(partes[4]),
                    })
                elif secao == "escolas":
                    if partes[0].lower() == "id_escola":
                        continue
                    if len(partes) < 6:
                        raise ValueError("esperados 6 campos para a escola")
                    capacidades = [
                        int(valor.strip()) for valor in partes[5].split(";") if valor.strip()
                    ]
                    numero_salas = int(partes[4])
                    if numero_salas != len(capacidades):
                        raise ValueError(
                            f"numero_salas={numero_salas}, mas foram informadas "
                            f"{len(capacidades)} capacidades"
                        )
                    escolas.append({
                        "id_escola": partes[0],
                        "cep": partes[1],
                        "latitude": float(partes[2]),
                        "longitude": float(partes[3]),
                        "numero_salas": numero_salas,
                        "capacidade_salas": capacidades,
                    })
                elif secao == "matriz":
                    if partes[0].lower() in ("id_estudante", "id_candidato"):
                        ids_escolas_matriz = partes[1:]
                        if not ids_escolas_matriz:
                            raise ValueError("cabeçalho da matriz sem IDs de escolas")
                        continue
                    if not ids_escolas_matriz:
                        ids_escolas_matriz = [e["id_escola"] for e in escolas]
                        matriz_sem_identificadores = True

                    if matriz_sem_identificadores:
                        if indice_linha_matriz >= len(candidatos):
                            raise ValueError(
                                "a matriz possui mais linhas do que candidatos"
                            )
                        id_candidato = candidatos[indice_linha_matriz]["id_estudante"]
                        valores = partes
                        indice_linha_matriz += 1
                    else:
                        id_candidato = partes[0]
                        valores = partes[1:]
                    
                    if len(valores) != len(ids_escolas_matriz):
                        raise ValueError(
                            f"a linha de distâncias possui {len(valores)} valores, "
                            f"mas são esperadas {len(ids_escolas_matriz)} escolas"
                        )
                    matriz_distancias[id_candidato] = {
                        id_escola: float(distancia)
                        for id_escola, distancia in zip(ids_escolas_matriz, valores)
                    }
                else:
                    continue
            except (ValueError, IndexError) as erro:
                raise ValueError(
                    f"Erro ao ler '{caminho_arquivo}', linha {numero_linha}: {erro}."
                ) from erro

    if not candidatos:
        raise ValueError("Nenhum candidato foi encontrado na seção # CANDIDATOS.")
    if not escolas:
        raise ValueError("Nenhuma escola foi encontrada na seção # ESCOLAS.")
    if not matriz_distancias:
        raise ValueError("Nenhuma distância foi encontrada na seção # MATRIZ_DISTANCIAS.")

    ids_candidatos = {c["id_estudante"] for c in candidatos}
    ids_linhas_matriz = set(matriz_distancias)
    if ids_candidatos != ids_linhas_matriz:
        faltando = ids_candidatos - ids_linhas_matriz
        extras = ids_linhas_matriz - ids_candidatos
        raise ValueError(
            "Os candidatos da matriz não correspondem aos candidatos da seção. "
            f"Sem linha na matriz: {len(faltando)}; linhas extras: {len(extras)}."
        )

    ids_escolas = {e["id_escola"] for e in escolas}
    if set(ids_escolas_matriz) != ids_escolas:
        raise ValueError(
            "Os IDs/ordem de escolas usados na matriz não correspondem à seção # ESCOLAS."
        )

    if matriz_sem_identificadores and indice_linha_matriz != len(candidatos):
        raise ValueError(
            f"A matriz possui {indice_linha_matriz} linhas, mas existem "
            f"{len(candidatos)} candidatos."
        )

    return candidatos, escolas, matriz_distancias


def calcular_metricas_escolas(alocacoes, estado_escolas):
    """Calcula quantidade de escolas ativadas e ocupação média sobre as escolas ativadas."""
    escolas_utilizadas = set()
    vagas_totais_ativadas = 0
    alocados_totais = len(alocacoes)

    for id_candidato, (id_escola, _) in alocacoes.items():
        escolas_utilizadas.add(id_escola)

    for id_escola in escolas_utilizadas:
        escola_info = estado_escolas[id_escola]
        salas = escola_info["salas"].values() if isinstance(escola_info["salas"], dict) else escola_info["salas"]
        for sala in salas:
            vagas_totais_ativadas += sala["capacidade"]

    ocupacao_media = (alocados_totais / vagas_totais_ativadas * 100) if vagas_totais_ativadas > 0 else 0.0
    return len(escolas_utilizadas), ocupacao_media


def salvar_resultado(caminho_saida, custo, alocacoes, nao_alocados, construtiva, estado_escolas=None):
    """Salva resumo e alocações para inspeção posterior."""
    with open(caminho_saida, "w", encoding="utf-8") as arquivo:
        if custo is None:
            arquivo.write("STATUS: SOLUCAO COMPLETA NAO ENCONTRADA\n")
            arquivo.write(f"CANDIDATOS ALOCADOS: {len(alocacoes)}\n")
            arquivo.write(f"CANDIDATOS NAO ALOCADOS: {len(nao_alocados)}\n")
        else:
            arquivo.write("STATUS: SOLUCAO VIAVEL\n")
            arquivo.write(f"DISTANCIA TOTAL (km): {custo:.4f}\n")
            arquivo.write(f"CANDIDATOS ALOCADOS: {len(alocacoes)}\n")
            arquivo.write("CANDIDATOS NAO ALOCADOS: 0\n")
            arquivo.write(f"MAX_TIPOS_POR_ESCOLA: {construtiva.K}\n\n")

            arquivo.write("# ALOCACOES (id_estudante, id_escola, id_sala, tipo_prova)\n")
            tipos_candidatos = {
                c["id_estudante"]: c["tipo_prova"] for c in construtiva.candidatos
            }
            for id_candidato in sorted(alocacoes):
                id_escola, id_sala = alocacoes[id_candidato]
                arquivo.write(
                    f"{id_candidato}, {id_escola}, {id_sala}, "
                    f"{tipos_candidatos[id_candidato]}\n"
                )

        if nao_alocados:
            arquivo.write("\n# CANDIDATOS_NAO_ALOCADOS\n")
            for id_candidato in nao_alocados:
                arquivo.write(f"{id_candidato}\n")

        escolas_finais = estado_escolas if estado_escolas else construtiva.escolas
        
        arquivo.write("\n# RESUMO_POR_ESCOLA\n")
        for id_escola, escola in escolas_finais.items():
            ocupacao = sum(sala["ocupacao"] for sala in escola["salas"].values() if isinstance(escola["salas"], dict)) if estado_escolas else sum(sala["ocupacao"] for sala in escola["salas"])
            capacidade = sum(sala["capacidade"] for sala in escola["salas"].values() if isinstance(escola["salas"], dict)) if estado_escolas else sum(sala["capacidade"] for sala in escola["salas"])
            
            if estado_escolas:
                tipos = sorted(set(sala["tipo_prova"] for sala in escola["salas"].values() if sala["tipo_prova"]))
            else:
                tipos = sorted(escola["tipos_atribuidos"])
                
            arquivo.write(
                f"{id_escola}: ocupacao={ocupacao}/{capacidade}; "
                f"tipos={','.join(tipos) if tipos else 'nenhum'}\n"
            )

            salas_iter = escola["salas"].values() if estado_escolas else escola["salas"]
                
            for sala in salas_iter:
                if sala["ocupacao"] > 0:
                    id_sala = sala.get("id_sala", "N/A") 
                    arquivo.write(
                        f"  sala {id_sala}: tipo={sala['tipo_prova']}; "
                        f"ocupacao={sala['ocupacao']}/{sala['capacidade']}\n"
                    )


def executar_instancia(caminho_instancia, max_tipos, tentativas, semente):
    """Executa uma instância uma vez e retorna suas métricas e solução."""
    candidatos, escolas, matriz_distancias = ler_instancia_txt(caminho_instancia)

    avaliador = AvaliacaoSolucao(
        candidatos,
        escolas,
        matriz_distancias,
        max_tipos_por_escola=max_tipos
    )

    inicio = time.perf_counter()
    construtiva = SolucaoConstrutiva(
        candidatos,
        escolas,
        matriz_distancias,
        max_tipos_por_escola=max_tipos,
        semente=semente,
        max_tentativas=tentativas
    )
    custo_inicial, alocacoes_iniciais, nao_alocados = construtiva.resolver()

    if custo_inicial is None:
        return {
            "custo": None,
            "tempo_s": time.perf_counter() - inicio,
            "candidatos": len(candidatos),
            "nao_alocados": len(nao_alocados),
            "construtiva": construtiva,
            "alocacoes": alocacoes_iniciais,
            "nao_alocados_ids": nao_alocados,
            "estado_escolas": None,
        }

    avaliacao_inicial = avaliador.avaliar(alocacoes_iniciais)
    busca = BuscaLocal(
        candidatos,
        escolas,
        matriz_distancias,
        alocacoes_iniciais,
        custo_inicial
    )
    custo_final, alocacoes_finais, iteracoes = busca.resolver()
    avaliacao_final = avaliador.avaliar(alocacoes_finais)

    num_escolas, ocupacao_med = calcular_metricas_escolas(alocacoes_finais, busca.estado_escolas)

    return {
        "custo": avaliacao_final["custo"],
        "custo_inicial": avaliacao_inicial["custo"],
        "melhoria": avaliacao_inicial["custo"] - avaliacao_final["custo"],
        "melhoria_perc": (
            (avaliacao_inicial["custo"] - avaliacao_final["custo"])
            / avaliacao_inicial["custo"] * 100
            if avaliacao_inicial["custo"] > 0 else 0
        ),
        "tempo_s": time.perf_counter() - inicio,
        "candidatos": len(candidatos),
        "iteracoes": iteracoes,
        "construtiva": construtiva,
        "alocacoes": alocacoes_finais,
        "nao_alocados_ids": nao_alocados,
        "estado_escolas": busca.estado_escolas,
        "viavel": avaliacao_final["viavel"],
        "escolas_utilizadas": num_escolas,
        "ocupacao_media": ocupacao_med
    }


def main():
    parser = argparse.ArgumentParser(description="Otimização da Alocação de Candidatos a Locais de Prova")
    parser.add_argument(
        "--max_tipos", 
        type=int, 
        default=2, 
        choices=[1, 2],
        help="Número máximo de tipos de prova permitidos por escola (1 ou 2). Padrão: 2"
    )
    args = parser.parse_args()

    instancias = [
        # Série 1
        "instancias/instancia1_G1.txt",
        "instancias/instancia1_G2.txt",
        "instancias/instancia1_G3.txt",
        "instancias/instancia1_G4.txt",
        "instancias/instancia1_G5.txt",
        "instancias/instancia1_G6.txt",
        "instancias/instancia1_G7.txt",
        "instancias/instancia1_G8.txt",
        "instancias/instancia1_G9.txt",
        "instancias/instancia1_G10.txt",
        "instancias/instancia1_G11.txt",
        "instancias/instancia1_G12.txt",
        "instancias/instancia_1_G13.txt",
        "instancias/instancia_1_G14.txt",
        # Série 2
        "instancias/instancia2_G1.txt",
        "instancias/instancia2_G2.txt",
        "instancias/instancia2_G3.txt",
        "instancias/instancia2_G4.txt",
        "instancias/instancia2_G5.txt",
        "instancias/instancia2_G6.txt",
        "instancias/instancia2_G7.txt",
        "instancias/instancia2_G8.txt",
        "instancias/instancia2_G9.txt",
        "instancias/instancia2_G10.txt",
        "instancias/instancia2_G11.txt",
        "instancias/instancia2_G12.txt",
        "instancias/instancia_2_G13.txt",
        "instancias/instancia_2_G14.txt",
    ]

    max_tipos = args.max_tipos
    execucoes = 10
    tentativas = 10
    semente = 42

    print("=" * 85)
    print("INÍCIO DOS EXPERIMENTOS EM LOTE (BENCHMARK ROBUSTO)")
    print(f"PARÂMETRO SELECIONADO: MAX_TIPOS_POR_ESCOLA (K) = {max_tipos}")
    print("=" * 85)

    Path("resultados").mkdir(parents=True, exist_ok=True)

    for nome_arquivo in instancias:
        caminho_instancia = Path(nome_arquivo)
        
        print(f"\n{'=' * 85}")
        print(f"--- Processando: {nome_arquivo} ---")
        if not caminho_instancia.exists():
            print(f"  [ERRO] Ficheiro não encontrado: {caminho_instancia}. Saltando para o próximo.")
            continue

        resultados = []
        for numero_execucao in range(1, execucoes + 1):
            try:
                resultado = executar_instancia(
                    caminho_instancia,
                    max_tipos,
                    tentativas,
                    semente + numero_execucao - 1
                )
            except Exception as erro:
                print(
                    f"  [ERRO] Execução {numero_execucao:02d}/{execucoes} falhou: {erro}"
                )
                continue

            resultados.append(resultado)
            if resultado["custo"] is None:
                print(
                    f"  Execução {numero_execucao:02d}/{execucoes}: "
                    f"Solução INVIÁVEL | tempo={resultado['tempo_s']:.2f}s"
                )
            else:
                print(
                    f"  Execução {numero_execucao:02d}/{execucoes}: "
                    f"Custo Inicial={resultado['custo_inicial']:.2f} km -> "
                    f"Melhor Custo={resultado['custo']:.2f} km | "
                    f"Ganho={resultado['melhoria_perc']:.2f}% ({resultado['melhoria']:.2f} km) | "
                    f"Escolas={resultado['escolas_utilizadas']} | "
                    f"Ocupação={resultado['ocupacao_media']:.2f}% | "
                    f"Tempo={resultado['tempo_s']:.2f}s"
                )

        resultados_validos = [r for r in resultados if r["custo"] is not None]
        
        if not resultados_validos:
            print(f"\n  [RESUMO - {nome_arquivo}]")
            print(f"  Status: INVIÁVEL (0/{execucoes} execuções viáveis)")
            continue

        melhor = min(resultados_validos, key=lambda r: r["custo"])
        custos = [r["custo"] for r in resultados_validos]
        custo_medio = sum(custos) / len(custos)
        
        # Cálculo do Desvio Padrão
        variancia = sum((c - custo_medio) ** 2 for c in custos) / len(custos)
        desvio_padrao = math.sqrt(variancia)
        
        tempo_medio = sum(r["tempo_s"] for r in resultados) / len(resultados)

        print(f"\n  [RESUMO CONSOLIDADO - {nome_arquivo}]")
        print(f"  Candidatos Processados: {melhor['candidatos']}")
        print(f"  Taxa de Sucesso (Viabilidade): {len(resultados_validos)}/{execucoes} execuções ({len(resultados_validos)/execucoes*100:.1f}%)")
        print(f"  Custo Inicial (Melhor Execução): {melhor['custo_inicial']:.2f} km")
        print(f"  Melhor Custo Encontrado: {melhor['custo']:.2f} km")
        print(f"  Custo Médio: {custo_medio:.2f} km")
        print(f"  Desvio Padrão: {desvio_padrao:.2f} km ({(desvio_padrao/custo_medio*100 if custo_medio > 0 else 0):.2f}%)")
        print(f"  Melhoria Obtida: {melhor['melhoria']:.2f} km ({melhor['melhoria_perc']:.2f}%)")
        print(f"  Escolas Utilizadas: {melhor['escolas_utilizadas']}")
        print(f"  Ocupação Média (Escolas Ativadas): {melhor['ocupacao_media']:.2f}%")
        print(f"  Tempo Médio de Execução: {tempo_medio:.2f}s")

        caminho_saida = f"resultados/resultado_{caminho_instancia.stem}.txt"
        salvar_resultado(
            caminho_saida,
            melhor["custo"],
            melhor["alocacoes"],
            melhor["nao_alocados_ids"],
            melhor["construtiva"],
            melhor["estado_escolas"]
        )
        print(f"  [+] Solução detalhada salva em: {caminho_saida}")

if __name__ == "__main__":
    main()