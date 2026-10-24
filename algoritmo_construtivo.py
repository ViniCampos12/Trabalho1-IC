"""
Resumo da estratégia:
  1. Agrupa candidatos em "unidades de demanda" (CEP, tipo_prova).
  2. Ordena as unidades por ARREPENDIMENTO (regret): d(2ª escola) - d(1ª escola).
     Quem mais perde se não for atendido na melhor escola é atendido primeiro.
  3. Para cada unidade percorre as escolas da mais próxima à mais distante:
       a) completa salas já abertas com o mesmo tipo (best-fit);
       b) abre novas salas se o limite K permitir (escolha da sala controla
          a fragmentação de capacidade);
       c) se ainda sobrar gente, a unidade é DIVIDIDA para a próxima escola.
  4. Look-ahead: evita gastar o último "slot" de tipo de uma escola com uma
     sala que ficaria muito vazia (primeira passada "estrita").
  5. Reparo por ejeção: se sobrar candidato sem vaga, esvazia uma sala de
     outro tipo, realoca seus ocupantes em outras escolas e usa a sala.
  6. Múltiplas tentativas (GRASP): a 1ª é determinística; as demais sorteiam a
     próxima unidade dentro de uma Lista Restrita de Candidatos (RCL).
     Guarda-se a melhor tentativa.
"""

import copy
import math
import random
import time

class SolucaoConstrutiva:

    # ------------------------------------------------------------------
    # Inicialização e pré-processamento
    # ------------------------------------------------------------------
    def __init__(self, candidatos, escolas, matriz_distancias,
                 max_tipos_por_escola=2, semente=42, max_tentativas=10,
                 alfa=0.05, limite_desperdicio=None,
                 max_ejecoes=50, escolas_reparo=5):
        """
        Parâmetros extras (todos opcionais, úteis para experimentos):
          alfa               : tamanho relativo da RCL (0 = guloso puro).
                               Com 1000 unidades restantes e alfa=0.05, o
                               próximo é sorteado entre as 50 primeiras.
          limite_desperdicio : look-ahead. Ao usar o ÚLTIMO slot de tipo de
                               uma escola (K>=2), a nova sala só é aberta na
                               1ª passada se desperdiçar no máximo essa fração
                               da capacidade. PADRÃO = None (desligado): nos
                               testes, valores baixos fazem as escolas ficarem
                               com 1 tipo só e aumentam muito a distância.
                               Experimente 0.8-0.9 e compare no relatório.
          max_ejecoes        : máximo de ejeções por unidade no reparo.
          escolas_reparo     : no reparo, só as N escolas mais próximas da
                               unidade são testadas (limita o custo).
        """
        self.candidatos = candidatos
        self.K = max_tipos_por_escola
        self.max_tentativas = max_tentativas
        self.alfa = alfa
        self.limite_desperdicio = limite_desperdicio
        self.max_ejecoes = max_ejecoes
        self.escolas_reparo = escolas_reparo
        self.rng = random.Random(semente)
        self.dist = matriz_distancias
        self._escolas_base = escolas

        self._tipo_cand = {c["id_estudante"]: c["tipo_prova"] for c in candidatos}
        self._cache_ordem_cand = {}      # ordem de escolas por candidato (reparo)
        self.historico = []
        self.avisos = []

        # Escolas com capacidade total zero nunca são úteis.
        self._escolas_uteis = [
            e["id_escola"] for e in escolas if sum(e["capacidade_salas"]) > 0
        ]
        self._construir_unidades()
        self._iniciar_estado()

    def _construir_unidades(self):
        """Agrupa candidatos por (CEP, tipo) e calcula a ordem de escolas e o regret.
        """
        grupos = {}
        for c in self.candidatos:
            grupos.setdefault((c["cep"], c["tipo_prova"]), []).append(c["id_estudante"])

        self.unidades = []
        for (cep, tipo), ids in grupos.items():
            rep = self.dist[ids[0]]
            ordem = sorted(self._escolas_uteis, key=lambda j: rep[j])
            if len(ordem) >= 2:
                regret = rep[ordem[1]] - rep[ordem[0]]
            else:
                regret = 1e9  # só uma escola: não há alternativa, prioridade máxima
            self.unidades.append({
                "cep": cep, "tipo": tipo, "ids": ids,
                "ordem": ordem, "regret": regret,
            })

    def _iniciar_estado(self):
        """Cria uma solução vazia: todas as salas livres, sem tipo."""
        self.escolas = {}
        for e in self._escolas_base:
            salas = [{
                "id_sala": f"{e['id_escola']}-S{r + 1}",
                "capacidade": cap,
                "ocupacao": 0,
                "tipo_prova": None,
                "candidatos": [],
            } for r, cap in enumerate(e["capacidade_salas"])]
            self.escolas[e["id_escola"]] = {"salas": salas, "tipos_atribuidos": set()}
        self._aloc = {}   # id_candidato -> (id_escola, índice_da_sala)

    def _verificar_viabilidade_global(self):
        """Teste necessário (não suficiente): demanda total <= capacidade total."""
        demanda = len(self.candidatos)
        capacidade = sum(sum(e["capacidade_salas"]) for e in self._escolas_base)
        if demanda > capacidade:
            self.avisos.append(
                f"Inviável: {demanda} candidatos para {capacidade} lugares."
            )
        elif demanda > 0.95 * capacidade:
            self.avisos.append(
                "Instância muito apertada (>95% da capacidade): a fragmentação "
                "por tipo/salas pode impedir uma solução completa."
            )

    # ------------------------------------------------------------------
    # Operações básicas sobre o estado (todas mantêm as invariantes)
    # ------------------------------------------------------------------
    def _pode_abrir(self, j, tipo):
        """Escola j pode receber uma sala do tipo dado sem violar o limite K?"""
        tipos = self.escolas[j]["tipos_atribuidos"]
        return tipo in tipos or len(tipos) < self.K

    def _colocar(self, i, j, r):
        """Coloca o candidato i na sala r da escola j (fixa o tipo da sala se livre)."""
        sala = self.escolas[j]["salas"][r]
        tipo = self._tipo_cand[i]
        if sala["ocupacao"] == 0:
            sala["tipo_prova"] = tipo
        sala["candidatos"].append(i)
        sala["ocupacao"] += 1
        self.escolas[j]["tipos_atribuidos"].add(tipo)
        self._aloc[i] = (j, r)

    def _remover(self, i):
        """Remove o candidato i da sala atual; sala vazia volta a ficar sem tipo."""
        j, r = self._aloc.pop(i)
        sala = self.escolas[j]["salas"][r]
        sala["candidatos"].remove(i)
        sala["ocupacao"] -= 1
        if sala["ocupacao"] == 0:
            sala["tipo_prova"] = None
            self.escolas[j]["tipos_atribuidos"] = {
                s["tipo_prova"] for s in self.escolas[j]["salas"] if s["ocupacao"] > 0
            }

    def _preencher_sala(self, j, r, pendentes):
        """Move candidatos de 'pendentes' para a sala até lotá-la ou acabarem."""
        sala = self.escolas[j]["salas"][r]
        while pendentes and sala["ocupacao"] < sala["capacidade"]:
            self._colocar(pendentes.pop(), j, r)

    def _custo_atual(self):
        return sum(self.dist[i][j] for i, (j, _) in self._aloc.items())

    # ------------------------------------------------------------------
    # Passo 3: alocação de uma unidade de demanda
    # ------------------------------------------------------------------
    def _preencher_abertas(self, j, tipo, pendentes):
        """Best-fit: completa primeiro a sala aberta do mesmo tipo com MENOS folga,
        concentrando o espaço livre em poucas salas."""
        salas = self.escolas[j]["salas"]
        abertas = [
            (s["capacidade"] - s["ocupacao"], r) for r, s in enumerate(salas)
            if s["tipo_prova"] == tipo and s["ocupacao"] < s["capacidade"]
        ]
        for _, r in sorted(abertas):
            if not pendentes:
                break
            self._preencher_sala(j, r, pendentes)

    def _escolher_sala_nova(self, j, demanda):
        """Entre as salas livres de j: a MENOR com capacidade >= demanda;
        se nenhuma comporta, a MAIOR (menos salas parcialmente ocupadas)."""
        livres = [(s["capacidade"], r) for r, s in enumerate(self.escolas[j]["salas"])
                  if s["ocupacao"] == 0 and s["capacidade"] > 0]
        if not livres:
            return None
        suficientes = [x for x in livres if x[0] >= demanda]
        if suficientes:
            return min(suficientes)[1]
        return max(livres)[1]

    def _deve_evitar(self, j, tipo, r, demanda):
        """Look-ahead: abrir a sala r de j para 'tipo' consome o último slot de
        tipo da escola e deixa muito espaço ocioso? Então vale tentar antes
        outras escolas (na passada relaxada ela ainda poderá ser usada)."""
        if self.limite_desperdicio is None or self.K < 2:
            return False
        tipos = self.escolas[j]["tipos_atribuidos"]
        consome_ultimo = tipo not in tipos and len(tipos) == self.K - 1
        if not consome_ultimo:
            return False
        cap = self.escolas[j]["salas"][r]["capacidade"]
        desperdicio = max(0, cap - demanda)
        return desperdicio > self.limite_desperdicio * cap

    def _alocar_unidade(self, u):
        """Aloca a unidade; devolve a lista de candidatos que NÃO coube em lugar nenhum."""
        tipo = u["tipo"]
        pendentes = list(u["ids"])
        for estrito in (True, False):          # 1ª passada com look-ahead, 2ª sem
            for j in u["ordem"]:
                if not pendentes:
                    break
                self._preencher_abertas(j, tipo, pendentes)
                while pendentes and self._pode_abrir(j, tipo):
                    r = self._escolher_sala_nova(j, len(pendentes))
                    if r is None:
                        break
                    if estrito and self._deve_evitar(j, tipo, r, len(pendentes)):
                        break
                    self._preencher_sala(j, r, pendentes)
            if not pendentes:
                break
        return pendentes

    # ------------------------------------------------------------------
    # Passo 4: reparo por ejeção
    # ------------------------------------------------------------------
    def _ordem_candidato(self, i):
        if i not in self._cache_ordem_cand:
            d = self.dist[i]
            self._cache_ordem_cand[i] = sorted(self._escolas_uteis, key=lambda j: d[j])
        return self._cache_ordem_cand[i]

    def _melhor_destino(self, i, proibida):
        """Escola/sala mais próxima (≠ proibida) onde i cabe SEM novas ejeções."""
        tipo = self._tipo_cand[i]
        for j in self._ordem_candidato(i):
            if j == proibida:
                continue
            salas = self.escolas[j]["salas"]
            abertas = [(s["capacidade"] - s["ocupacao"], r) for r, s in enumerate(salas)
                       if s["tipo_prova"] == tipo and s["ocupacao"] < s["capacidade"]]
            if abertas:
                return j, min(abertas)[1]
            if self._pode_abrir(j, tipo):
                livres = [(s["capacidade"], r) for r, s in enumerate(salas)
                          if s["ocupacao"] == 0 and s["capacidade"] > 0]
                if livres:
                    return j, min(livres)[1]
        return None

    def _liberacao_permitida(self, j, r, tipo):
        """Se a sala r de j for esvaziada, a escola pode receber 'tipo' (limite K)?"""
        restantes = {s["tipo_prova"] for k, s in enumerate(self.escolas[j]["salas"])
                     if k != r and s["ocupacao"] > 0}
        return tipo in restantes or len(restantes) < self.K

    def _desfazer(self, log):
        """Reverte uma sequência de operações registradas (ordem inversa)."""
        for item in reversed(log):
            if item[0] == "novo":          # candidato da unidade colocado na sala
                self._remover(item[1])
            else:                          # ("mov", i, j_antigo, r_antigo)
                _, i, j_old, r_old = item
                self._remover(i)
                self._colocar(i, j_old, r_old)

    def _executar_ejecao(self, u, j, r, pendentes):
        """Esvazia a sala r de j, realoca os ocupantes e aloca a unidade ali."""
        sala = self.escolas[j]["salas"][r]
        log, delta = [], 0.0
        for i in list(sala["candidatos"]):
            destino = self._melhor_destino(i, proibida=j)
            if destino is None:
                self._desfazer(log)
                return None
            jn, rn = destino
            delta += self.dist[i][jn] - self.dist[i][j]
            self._remover(i)
            self._colocar(i, jn, rn)
            log.append(("mov", i, j, r))

        restantes = list(pendentes)
        antes = len(restantes)
        self._preencher_sala(j, r, restantes)
        for i in pendentes[len(restantes):antes]:
            log.append(("novo", i))
            delta += self.dist[i][j]
        return delta, log, restantes

    def _reparar(self, u, pendentes):
        """Tenta alocar 'pendentes' ejetando salas de outros tipos.

        Para cada (escola próxima, sala de outro tipo) SIMULA a ejeção, mede o
        aumento de custo e desfaz; ao final executa a de menor aumento.
        Modifica 'pendentes' in-place.
        """
        tipo = u["tipo"]
        for _ in range(self.max_ejecoes):
            if not pendentes:
                return
            melhor = None  # (delta, j, r)
            for j in u["ordem"][:self.escolas_reparo]:
                for r, sala in enumerate(self.escolas[j]["salas"]):
                    if sala["ocupacao"] == 0 or sala["tipo_prova"] == tipo:
                        continue
                    if not self._liberacao_permitida(j, r, tipo):
                        continue
                    res = self._executar_ejecao(u, j, r, pendentes)
                    if res is None:
                        continue
                    delta, log, _ = res
                    self._desfazer(log)
                    if melhor is None or delta < melhor[0]:
                        melhor = (delta, j, r)
            if melhor is None:
                return                      # nenhum reparo possível
            _, j, r = melhor
            res = self._executar_ejecao(u, j, r, pendentes)
            if res is None:
                return
            pendentes[:] = res[2]

    # ------------------------------------------------------------------
    # Ordem de processamento das unidades (regret + RCL)
    # ------------------------------------------------------------------
    def _ordenar_unidades(self, alfa):
        """Regret decrescente (desempate: unidade maior primeiro).
        Com alfa>0 sorteia o próximo entre as ceil(alfa*restantes) primeiras."""
        base = sorted(self.unidades, key=lambda u: (-u["regret"], -len(u["ids"])))
        if alfa <= 0:
            return base
        restantes, ordem = base, []
        while restantes:
            janela = max(1, math.ceil(alfa * len(restantes)))
            ordem.append(restantes.pop(self.rng.randrange(janela)))
        return ordem

    # ------------------------------------------------------------------
    # Execução principal
    # ------------------------------------------------------------------
    def resolver(self):
        """Executa 'max_tentativas' construções e devolve a melhor.

        Critério: primeiro menos candidatos sem vaga, depois menor distância.
        """
        self._verificar_viabilidade_global()
        for aviso in self.avisos:
            print(f"[AVISO] {aviso}")

        self.historico = []
        melhor = None
        for k in range(self.max_tentativas):
            alfa = 0.0 if k == 0 else self.alfa   # 1ª tentativa determinística
            inicio = time.perf_counter()
            self._iniciar_estado()

            nao_alocados = []
            for u in self._ordenar_unidades(alfa):
                pendentes = self._alocar_unidade(u)
                if pendentes:
                    self._reparar(u, pendentes)
                nao_alocados.extend(pendentes)

            custo = self._custo_atual()
            self.historico.append({
                "tentativa": k + 1, "alfa": alfa, "custo": custo,
                "nao_alocados": len(nao_alocados),
                "tempo_s": time.perf_counter() - inicio,
            })

            chave = (len(nao_alocados), custo)
            if melhor is None or chave < melhor["chave"]:
                melhor = {
                    "chave": chave,
                    "escolas": copy.deepcopy(self.escolas),
                    "aloc": dict(self._aloc),
                    "nao_alocados": list(nao_alocados),
                    "custo": custo,
                }

        # Restaura a melhor tentativa em self.escolas (usado pelo main).
        self.escolas = melhor["escolas"]
        self._aloc = melhor["aloc"]
        alocacoes = {
            i: (j, self.escolas[j]["salas"][r]["id_sala"])
            for i, (j, r) in self._aloc.items()
        }
        nao_alocados = melhor["nao_alocados"]
        custo = melhor["custo"] if not nao_alocados else None
        self.custo_parcial = melhor["custo"]
        return custo, alocacoes, nao_alocados

    def estatisticas(self):
        custos = [h["custo"] for h in self.historico if h["nao_alocados"] == 0]
        if not custos:
            return None
        media = sum(custos) / len(custos)
        desvio = math.sqrt(sum((c - media) ** 2 for c in custos) / len(custos))
        return {"validas": len(custos), "melhor": min(custos), "pior": max(custos),
                "media": media, "desvio": desvio}