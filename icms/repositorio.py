"""Persistência, restauração CSV e controle de versão das fichas do projeto."""

import csv
import hashlib
import io
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
CABECALHO_BACKUP_CSV = [*CABECALHO, "historico_json"]


class Conflito(ValueError):
    """Indica uma edição baseada em versão antiga."""


class Repositorio:
    """Coordena leitura, validação e gravação em uma instância do app."""

    def __init__(self) -> None:
        """Inicializa o repositório temporário e seu histórico em memória."""
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
            (evento.get("processo"), evento.get("versao")): evento for evento in eventos
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
            registro
            for registro in self.listar()
            if registro["ficha"]["processo"] == processo
        ]
        if len(encontrados) > 1:
            raise ValueError("Processo duplicado na base. Gravação bloqueada.")
        return encontrados[0] if encontrados else None

    def gravar(
        self, ficha: dict[str, Any], versao: int, situacao: str, autor: str
    ) -> dict[str, Any]:
        """Salva com versão esperada; reenvio idêntico é idempotente."""
        if situacao not in ("Rascunho", "Concluída"):
            raise ValueError("Status desconhecido.")
        ficha = preparar(ficha)
        erros = validar(ficha, concluir=situacao == "Concluída")
        if erros:
            raise ValueError("\n".join(erros))
        if situacao == "Concluída":
            calcular(ficha)
        texto = json.dumps(ficha, ensure_ascii=False, sort_keys=True)
        if len(texto) > 45000:
            raise ValueError(
                "Ficha muito extensa. Reduza as justificativas para salvar."
            )
        with self.trava:
            atual = self.consultar(ficha["processo"])
            if atual and atual["ficha"] == ficha and atual["status"] == situacao:
                return atual
            if atual and atual["status"] == "Concluída" and situacao == "Rascunho":
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
                "status": situacao,
                "autor": autor,
                "atualizado_em": agora().isoformat(),
            }
            anterior = atual["ficha"] if atual else {}
            alteracoes = self._diferencas(anterior, ficha)
            evento = {
                "processo": ficha["processo"],
                "versao": novo["versao"],
                "status": situacao,
                "autor": autor,
                "data": novo["atualizado_em"],
                "hash": hashlib.sha256(texto.encode()).hexdigest(),
                "alteracoes": alteracoes,
            }
            if len(json.dumps(alteracoes, ensure_ascii=False)) > 45000:
                raise ValueError("Histórico da alteração excede o tamanho permitido.")
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
                confirmado.get(campo) != novo[campo] for campo in campos_confirmacao
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
            texto = json.dumps(atual["ficha"], ensure_ascii=False, sort_keys=True)
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

    def exportar_backup_csv(self) -> bytes:
        """Exporta fichas completas e seus históricos para restauração posterior.

        O arquivo é um backup de demonstração, distinto do CSV de resultados.
        Cada ficha fica em uma linha; campos aninhados são serializados em JSON.
        """
        if type(self) is not Repositorio:
            raise ValueError(
                "O backup CSV está disponível somente no modo demonstração."
            )

        with self.trava:
            arquivo_csv = io.StringIO(newline="")
            escritor = csv.DictWriter(
                arquivo_csv,
                fieldnames=CABECALHO_BACKUP_CSV,
                delimiter=";",
                lineterminator="\n",
            )
            escritor.writeheader()
            eventos_por_processo: dict[str, list[dict[str, Any]]] = {}
            for evento in self.historico:
                eventos_por_processo.setdefault(evento["processo"], []).append(evento)

            for registro in self.registros:
                ficha = registro["ficha"]
                escritor.writerow(
                    {
                        "processo": ficha["processo"],
                        "versao": registro["versao"],
                        "status": registro["status"],
                        "autor": registro["autor"],
                        "atualizado_em": registro["atualizado_em"],
                        "conteudo_json": json.dumps(
                            ficha, ensure_ascii=False, sort_keys=True
                        ),
                        "historico_json": json.dumps(
                            eventos_por_processo.get(ficha["processo"], []),
                            ensure_ascii=False,
                            sort_keys=True,
                        ),
                    }
                )

        return arquivo_csv.getvalue().encode("utf-8-sig")

    def restaurar_backup_csv(self, conteudo_csv: bytes) -> int:
        """Restaura sem sobrescrever registros existentes ou mesclar conflitos.

        Retorna a quantidade de fichas novas. Reimportar o mesmo backup é seguro:
        fichas e eventos idênticos são ignorados.
        """
        if type(self) is not Repositorio:
            raise ValueError(
                "A restauração CSV está disponível somente no modo demonstração."
            )
        if len(conteudo_csv) > 50 * 1024 * 1024:
            raise ValueError("O arquivo de backup excede o limite de 50 MB.")

        try:
            texto_csv = conteudo_csv.decode("utf-8-sig")
            leitor = csv.DictReader(io.StringIO(texto_csv, newline=""), delimiter=";")
            if leitor.fieldnames != CABECALHO_BACKUP_CSV:
                raise ValueError("O cabeçalho do backup CSV não é compatível.")

            fichas_importadas: list[dict[str, Any]] = []
            eventos_importados: list[dict[str, Any]] = []
            processos_no_arquivo: set[str] = set()
            for linha in leitor:
                ficha = preparar(json.loads(linha["conteudo_json"]))
                processo = ficha["processo"]
                versao = int(linha["versao"])
                situacao = linha["status"]
                if processo != linha["processo"] or versao < 1:
                    raise ValueError("A chave ou a versão de uma ficha é inválida.")
                if situacao not in ("Rascunho", "Concluída"):
                    raise ValueError("O backup contém uma situação desconhecida.")
                if processo in processos_no_arquivo:
                    raise ValueError(f"O processo {processo} está duplicado no CSV.")
                erros = validar(ficha, concluir=situacao == "Concluída")
                if erros:
                    raise ValueError(
                        f"A ficha {processo} contém dados inválidos: "
                        + "; ".join(erros)
                    )
                if situacao == "Concluída":
                    calcular(ficha)
                processos_no_arquivo.add(processo)
                fichas_importadas.append(
                    {
                        "ficha": ficha,
                        "versao": versao,
                        "status": situacao,
                        "autor": linha["autor"],
                        "atualizado_em": linha["atualizado_em"],
                    }
                )

                historico = json.loads(linha["historico_json"] or "[]")
                if not isinstance(historico, list):
                    raise ValueError("O histórico do backup tem formato inválido.")
                for evento in historico:
                    if (
                        not isinstance(evento, dict)
                        or evento.get("processo") != processo
                        or not isinstance(evento.get("alteracoes"), dict)
                    ):
                        raise ValueError(
                            f"O histórico da ficha {processo} não é compatível."
                        )
                    eventos_importados.append(evento)
        except (
            UnicodeDecodeError,
            csv.Error,
            KeyError,
            TypeError,
            json.JSONDecodeError,
        ) as erro:
            raise ValueError("Não foi possível ler o backup CSV selecionado.") from erro

        with self.trava:
            atuais = {
                registro["ficha"]["processo"]: registro for registro in self.registros
            }
            novos_registros: list[dict[str, Any]] = []
            for registro in fichas_importadas:
                processo = registro["ficha"]["processo"]
                existente = atuais.get(processo)
                if existente is None:
                    novos_registros.append(registro)
                elif any(
                    existente.get(campo) != registro.get(campo)
                    for campo in ("ficha", "versao", "status", "atualizado_em")
                ):
                    raise ValueError(
                        f"O processo {processo} já existe com outra versão. "
                        "A restauração foi cancelada sem alterar os dados."
                    )

            eventos_atuais = {
                (evento["processo"], evento["versao"]): evento
                for evento in self.historico
            }
            novos_eventos: list[dict[str, Any]] = []
            for evento in eventos_importados:
                chave_evento = (evento["processo"], evento["versao"])
                evento_existente = eventos_atuais.get(chave_evento)
                if evento_existente is None:
                    novos_eventos.append(evento)
                elif evento_existente != evento:
                    raise ValueError(
                        "O histórico do CSV conflita com o histórico atual. "
                        "A restauração foi cancelada sem alterar os dados."
                    )

            self.registros.extend(deepcopy(novos_registros))
            self.historico.extend(deepcopy(novos_eventos))
        return len(novos_registros)

    def _excluir(self, registro: dict[str, Any], evento: dict[str, Any]) -> None:
        """Remove do repositório temporário e conserva evento de auditoria."""
        processo = registro["ficha"]["processo"]
        self.registros = [
            atual for atual in self.registros if atual["ficha"]["processo"] != processo
        ]
        self.historico.append(deepcopy(evento))

    def _persistir(self, registro: dict[str, Any], evento: dict[str, Any]) -> None:
        """Atualiza a base temporária de demonstração."""
        self.registros = [
            registro
            for registro in self.registros
            if registro["ficha"]["processo"] != registro["ficha"]["processo"]
        ]
        self.registros.append(deepcopy(registro))
        self.historico.append(deepcopy(evento))


class RepositorioSheets(Repositorio):
    """Usa duas abas exclusivas, com dados e histórico em lote atômico.

    A trava cobre sessões do mesmo processo Python. Não cobre réplicas,
    edições diretas na planilha nem outra aplicação gravando na mesma base.
    """

    def __init__(self, credenciais: dict[str, Any], identificador: str) -> None:
        """Conecta às abas de fichas e auditoria da planilha configurada."""
        super().__init__()
        import gspread
        from google.oauth2.service_account import Credentials

        # O acesso é feito pelo identificador, sem pesquisar todo o Drive.
        identidade = Credentials.from_service_account_info(
            credenciais,
            scopes=["https://www.googleapis.com/auth/spreadsheets"],
        )
        self.planilha = gspread.authorize(identidade).open_by_key(identificador)
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
                    raise ValueError("Chave do processo divergente do conteúdo salvo.")
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

    def _persistir(self, registro: dict[str, Any], evento: dict[str, Any]) -> None:
        """Atualiza a ficha e acrescenta a auditoria na mesma chamada."""
        linhas = self.fichas.get_all_values()
        processo = registro["ficha"]["processo"]
        indices = [
            indice
            for indice, linha in enumerate(linhas[1:], 1)
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
            """Converte valores para o formato de escrita da API do Sheets."""
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

    def _excluir(self, registro: dict[str, Any], evento: dict[str, Any]) -> None:
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
