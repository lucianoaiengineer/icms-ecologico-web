"""Armazenamento SQL transacional e edições automáticas por usuário.

SQLite é próprio de servidores com volume persistente. Em Streamlit Community
Cloud, usar PostgreSQL externo (o disco local da hospedagem é efêmero).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sqlalchemy import (
    Column,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    and_,
    create_engine,
    delete,
    insert,
    select,
    update,
)
from sqlalchemy.exc import IntegrityError

from icms.regras import agora
from icms.repositorio import Conflito, Repositorio

META = MetaData()
FICHAS = Table(
    "icms_fichas", META,
    Column("processo", String(40), primary_key=True),
    Column("versao", Integer, nullable=False),
    Column("status", String(20), nullable=False),
    Column("autor", String(320), nullable=False),
    Column("atualizado_em", Text, nullable=False),
    Column("conteudo_json", Text, nullable=False),
)
HISTORICO = Table(
    "icms_historico", META,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("processo", String(40), nullable=False, index=True),
    Column("versao", Integer, nullable=False),
    Column("status", String(20), nullable=False),
    Column("autor", String(320), nullable=False),
    Column("data", Text, nullable=False),
    Column("hash", String(64), nullable=False),
    Column("alteracoes_json", Text, nullable=False),
)
EDICOES = Table(
    "icms_edicoes_automaticas", META,
    Column("autor", String(320), primary_key=True),
    Column("chave", String(40), primary_key=True),
    Column("processo", String(40), nullable=False),
    Column("ficha_json", Text, nullable=False),
    Column("original_json", Text, nullable=False),
    Column("versao", Integer, nullable=False),
    Column("status", String(20), nullable=False),
    Column("atualizado_em", Text, nullable=False),
)


def chave_edicao(ficha: dict[str, Any]) -> str:
    """Usa o SEI ou marcador interno para uma ficha sem chave definida."""
    return str(ficha.get("processo", "")).strip() or "__nova__"


class RepositorioSQL(Repositorio):
    """Implementa a API original em SQL, sem mudar as regras das fichas.

    `gravar` e `excluir` continuam validando pela classe base; as escritas
    repetem o teste da versão dentro da transação, inclusive entre processos.
    """

    def __init__(self, url: str) -> None:
        super().__init__()
        if not url.startswith(("sqlite:///", "postgresql+psycopg://")):
            raise ValueError("Use SQLite local ou PostgreSQL com driver psycopg.")
        if url.startswith("sqlite:///"):
            arquivo = url.removeprefix("sqlite:///")
            if arquivo != ":memory:":
                Path(arquivo).expanduser().parent.mkdir(parents=True, exist_ok=True)
        self.engine = create_engine(url, pool_pre_ping=True, future=True,
                                    connect_args={"timeout": 20} if url.startswith("sqlite:///") else {})
        META.create_all(self.engine)

    def listar(self) -> list[dict[str, Any]]:
        """Lê apenas fichas ativas; exclusões desaparecem dos resultados."""
        with self.engine.connect() as conexao:
            fichas = conexao.execute(select(FICHAS)).mappings().all()
            eventos = conexao.execute(
                select(HISTORICO.c.processo, HISTORICO.c.versao,
                       HISTORICO.c.alteracoes_json).order_by(HISTORICO.c.id)
            ).mappings().all()
        registros = [
            {
                "ficha": json.loads(linha["conteudo_json"]),
                "versao": linha["versao"], "status": linha["status"],
                "autor": linha["autor"], "atualizado_em": linha["atualizado_em"],
            }
            for linha in fichas
        ]
        alteracoes = [
            {"processo": linha["processo"], "versao": linha["versao"],
             "alteracoes": json.loads(linha["alteracoes_json"])}
            for linha in eventos
        ]
        return self._incluir_alteracoes_atuais(registros, alteracoes)

    def _persistir(self, registro: dict[str, Any], evento: dict[str, Any]) -> None:
        """Grava ficha e evento com verificação atômica da versão esperada."""
        processo = registro["ficha"]["processo"]
        esperado = registro["versao"] - 1
        valores = dict(
            processo=processo, versao=registro["versao"],
            status=registro["status"], autor=registro["autor"],
            atualizado_em=registro["atualizado_em"],
            conteudo_json=json.dumps(registro["ficha"], ensure_ascii=False, sort_keys=True),
        )
        with self.engine.begin() as conexao:
            if esperado == 0:
                try:
                    # Transação externa faz o histórico voltar atrás em caso de erro.
                    conexao.execute(insert(FICHAS).values(**valores))
                except IntegrityError as erro:
                    raise Conflito("Ficha já cadastrada. Consulte novamente.") from erro
            else:
                resultado = conexao.execute(
                    update(FICHAS)
                    .where(and_(FICHAS.c.processo == processo, FICHAS.c.versao == esperado))
                    .values(**valores)
                )
                if resultado.rowcount != 1:
                    raise Conflito("Outra pessoa alterou a ficha. Consulte novamente.")
            conexao.execute(insert(HISTORICO).values(
                processo=processo, versao=evento["versao"],
                status=evento["status"], autor=evento["autor"],
                data=evento["data"], hash=evento["hash"],
                alteracoes_json=json.dumps(evento["alteracoes"], ensure_ascii=False),
            ))
            # Autosaves antigos da mesma versão não devem ressurgir após gravação.
            conexao.execute(delete(EDICOES).where(and_(
                EDICOES.c.autor == registro["autor"], EDICOES.c.chave == processo
            )))

    def _excluir(self, registro: dict[str, Any], evento: dict[str, Any]) -> None:
        """Exclui a ficha e suas cópias automáticas sem apagar o histórico."""
        processo = registro["ficha"]["processo"]
        with self.engine.begin() as conexao:
            removido = conexao.execute(delete(FICHAS).where(and_(
                FICHAS.c.processo == processo,
                FICHAS.c.versao == registro["versao"],
            )))
            if removido.rowcount != 1:
                raise Conflito("Ficha alterada ou excluída. Consulte novamente.")
            conexao.execute(insert(HISTORICO).values(
                processo=processo, versao=evento["versao"],
                status=evento["status"], autor=evento["autor"],
                data=evento["data"], hash=evento["hash"],
                alteracoes_json=json.dumps(evento["alteracoes"], ensure_ascii=False),
            ))
            conexao.execute(delete(EDICOES).where(EDICOES.c.processo == processo))

    def salvar_edicao(
        self, autor: str, ficha: dict[str, Any], original: dict[str, Any],
        versao: int, status: str,
    ) -> None:
        """Guarda edição não concluída, sem afetar a ficha oficial e o relatório."""
        if not autor or autor == "demonstracao":
            raise ValueError("Salvamento automático requer usuário autenticado.")
        chave = chave_edicao(ficha)
        atual = dict(
            autor=autor, chave=chave, processo=str(ficha.get("processo", "")),
            ficha_json=json.dumps(ficha, ensure_ascii=False, sort_keys=True),
            original_json=json.dumps(original, ensure_ascii=False, sort_keys=True),
            versao=versao, status=status, atualizado_em=agora().isoformat(),
        )
        if len(atual["ficha_json"]) > 150000:
            raise ValueError("Edição excede o limite de segurança para recuperação.")
        # Upsert atômico compatível com SQLite e PostgreSQL.
        if self.engine.dialect.name == "sqlite":
            from sqlalchemy.dialects.sqlite import insert as upsert
        else:
            from sqlalchemy.dialects.postgresql import insert as upsert
        comando = upsert(EDICOES).values(**atual)
        comando = comando.on_conflict_do_update(
            index_elements=[EDICOES.c.autor, EDICOES.c.chave],
            set_={coluna: valor for coluna, valor in atual.items()
                  if coluna not in ("autor", "chave")},
        )
        with self.engine.begin() as conexao:
            conexao.execute(comando)

    def listar_edicoes(self, autor: str) -> list[dict[str, Any]]:
        """Expõe somente autosaves do usuário autenticado."""
        with self.engine.connect() as conexao:
            linhas = conexao.execute(
                select(EDICOES).where(EDICOES.c.autor == autor)
                .order_by(EDICOES.c.atualizado_em.desc())
            ).mappings().all()
        return [
            {
                "chave": linha["chave"], "processo": linha["processo"],
                "ficha": json.loads(linha["ficha_json"]),
                "original": json.loads(linha["original_json"]),
                "versao": linha["versao"], "status": linha["status"],
                "atualizado_em": linha["atualizado_em"],
            }
            for linha in linhas
        ]

    def excluir_edicao(self, autor: str, chave: str) -> None:
        """Descarta cópia de recuperação, não a ficha gravada."""
        with self.engine.begin() as conexao:
            conexao.execute(delete(EDICOES).where(and_(
                EDICOES.c.autor == autor, EDICOES.c.chave == chave
            )))
