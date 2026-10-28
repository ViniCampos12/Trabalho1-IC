import argparse
import time
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

        # Usa o estado atualizado da busca local, se fornecido. Caso contrário, usa o do construtivo.
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

            if estado_escolas:
                salas_iter = escola["salas"].values()
            else:
                salas_iter = escola["salas"]
                
            for sala in salas_iter:
                if sala["ocupacao"] > 0:
                    id_sala = sala.get("id_sala", "N/A") 
                    arquivo.write(
                        f"  sala {id_sala}: tipo={sala['tipo_prova']}; "
                        f"ocupacao={sala['ocupacao']}/{sala['capacidade']}\n"
                    )


def main():
    # Benchmark completo com 15 instâncias
    instancias = [
        # Testes Iniciais
        # "instancia_2.txt", # Pequena (382 candidatos) - Exemplo passo a passo
        # "instancia_1(2).txt", # Média (4213 candidatos) - Instância de validação
        # "instancia_base.txt", # Média/Grande (4744 candidatos) - Comportamento padrão
        # "instancia_diferenciada.txt", # Média/Grande (4374 candidatos) - Distribuição diferente
        # "instancia_2_grande.txt" # Muito Grande (5287 candidatos) - Teste de stress
        "instancia_1(3).txt",       # Pequena (316 cand.)
        "instancia1.txt",           # Média/Pequena (2550 cand.)
        "instancia2.txt",           # Média/Pequena (2550 cand.)
        "instancia_1(1).txt",       # Média (3452 cand.)
        "instancia_1(8).txt",       # Média (3531 cand.)
        "instancia_2(3).txt",       # Média (3900 cand.)
        "instancia_2(8).txt",       # Média (4131 cand.)
        "instancia_A.txt",          # Média (4518 cand.)
        "instancia_B.txt",          # Média (4442 cand.)
        "instancia_1(4).txt",       # Média/Grande (4656 cand.)
        "instancia_1(6).txt",       # Média/Grande (4656 cand.)
        "instancia_3_extra.txt",    # Grande (5287 cand.)
        "instancia_1(5).txt",       # Grande (5917 cand.)
        "instancia_2(4).txt",       # Muito Grande (7038 cand.)
        "instancia_2(6).txt"        # Muito Grande (7038 cand.)
    ]

    max_tipos = 2
    tentativas = 10
    semente = 42

    print("="*70)
    print("INÍCIO DOS EXPERIMENTOS EM LOTE (BENCHMARK ROBUSTO)")
    print("="*70)

    Path("resultados").mkdir(parents=True, exist_ok=True)

    for nome_arquivo in instancias:
        caminho_instancia = Path(nome_arquivo)
        
        print(f"\n{'='*70}")
        print(f"--- A processar: {nome_arquivo} ---")
        if not caminho_instancia.exists():
            print(f"  [ERRO] Ficheiro não encontrado: {caminho_instancia}. Salte para o próximo.")
            continue

        # 1. Leitura da Instância (AGORA PROTEGIDA CONTRA ERROS DE FORMATAÇÃO)
        try:
            candidatos, escolas, matriz_distancias = ler_instancia_txt(caminho_instancia)
        except Exception as e:
            print(f"  [ERRO CRÍTICO] Falha ao ler o arquivo {nome_arquivo}.")
            print(f"  Detalhe do erro: {e}")
            print("  Ignorando esta instância e saltando para a próxima...")
            continue # Pula para o próximo arquivo do loop
        
        avaliador = AvaliacaoSolucao(
            candidatos,
            escolas,
            matriz_distancias,
            max_tipos_por_escola=max_tipos
        )

        # 2. Heurística Construtiva
        tempo_inicio_construtivo = time.time()
        construtiva = SolucaoConstrutiva(
            candidatos, escolas, matriz_distancias,
            max_tipos_por_escola=max_tipos, semente=semente, max_tentativas=tentativas
        )
        custo_inicial, alocacoes_iniciais, nao_alocados = construtiva.resolver()
        tempo_fim_construtivo = time.time()

        if custo_inicial is None:
            print("  [AVISO] Solução viável não encontrada na fase construtiva.")
            print("  Possíveis causas: instâncias muito restritas (poucas vagas) ou limite de tipos de prova (K) muito baixo.")
            continue

        avaliacao_inicial = avaliador.avaliar(alocacoes_iniciais)
        
        # 3. Busca Local
        tempo_inicio_busca = time.time()
        busca = BuscaLocal(candidatos, escolas, matriz_distancias, alocacoes_iniciais, custo_inicial)
        custo_final, alocacoes_finais, iteracoes = busca.resolver()
        tempo_fim_busca = time.time()
        
        avaliacao_final = avaliador.avaliar(alocacoes_finais)

        # 4. Cálculo de Métricas para o Relatório
        melhoria = custo_inicial - custo_final
        melhoria_perc = (melhoria / custo_inicial) * 100 if custo_inicial > 0 else 0
        tempo_total = (tempo_fim_construtivo - tempo_inicio_construtivo) + (tempo_fim_busca - tempo_inicio_busca)
        escolas_utilizadas = sum(1 for e in busca.estado_escolas.values() if sum(s["ocupacao"] for s in e["salas"].values()) > 0)

        # 5. Impressão dos Dados
        print(f"\n  [MÉTRICAS - {nome_arquivo}]")
        print(f"  Candidatos: {len(candidatos)} | Escolas Utilizadas: {escolas_utilizadas}/{len(escolas)}")
        
        print(f"\n  -> Fase Construtiva:")
        print(f"     Custo Inicial : {avaliacao_inicial['custo']:.4f} km")
        print(f"     Viável?       : {'Sim' if avaliacao_inicial['viavel'] else 'Não'}")

        print(f"\n  -> Fase Busca Local:")
        print(f"     Custo Final   : {avaliacao_final['custo']:.4f} km")
        print(f"     Viável?       : {'Sim' if avaliacao_final['viavel'] else 'Não'}")

        print(f"\n  -> Resumo da Otimização:")
        print(f"     Melhoria Obtida       : {melhoria:.4f} km ({melhoria_perc:.2f}%)")
        print(f"     Iterações de Melhoria : {iteracoes}")
        print(f"     Tempo de Execução     : {tempo_total:.2f} segundos")

        # Guarda o resultado num ficheiro TXT
        caminho_saida = f"resultados/resultado_{caminho_instancia.stem}.txt"
        salvar_resultado(caminho_saida, custo_final, alocacoes_finais, nao_alocados, construtiva, busca.estado_escolas)
        print(f"  [+] Detalhes guardados em: {caminho_saida}")

if __name__ == "__main__":
    main()