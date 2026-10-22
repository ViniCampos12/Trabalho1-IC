# busca_local.py
import copy
import time

class BuscaLocal:
    def __init__(self, candidatos, escolas, matriz_distancias, alocacoes_iniciais, custo_inicial, 
                 max_escolas_vizinhas=3, ganho_minimo=0.05):
        self.candidatos = candidatos
        self.dist = matriz_distancias
        self.alocacoes = copy.deepcopy(alocacoes_iniciais)  # {id_cand: (id_escola, id_sala)}
        self.custo_atual = custo_inicial
        self.ganho_minimo = ganho_minimo  # Ganho mínimo de 50m
        
        self.tipo_cand = {c["id_estudante"]: c["tipo_prova"] for c in candidatos}
        
        # 1. Indexação das N escolas mais próximas por candidato
        self.escolas_proximas = {}
        for c in candidatos:
            i = c["id_estudante"]
            escolas_ordenadas = sorted(
                matriz_distancias[i].keys(), 
                key=lambda j: matriz_distancias[i][j]
            )
            self.escolas_proximas[i] = escolas_ordenadas[:max_escolas_vizinhas]

        # 2. Estado das salas
        self.estado_escolas = {e["id_escola"]: {"salas": {}} for e in escolas}
        for e in escolas:
            for i, cap in enumerate(e["capacidade_salas"]):
                id_sala = f"{e['id_escola']}-S{i + 1}"
                self.estado_escolas[e["id_escola"]]["salas"][id_sala] = {
                    "id_sala": id_sala,
                    "capacidade": cap,
                    "ocupacao": 0,
                    "tipo_prova": None
                }

        # 3. Mapeamento direto: (escola, tipo_prova) -> lista de id_candidato
        self.cands_por_escola_tipo = {}
        
        for id_cand, (id_escola, id_sala) in self.alocacoes.items():
            sala = self.estado_escolas[id_escola]["salas"][id_sala]
            sala["ocupacao"] += 1
            sala["tipo_prova"] = self.tipo_cand[id_cand]
            
            chave = (id_escola, self.tipo_cand[id_cand])
            self.cands_por_escola_tipo.setdefault(chave, []).append(id_cand)

    def _tentar_shift(self, iteracao):
        """Tenta mover um candidato para uma escola mais próxima com vaga do mesmo tipo."""
        for id_cand, (escola_atual, sala_atual) in list(self.alocacoes.items()):
            tipo_prova = self.tipo_cand[id_cand]
            dist_atual = self.dist[id_cand][escola_atual]
            
            for nova_escola in self.escolas_proximas[id_cand]:
                if nova_escola == escola_atual or self.dist[id_cand][nova_escola] >= dist_atual:
                    continue
                
                dados_escola = self.estado_escolas[nova_escola]
                for nova_sala_id, nova_sala in dados_escola["salas"].items():
                    if nova_sala["tipo_prova"] == tipo_prova and nova_sala["ocupacao"] < nova_sala["capacidade"]:
                        ganho = dist_atual - self.dist[id_cand][nova_escola]
                        
                        if ganho >= self.ganho_minimo:
                            self.custo_atual -= ganho
                            
                            self.alocacoes[id_cand] = (nova_escola, nova_sala_id)
                            
                            self.cands_por_escola_tipo[(escola_atual, tipo_prova)].remove(id_cand)
                            self.cands_por_escola_tipo.setdefault((nova_escola, tipo_prova), []).append(id_cand)
                            
                            s_antiga = self.estado_escolas[escola_atual]["salas"][sala_atual]
                            s_antiga["ocupacao"] -= 1
                            if s_antiga["ocupacao"] == 0:
                                s_antiga["tipo_prova"] = None
                                
                            nova_sala["ocupacao"] += 1
                            print(f"  [ITERAÇÃO {iteracao}] [SHIFT] Cand {id_cand}: {escola_atual} -> {nova_escola} | Ganho: {ganho:.4f} km | Custo: {self.custo_atual:.4f} km")
                            return True
        return False

    def _tentar_swap(self, iteracao):
        """Tenta trocar candidatos buscando diretamente na lista da escola de destino."""
        for id1, (escola1, sala1) in list(self.alocacoes.items()):
            tipo1 = self.tipo_cand[id1]
            dist1_e1 = self.dist[id1][escola1]

            for escola2 in self.escolas_proximas[id1]:
                if escola2 == escola1:
                    continue

                candidatos_destino = self.cands_por_escola_tipo.get((escola2, tipo1), [])

                for id2 in candidatos_destino:
                    escola2_check, sala2 = self.alocacoes[id2]
                    dist2_e2 = self.dist[id2][escola2_check]
                    
                    dist1_e2 = self.dist[id1][escola2_check]
                    dist2_e1 = self.dist[id2][escola1]

                    ganho = (dist1_e1 + dist2_e2) - (dist1_e2 + dist2_e1)

                    if ganho >= self.ganho_minimo:
                        self.custo_atual -= ganho
                        
                        self.alocacoes[id1] = (escola2_check, sala2)
                        self.alocacoes[id2] = (escola1, sala1)
                        
                        self.cands_por_escola_tipo[(escola1, tipo1)].remove(id1)
                        self.cands_por_escola_tipo[(escola1, tipo1)].append(id2)
                        
                        self.cands_por_escola_tipo[(escola2_check, tipo1)].remove(id2)
                        self.cands_por_escola_tipo[(escola2_check, tipo1)].append(id1)
                        
                        print(f"  [ITERAÇÃO {iteracao}] [SWAP] Troca {id1} ({escola1}) <-> {id2} ({escola2_check}) | Ganho: {ganho:.4f} km | Custo: {self.custo_atual:.4f} km")
                        return True
        return False

    def resolver(self):
        """Executa a busca local indexada com logs numerados no console."""
        melhoria = True
        iteracoes = 0
        t0 = time.perf_counter()
        
        print("\n=================== INICIANDO BUSCA LOCAL INDEXADA ===================")
        print(f"Custo Inicial: {self.custo_atual:.4f} km\n")
        
        while melhoria:
            iteracoes += 1
            if self._tentar_shift(iteracoes):
                continue
            if self._tentar_swap(iteracoes):
                continue
            melhoria = False
            
        tempo_exec = time.perf_counter() - t0
        print(f"\n=====================================================================")
        print(f"Busca Local concluída em {tempo_exec:.2f}s ({iteracoes} iterações).")
        print(f"Custo Final: {self.custo_atual:.4f} km")
        print(f"=====================================================================\n")
        
        return self.custo_atual, self.alocacoes, iteracoes