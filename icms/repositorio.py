"""Persistência e controle de versão para um único processo servidor."""

import hashlib
import json
from copy import deepcopy
from threading import RLock
from typing import Any

from icms.regras import agora, calcular, normalizar_processo, preparar, validar

CABECALHO = [
    "processo",
    "versao",
    "status",
    "autor",
    "atualizado_em",
    "conteudo_json",
]
HISTORICO = [
    "processo",
    "versao",
    "status",
    "autor",
    "data",
    "hash",
    "alteracoes_json",
]


class Conflito(ValueError):
    """Indica uma edição baseada em versão antiga."""


class Repositorio:
    """Coordena leitura, validação e gravação em uma instância do app."""

    def __init__(self) -> None:
        self.trava = RLock()
        self.registros: list[dict[str, Any]] = []
        self.historico: list[dict[str, Any]] = []

    @staticmethod
    def _diferencas(
        antes: Any, depois: Any, caminho: str = ""
    ) -> dict[str, dict[str, Any]]:
        """Descreve apenas os valores alterados, com caminho até o campo."""
        if isinstance(antes, dict) and isinstance(depois, dict):
            diferencas: dict[str, dict[str, Any]] = {}
            for chave in sorted(set(antes) | set(depois)):
                proximo = f"{caminho}.{chave}" if caminho else str(chave)
                diferencas.update(
                    Repositorio._diferencas(
                        antes.get(chave), depois.get(chave), proximo
                    )
                )
            return diferencas
        if isinstance(antes, list) and isinstance(depois, list):
            diferencas = {}
            for indice in range(max(len(antes), len(depois))):
                valor_antes = antes[indice] if indice < len(antes) else None
                valor_depois = depois[indice] if indice < len(depois) else None
                diferencas.update(
                    Repositorio._diferencas(
                        valor_antes, valor_depois, f"{caminho}[{indice + 1}]"
                    )
                )
            return diferencas
        if antes != depois:
            return {caminho: {"antes": antes, "depois": depois}}
        return {}

    def listar(self) -> list[dict[str, Any]]:
        """Lê uma cópia dos registros atuais."""
        with self.trava:
            registros = deepcopy(self.registros)
            eventos = deepcopy(self.historico)
        return self._incluir_alteracoes_atuais(registros, eventos)

    @staticmethod
    def _incluir_alteracoes_atuais(
        registros: list[dict[str, Any]], eventos: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Anexa ao registro as alterações da versão atualmente publicada."""
        eventos_por_chave = {
            (evento.get("processo"), evento.get("versao")): evento
            for evento in eventos
        }
        for registro in registros:
            chave = (
                registro["ficha"]["processo"],
                registro["versao"],
            )
            evento = eventos_por_chave.get(chave)
            registro["alteracoes_ultima_versao"] = (
                deepcopy(evento.get("alteracoes", {}))
                if evento and registro["versao"] > 1
                else {}
            )
        return registros

    def consultar(self, processo: str) -> dict[str, Any] | None:
        """Procura pela chave, rejeitando duplicidades existentes."""
        encontrados = [
            r for r in self.listar() if r["ficha"]["processo"] == processo
        ]
        if len(encontrados) > 1:
            raise ValueError("Processo duplicado na base. Gravação bloqueada.")
        return encontrados[0] if encontrados else None

    def gravar(
        self, ficha: dict[str, Any], versao: int, status: str, autor: str
    ) -> dict[str, Any]:
        """Salva com versão esperada; reenvio idêntico é idempotente."""
        if status not in ("Rascunho", "Concluída"):
            raise ValueError("Status desconhecido.")
        ficha = preparar(ficha)
        erros = validar(ficha, concluir=status == "Concluída")
        if erros:
            raise ValueError("\n".join(erros))
        if status == "Concluída":
            calcular(ficha)
        texto = json.dumps(ficha, ensure_ascii=False, sort_keys=True)
        if len(texto) > 45000:
            raise ValueError(
                "Ficha muito extensa. Reduza as justificativas para salvar."
            )
        with self.trava:
            atual = self.consultar(ficha["processo"])
            if atual and atual["ficha"] == ficha and atual["status"] == status:
                return atual
            if (
                atual
                and atual["status"] == "Concluída"
                and status == "Rascunho"
            ):
                raise ValueError(
                    "Ficha já concluída: revise e salve a atualização como concluída. "
                    "A versão publicada será preservada até essa gravação."
                )
            if (atual["versao"] if atual else 0) != versao:
                raise Conflito(
                    "Outra pessoa alterou esta ficha. Consulte novamente antes de editar."
                )
            novo = {
                "ficha": ficha,
                "versao": versao + 1,
                "status": status,
                "autor": autor,
                "atualizado_em": agora().isoformat(),
            }
            anterior = atual["ficha"] if atual else {}
            alteracoes = self._diferencas(anterior, ficha)
            evento = {
                "processo": ficha["processo"],
                "versao": novo["versao"],
                "status": status,
                "autor": autor,
                "data": novo["atualizado_em"],
                "hash": hashlib.sha256(texto.encode()).hexdigest(),
                "alteracoes": alteracoes,
            }
            if len(json.dumps(alteracoes, ensure_ascii=False)) > 45000:
                raise ValueError(
                    "Histórico da alteração excede o tamanho permitido."
                )
            self._persistir(novo, evento)
            confirmado = self.consultar(ficha["processo"])
            campos_confirmacao = (
                "ficha",
                "versao",
                "status",
                "autor",
                "atualizado_em",
            )
            if confirmado is None or any(
                confirmado.get(campo) != novo[campo]
                for campo in campos_confirmacao
            ):
                raise ValueError(
                    "Gravação sem confirmação. Consulte o processo antes de repetir."
                )
            return confirmado

    def excluir(self, processo: str, versao: int, autor: str) -> dict[str, Any]:
        """Remove uma ficha após conferir sua versão e registra a exclusão."""
        processo = normalizar_processo(processo)
        with self.trava:
            atual = self.consultar(processo)
            if atual is None:
                raise ValueError("Não há ficha cadastrada para excluir.")
            if atual["versao"] != versao:
                raise Conflito(
                    "A ficha foi alterada por outra pessoa. Consulte novamente antes de excluir."
                )
            texto = json.dumps(
                atual["ficha"], ensure_ascii=False, sort_keys=True
            )
            evento = {
                "processo": processo,
                "versao": versao + 1,
                "status": "Excluída",
                "autor": autor,
                "data": agora().isoformat(),
                "hash": hashlib.sha256(texto.encode()).hexdigest(),
                "alteracoes": {"registro": "Ficha excluída"},
            }
            self._excluir(atual, evento)
            if self.consultar(processo) is not None:
                raise ValueError(
                    "A exclusão não foi confirmada. Consulte o processo antes de repetir."
                )
            return evento

    def _excluir(
        self, registro: dict[str, Any], evento: dict[str, Any]
    ) -> None:
        """Remove do repositório temporário e conserva evento de auditoria."""
        processo = registro["ficha"]["processo"]
        self.registros = [
            atual
            for atual in self.registros
            if atual["ficha"]["processo"] != processo
        ]
        self.historico.append(deepcopy(evento))

    def _persistir(
        self, registro: dict[str, Any], evento: dict[str, Any]
    ) -> None:
        """Atualiza a base temporária de demonstração."""
        self.registros = [
            r
            for r in self.registros
            if r["ficha"]["processo"] != registro["ficha"]["processo"]
        ]
        self.registros.append(deepcopy(registro))
        self.historico.append(deepcopy(evento))


class RepositorioSheets(Repositorio):
    """Usa duas abas exclusivas, com dados e histórico em lote atômico.

    A trava cobre sessões do mesmo processo Python. Não cobre réplicas,
    edições diretas na planilha nem outra aplicação gravando na mesma base.
    """

    def __init__(
        self, credenciais: dict[str, Any], identificador: str
    ) -> None:
        super().__init__()
        import gspread
        from google.oauth2.service_account import Credentials

        # O acesso é feito pelo identificador, sem pesquisar todo o Drive.
        identidade = Credentials.from_service_account_info(
            credenciais,
            scopes=["https://www.googleapis.com/auth/spreadsheets"],
        )
        self.planilha = gspread.authorize(identidade).open_by_key(
            identificador
        )
        self.fichas = self.planilha.worksheet("Fichas")
        self.auditoria = self.planilha.worksheet("Historico")
        if self.fichas.row_values(1) != CABECALHO:
            raise ValueError("Cabeçalho da aba Fichas incompatível.")
        if self.auditoria.row_values(1) != HISTORICO:
            raise ValueError("Cabeçalho da aba Historico incompatível.")

    def listar(self) -> list[dict[str, Any]]:
        """Lê conteúdo canônico e verifica sua identidade com as colunas."""
        with self.trava:
            registros = []
            for linha in self.fichas.get_all_values()[1:]:
                if not any(linha):
                    continue
                if len(linha) < 6:
                    raise ValueError(
                        "Registro incompleto na base. Verifique com o responsável."
                    )
                ficha = json.loads(linha[5])
                if ficha["processo"] != linha[0]:
                    raise ValueError(
                        "Chave do processo divergente do conteúdo salvo."
                    )
                registros.append(
                    {
                        "ficha": ficha,
                        "versao": int(linha[1]),
                        "status": linha[2],
                        "autor": linha[3],
                        "atualizado_em": linha[4],
                    }
                )
            eventos = []
            for linha in self.auditoria.get_all_values()[1:]:
                if len(linha) < 7 or not linha[0] or not linha[1]:
                    continue
                try:
                    eventos.append(
                        {
                            "processo": linha[0],
                            "versao": int(linha[1]),
                            "alteracoes": json.loads(linha[6]),
                        }
                    )
                except (TypeError, ValueError, json.JSONDecodeError):
                    # Uma linha de auditoria inválida não deve impedir a consulta
                    # das fichas; ela simplesmente não participa do destaque.
                    continue
            return self._incluir_alteracoes_atuais(registros, eventos)

    def _persistir(
        self, registro: dict[str, Any], evento: dict[str, Any]
    ) -> None:
        """Atualiza a ficha e acrescenta a auditoria na mesma chamada."""
        linhas = self.fichas.get_all_values()
        processo = registro["ficha"]["processo"]
        indices = [
            i
            for i, linha in enumerate(linhas[1:], 1)
            if linha and linha[0] == processo
        ]
        if len(indices) > 1:
            raise ValueError("Processo duplicado. Gravação bloqueada.")
        valores = [
            processo,
            registro["versao"],
            registro["status"],
            registro["autor"],
            registro["atualizado_em"],
            json.dumps(registro["ficha"], ensure_ascii=False),
        ]
        auditoria = [
            processo,
            evento["versao"],
            evento["status"],
            evento["autor"],
            evento["data"],
            evento["hash"],
            json.dumps(evento["alteracoes"], ensure_ascii=False),
        ]

        def celulas(dados: list[Any]) -> dict[str, Any]:
            # Textos são gravados literalmente; não executam fórmulas.
            return {
                "values": [
                    {
                        "userEnteredValue": {"numberValue": valor}
                        if type(valor) is int
                        else {"stringValue": str(valor)}
                    }
                    for valor in dados
                ]
            }

        if indices:
            escrita = {
                "updateCells": {
                    "start": {
                        "sheetId": self.fichas.id,
                        "rowIndex": indices[0],
                        "columnIndex": 0,
                    },
                    "rows": [celulas(valores)],
                    "fields": "userEnteredValue",
                }
            }
        else:
            escrita = {
                "appendCells": {
                    "sheetId": self.fichas.id,
                    "rows": [celulas(valores)],
                    "fields": "userEnteredValue",
                }
            }
        self.planilha.batch_update(
            {
                "requests": [
                    escrita,
                    {
                        "appendCells": {
                            "sheetId": self.auditoria.id,
                            "rows": [celulas(auditoria)],
                            "fields": "userEnteredValue",
                        }
                    },
                ]
            }
        )

    def _excluir(
        self, registro: dict[str, Any], evento: dict[str, Any]
    ) -> None:
        """Exclui a linha ativa e acrescenta auditoria na mesma operação."""
        linhas = self.fichas.get_all_values()
        processo = registro["ficha"]["processo"]
        indices = [
            indice
            for indice, linha in enumerate(linhas[1:], 1)
            if linha and linha[0] == processo
        ]
        if len(indices) != 1:
            raise ValueError(
                "A ficha não foi localizada de forma única. Exclusão cancelada."
            )
        indice = indices[0]
        if len(linhas[indice]) < 2 or int(linhas[indice][1]) != evento["versao"] - 1:
            raise Conflito(
                "A ficha foi alterada por outra pessoa. Consulte novamente antes de excluir."
            )

        valores_auditoria = [
            evento["processo"],
            evento["versao"],
            evento["status"],
            evento["autor"],
            evento["data"],
            evento["hash"],
            json.dumps(evento["alteracoes"], ensure_ascii=False),
        ]
        celulas = {
            "values": [
                {"userEnteredValue": {"stringValue": str(valor)}}
                for valor in valores_auditoria
            ]
        }
        self.planilha.batch_update(
            {
                "requests": [
                    {
                        "deleteDimension": {
                            "range": {
                                "sheetId": self.fichas.id,
                                "dimension": "ROWS",
                                "startIndex": indice,
                                "endIndex": indice + 1,
                            }
                        }
                    },
                    {
                        "appendCells": {
                            "sheetId": self.auditoria.id,
                            "rows": [celulas],
                            "fields": "userEnteredValue",
                        }
                    },
                ]
            }
        )
