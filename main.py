"""Ponto de entrada: lê a instância TXT, executa a heurística construtiva e a busca local."""
import argparse
from pathlib import Path
from algoritmo_construtivo import SolucaoConstrutiva
from busca_local import BuscaLocal

def ler_instancia_txt(caminho_arquivo):
    """Lê o formato TXT produzido por gerador_instancias.py.
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
    parser = argparse.ArgumentParser(
        description="Executa a heurística construtiva e busca local sobre uma instância TXT."
    )
    parser.add_argument(
        "instancia", nargs="?", default="instancia_1.txt",
        help="Caminho do arquivo TXT (padrão: instancia_1.txt)."
    )
    parser.add_argument(
        "--max-tipos", type=int, default=2,
        help="Máximo de tipos de prova por escola (padrão: 2)."
    )
    parser.add_argument(
        "--tentativas", type=int, default=10,
        help="Número de tentativas de construção (padrão: 10)."
    )
    parser.add_argument(
        "--semente", type=int, default=42,
        help="Semente aleatória para reproduzir o teste (padrão: 42)."
    )
    parser.add_argument(
        "--saida", default=None,
        help="Arquivo para guardar o resultado (padrão: resultado_<nome_instancia>.txt)."
    )
    args = parser.parse_args()

    caminho_instancia = Path(args.instancia)
    if not caminho_instancia.exists():
        parser.error(
            f"Arquivo de instância não encontrado: {caminho_instancia.resolve()}"
        )

    candidatos, escolas, matriz_distancias = ler_instancia_txt(caminho_instancia)

    print(f"Instância carregada: {caminho_instancia}")
    print(f"Candidatos: {len(candidatos)}")
    print(f"Escolas: {len(escolas)}")
    print(f"Distâncias carregadas: {sum(len(linha) for linha in matriz_distancias.values())}")
    print(f"Máximo de tipos por escola (K): {args.max_tipos}")
    print(f"Tentativas: {args.tentativas}\n")

    # 1. EXECUTA O ALGORITMO CONSTRUTIVO
    construtiva = SolucaoConstrutiva(
        candidatos,
        escolas,
        matriz_distancias,
        max_tipos_por_escola=args.max_tipos,
        semente=args.semente,
        max_tentativas=args.tentativas,
    )
    custo_inicial, alocacoes_iniciais, nao_alocados = construtiva.resolver()

    estado_escolas_final = None

    if custo_inicial is None:
        print("Não foi encontrada uma solução completa e viável.")
        print(f"Candidatos alocados na melhor tentativa: {len(alocacoes_iniciais)}")
        print(f"Candidatos não alocados: {len(nao_alocados)}")
        custo_final = None
        alocacoes_finais = alocacoes_iniciais
    else:
        print("Solução viável encontrada pelo Construtivo!")
        print(f"Distância total inicial: {custo_inicial:.4f} km\n")
        
        # 2. EXECUTA A BUSCA LOCAL
        print("A iniciar a Busca Local...")
        busca = BuscaLocal(candidatos, escolas, matriz_distancias, alocacoes_iniciais, custo_inicial)
        custo_final, alocacoes_finais, iteracoes = busca.resolver()
        estado_escolas_final = busca.estado_escolas
        
        print(f"Busca Local finalizada em {iteracoes} iterações de melhoria.")
        print(f"Distância total final: {custo_final:.4f} km")
        print(f"Melhoria obtida: {(custo_inicial - custo_final):.4f} km\n")

        print("Ocupação por escola (Pós-Busca Local):")
        for id_escola, escola in estado_escolas_final.items():
            ocupacao = sum(sala["ocupacao"] for sala in escola["salas"].values())
            capacidade = sum(sala["capacidade"] for sala in escola["salas"].values())
            tipos = sorted(set(sala["tipo_prova"] for sala in escola["salas"].values() if sala["tipo_prova"]))
            if ocupacao:
                print(
                    f"  {id_escola}: {ocupacao}/{capacidade} candidatos; "
                    f"tipos: {', '.join(tipos)}"
                )

    caminho_saida = args.saida
    if caminho_saida is None:
        caminho_saida = f"resultado_{caminho_instancia.stem}.txt"

    salvar_resultado(caminho_saida, custo_final, alocacoes_finais, nao_alocados, construtiva, estado_escolas_final)
    print(f"\nResultado detalhado guardado em: {Path(caminho_saida).resolve()}")

if __name__ == "__main__":
    main()