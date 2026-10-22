class AvaliacaoSolucao:
    def __init__(
        self,
        candidatos,
        escolas,
        matriz_distancias,
        max_tipos_por_escola=2
    ):
        self.candidatos = candidatos
        self.escolas = escolas
        self.dist = matriz_distancias
        self.K = max_tipos_por_escola

        self.tipos = {
            c["id_estudante"]: c["tipo_prova"]
            for c in candidatos
        }

        # Capacidade de cada sala, identificada pelo mesmo padrão
        # utilizado pelo algoritmo construtivo.
        self.salas = {}
        for escola in escolas:
            id_escola = escola["id_escola"]

            for i, capacidade in enumerate(
                escola["capacidade_salas"]
            ):
                id_sala = f"{id_escola}-S{i + 1}"
                self.salas[(id_escola, id_sala)] = capacidade

    def avaliar(self, alocacoes):
        """
        Retorna a distância total, a viabilidade e as violações.
        alocacoes: {id_candidato: (id_escola, id_sala)}
        """
        violacoes = []
        ocupacao = {}
        tipos_salas = {}
        tipos_escolas = {}
        custo = 0.0

        ids_candidatos = set(self.tipos)
        ids_alocados = set(alocacoes)

        # Verifica candidatos ausentes ou IDs desconhecidos.
        faltantes = ids_candidatos - ids_alocados
        extras = ids_alocados - ids_candidatos

        if faltantes:
            violacoes.append(
                f"{len(faltantes)} candidato(s) não alocado(s)."
            )

        if extras:
            violacoes.append(
                f"{len(extras)} candidato(s) desconhecido(s)."
            )

        for id_cand, (id_escola, id_sala) in alocacoes.items():
            if id_cand not in self.tipos:
                continue

            if (id_escola, id_sala) not in self.salas:
                violacoes.append(
                    f"Candidato {id_cand}: escola/sala inválida."
                )
                continue

            # Calcula a distância do candidato à escola.
            if (
                id_cand not in self.dist
                or id_escola not in self.dist[id_cand]
            ):
                violacoes.append(
                    f"Candidato {id_cand}: distância inexistente."
                )
                continue

            custo += self.dist[id_cand][id_escola]

            chave_sala = (id_escola, id_sala)
            ocupacao[chave_sala] = (
                ocupacao.get(chave_sala, 0) + 1
            )

            tipo = self.tipos[id_cand]
            tipo_anterior = tipos_salas.get(chave_sala)

            if tipo_anterior is not None and tipo_anterior != tipo:
                violacoes.append(
                    f"Sala {id_sala}, escola {id_escola}: "
                    "tipos de prova incompatíveis."
                )
            else:
                tipos_salas[chave_sala] = tipo

            tipos_escolas.setdefault(id_escola, set()).add(tipo)

        # Verifica capacidades.
        for chave_sala, quantidade in ocupacao.items():
            capacidade = self.salas[chave_sala]

            if quantidade > capacidade:
                violacoes.append(
                    f"Sala {chave_sala[1]} da escola "
                    f"{chave_sala[0]} excede a capacidade: "
                    f"{quantidade}/{capacidade}."
                )

        # Verifica limite de tipos por escola.
        for id_escola, tipos in tipos_escolas.items():
            if len(tipos) > self.K:
                violacoes.append(
                    f"Escola {id_escola} oferece "
                    f"{len(tipos)} tipos; limite K={self.K}."
                )

        return {
            "custo": custo,
            "viavel": len(violacoes) == 0,
            "violacoes": violacoes,
            "candidatos_alocados": len(
                ids_alocados & ids_candidatos
            ),
            "candidatos_nao_alocados": len(faltantes),
        }
