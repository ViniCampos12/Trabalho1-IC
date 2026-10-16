import random
from collections import defaultdict


class SolucaoConstrutiva:
    """Heurística construtiva gulosa com múltiplas tentativas.

    Estruturas esperadas:
      candidatos: lista de dicts com 'id_estudante' e 'tipo_prova'.
      escolas: lista de dicts com 'id_escola' e 'capacidade_salas' (lista de capacidades).
      matriz_distancias: dict no formato distancias[id_estudante][id_escola] = distância.
      max_tipos_por_escola: máximo de tipos distintos permitidos em cada escola.

    Cada sala recebe no máximo um tipo de prova. O tipo é definido quando o
    primeiro candidato é alocado à sala. A heurística tenta várias ordens de
    construção, mas não garante encontrar uma solução para toda instância viável.
    """

    def __init__(
        self,
        candidatos,
        escolas,
        matriz_distancias,
        max_tipos_por_escola=2,
        semente=42,
        max_tentativas=10,
    ):
        self.candidatos = candidatos
        self.escolas_raw = escolas
        self.distancias = matriz_distancias
        self.K = max_tipos_por_escola
        self.semente = semente
        self.max_tentativas = max_tentativas

        if not isinstance(self.K, int) or self.K < 1:
            raise ValueError("max_tipos_por_escola deve ser um inteiro maior ou igual a 1.")
        if not isinstance(self.max_tentativas, int) or self.max_tentativas < 1:
            raise ValueError("max_tentativas deve ser um inteiro maior ou igual a 1.")

        self._validar_dados()
        self._reiniciar_estado()

    def _validar_dados(self):
        """Verifica campos e consistência básica antes de executar a heurística."""
        ids_candidatos = [c.get("id_estudante") for c in self.candidatos]
        ids_escolas = [e.get("id_escola") for e in self.escolas_raw]

        if not self.escolas_raw:
            raise ValueError("É necessário informar pelo menos uma escola.")
        if not self.candidatos:
            raise ValueError("É necessário informar pelo menos um candidato.")
        if any(i is None for i in ids_candidatos):
            raise ValueError("Todo candidato deve possuir 'id_estudante'.")
        if any(i is None for i in ids_escolas):
            raise ValueError("Toda escola deve possuir 'id_escola'.")
        if len(ids_candidatos) != len(set(ids_candidatos)):
            raise ValueError("Existem identificadores de candidatos duplicados.")
        if len(ids_escolas) != len(set(ids_escolas)):
            raise ValueError("Existem identificadores de escolas duplicados.")

        for c in self.candidatos:
            if not c.get("tipo_prova"):
                raise ValueError(
                    f"Candidato {c['id_estudante']} não possui 'tipo_prova'."
                )
            id_c = c["id_estudante"]
            if id_c not in self.distancias:
                raise ValueError(f"Não há linha de distâncias para o candidato {id_c}.")
            for id_e in ids_escolas:
                if id_e not in self.distancias[id_c]:
                    raise ValueError(
                        f"Distância ausente entre candidato {id_c} e escola {id_e}."
                    )
                try:
                    d = float(self.distancias[id_c][id_e])
                except (TypeError, ValueError):
                    raise ValueError(
                        f"Distância inválida entre candidato {id_c} e escola {id_e}."
                    )
                if d < 0 or d != d or d == float("inf"):
                    raise ValueError(
                        f"Distância deve ser finita e não negativa: candidato {id_c}, escola {id_e}."
                    )

        for e in self.escolas_raw:
            capacidades = e.get("capacidade_salas")
            if not isinstance(capacidades, (list, tuple)) or not capacidades:
                raise ValueError(
                    f"Escola {e['id_escola']} deve possuir uma lista não vazia em 'capacidade_salas'."
                )
            for cap in capacidades:
                if not isinstance(cap, (int, float)) or cap <= 0:
                    raise ValueError(
                        f"Capacidade de sala inválida na escola {e['id_escola']}: {cap}."
                    )

    def _reiniciar_estado(self):
        """Limpa todas as alocações, permitindo iniciar uma nova tentativa."""
        self.escolas = {}
        for e in self.escolas_raw:
            self.escolas[e["id_escola"]] = {
                "tipos_atribuidos": set(),
                "salas": [
                    {
                        "id_sala": indice,
                        "capacidade": capacidade,
                        "ocupacao": 0,
                        "tipo_prova": None,
                        "candidatos": [],
                    }
                    for indice, capacidade in enumerate(e["capacidade_salas"])
                ],
            }
        self.alocacoes = {}  # id_candidato -> (id_escola, id_sala)
        self.nao_alocados = []
        self.solucao_viavel = False

    def _distancia_media(self, candidato):
        id_c = candidato["id_estudante"]
        return sum(
            float(self.distancias[id_c][id_e]) for id_e in self.escolas
        ) / len(self.escolas)

    def _ordenar_candidatos(self, rng, tentativa):
        """Prioriza tipos de maior demanda e candidatos geograficamente isolados.

        Em tentativas posteriores, pequenas perturbações mudam a ordem dos tipos
        e dos candidatos para explorar construções alternativas.
        """
        grupos = defaultdict(list)
        for candidato in self.candidatos:
            grupos[candidato["tipo_prova"]].append(candidato)

        tipos = list(grupos)
        # A primeira tentativa prioriza estritamente os tipos mais numerosos.
        # Nas demais, o ruído pode alterar a ordem de tipos com demandas próximas.
        escala = max(1, len(self.candidatos)) * (0.015 * tentativa)
        tipos.sort(
            key=lambda tipo: (
                len(grupos[tipo]) + rng.uniform(-escala, escala),
                rng.random(),
            ),
            reverse=True,
        )

        ordenados = []
        for tipo in tipos:
            grupo = list(grupos[tipo])
            if tentativa == 0:
                grupo.sort(key=self._distancia_media, reverse=True)
            else:
                # Ruído limitado para variar a ordem sem ignorar totalmente o
                # critério de priorizar candidatos mais isolados.
                max_media = max((self._distancia_media(c) for c in grupo), default=1)
                fator = max(max_media, 1.0) * min(0.20, 0.03 * tentativa)
                grupo.sort(
                    key=lambda c: self._distancia_media(c) + rng.uniform(-fator, fator),
                    reverse=True,
                )
            ordenados.extend(grupo)
        return ordenados

    def _escolas_por_distancia(self, candidato, rng):
        id_c = candidato["id_estudante"]
        escolas = list(self.escolas)
        # Aleatoriza apenas empates exatos para não repetir sempre a mesma escolha.
        rng.shuffle(escolas)
        escolas.sort(key=lambda id_e: float(self.distancias[id_c][id_e]))
        return escolas

    def _salas_viaveis(self, escola, tipo):
        """Prefere salas já destinadas ao tipo, para preservar salas livres."""
        salas_compativeis = [
            s for s in escola["salas"]
            if s["tipo_prova"] == tipo and s["ocupacao"] < s["capacidade"]
        ]
        salas_livres = [
            s for s in escola["salas"]
            if s["tipo_prova"] is None and s["ocupacao"] < s["capacidade"]
        ]

        # Se o tipo ainda não existe na escola, só podemos abrir sala para ele
        # se houver espaço no limite K de tipos distintos.
        if tipo not in escola["tipos_atribuidos"]:
            if len(escola["tipos_atribuidos"]) >= self.K:
                return []
            return salas_compativeis + salas_livres
        return salas_compativeis + salas_livres

    def _alocar(self, candidato, id_escola, sala):
        id_c = candidato["id_estudante"]
        tipo = candidato["tipo_prova"]
        sala["ocupacao"] += 1
        sala["candidatos"].append(id_c)
        if sala["tipo_prova"] is None:
            sala["tipo_prova"] = tipo
        self.escolas[id_escola]["tipos_atribuidos"].add(tipo)
        self.alocacoes[id_c] = (id_escola, sala["id_sala"])

    def _construir_uma_vez(self, tentativa, rng):
        self._reiniciar_estado()
        candidatos_ordenados = self._ordenar_candidatos(rng, tentativa)

        for candidato in candidatos_ordenados:
            alocado = False
            for id_escola in self._escolas_por_distancia(candidato, rng):
                escola = self.escolas[id_escola]
                for sala in self._salas_viaveis(escola, candidato["tipo_prova"]):
                    self._alocar(candidato, id_escola, sala)
                    alocado = True
                    break
                if alocado:
                    break

            if not alocado:
                self.nao_alocados.append(candidato["id_estudante"])

        self.solucao_viavel = len(self.nao_alocados) == 0 and len(self.alocacoes) == len(self.candidatos)
        return self.solucao_viavel

    def _validar_solucao(self):
        """Confere as restrições da solução construída."""
        if len(self.alocacoes) != len(self.candidatos):
            return False

        tipos_por_escola = {}
        candidatos_por_id = {c["id_estudante"]: c for c in self.candidatos}
        for id_escola, escola in self.escolas.items():
            tipos = set()
            for sala in escola["salas"]:
                if sala["ocupacao"] > sala["capacidade"]:
                    return False
                if sala["ocupacao"] != len(sala["candidatos"]):
                    return False
                if sala["ocupacao"] > 0:
                    if sala["tipo_prova"] is None:
                        return False
                    tipos.add(sala["tipo_prova"])
                    for id_c in sala["candidatos"]:
                        candidato = candidatos_por_id[id_c]
                        if candidato["tipo_prova"] != sala["tipo_prova"]:
                            return False
            if len(tipos) > self.K:
                return False
            tipos_por_escola[id_escola] = tipos
        return True

    def resolver(self):
        """Retorna (custo_total, alocacoes, nao_alocados).

        Se nenhuma tentativa construir uma solução completa e válida, custo_total
        será None, alocacoes conterá a melhor tentativa parcial e nao_alocados
        listará os candidatos que não foram alocados. A heurística usa múltiplas
        tentativas com ordens diferentes como mecanismo de recuperação.
        """
        melhor_parcial = None
        melhor_quantidade = -1
        melhor_nao_alocados = None

        for tentativa in range(self.max_tentativas):
            rng = random.Random(self.semente + tentativa)
            viavel = self._construir_uma_vez(tentativa, rng)

            quantidade_alocada = len(self.alocacoes)
            if quantidade_alocada > melhor_quantidade:
                melhor_quantidade = quantidade_alocada
                melhor_parcial = (
                    dict(self.alocacoes),
                    self._copiar_escolas(),
                )
                melhor_nao_alocados = list(self.nao_alocados)

            if viavel and self._validar_solucao():
                custo_total = sum(
                    float(self.distancias[id_c][id_e])
                    for id_c, (id_e, _) in self.alocacoes.items()
                )
                return custo_total, self.alocacoes, []

        # Restaura a tentativa parcial que alocou mais candidatos.
        if melhor_parcial is not None:
            self.alocacoes, self.escolas = melhor_parcial
            self.nao_alocados = melhor_nao_alocados or []
        self.solucao_viavel = False

        # Não apresenta o custo parcial como se fosse uma solução completa.
        return None, self.alocacoes, self.nao_alocados

    def _copiar_escolas(self):
        """Cópia independente do estado para preservar a melhor tentativa parcial."""
        copia = {}
        for id_escola, escola in self.escolas.items():
            copia[id_escola] = {
                "tipos_atribuidos": set(escola["tipos_atribuidos"]),
                "salas": [
                    {
                        "id_sala": sala["id_sala"],
                        "capacidade": sala["capacidade"],
                        "ocupacao": sala["ocupacao"],
                        "tipo_prova": sala["tipo_prova"],
                        "candidatos": list(sala["candidatos"]),
                    }
                    for sala in escola["salas"]
                ],
            }
        return copia


# Exemplo de uso:
# construtiva = SolucaoConstrutiva(
#     candidatos, escolas, matriz_distancias,
#     max_tipos_por_escola=2,
#     semente=42,
#     max_tentativas=10,
# )
# custo, alocacoes, nao_alocados = construtiva.resolver()
# if custo is None:
#     print("Não foi encontrada uma solução completa.")
#     print("Candidatos não alocados:", len(nao_alocados))
# else:
#     print("Solução viável! Distância total:", custo)
#     print("Candidatos alocados:", len(alocacoes))
