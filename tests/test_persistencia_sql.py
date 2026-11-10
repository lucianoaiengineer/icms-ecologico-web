"""Regressões de persistência e recuperação de edições interrompidas."""

import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from pathlib import Path

from icms.regras import nova_ficha
from icms.repositorio import Conflito
from icms.repositorio_sql import RepositorioSQL
from tests.test_regras import ficha_valida


class TestePersistenciaSQL(unittest.TestCase):
    def setUp(self) -> None:
        """Abre SQLite temporário isolado para cada teste."""
        self.diretorio = tempfile.TemporaryDirectory()
        self.url = f"sqlite:///{Path(self.diretorio.name) / 'icms.sqlite'}"
        self.base = RepositorioSQL(self.url)

    def tearDown(self) -> None:
        """Fecha a conexão e remove o banco de teste."""
        self.base.engine.dispose()
        self.diretorio.cleanup()

    def test_ficha_e_historico_sobrevivem_nova_conexao(self) -> None:
        """Ficha e historico sobrevivem nova conexao."""
        ficha = ficha_valida()
        salvo = self.base.gravar(ficha, 0, "Concluída", "editor@exemplo.org")
        self.assertEqual(salvo["versao"], 1)
        self.base.engine.dispose()
        outra_sessao = RepositorioSQL(self.url)
        try:
            consulta = outra_sessao.consultar(ficha["processo"])
            self.assertEqual(consulta["ficha"], ficha)
            self.assertEqual(consulta["status"], "Concluída")
            self.assertEqual(len(outra_sessao.listar()), 1)
        finally:
            outra_sessao.engine.dispose()

    def test_edicao_automatica_nao_altera_registro_concluido(self) -> None:
        """Edicao automatica nao altera registro concluido."""
        ficha = ficha_valida()
        self.base.gravar(ficha, 0, "Concluída", "editor@exemplo.org")
        edicao = deepcopy(ficha)
        edicao["unidade"] = "Unidade ainda não confirmada"
        self.base.salvar_edicao("editor@exemplo.org", edicao, ficha, 1, "Concluída")
        self.assertEqual(self.base.consultar(ficha["processo"])["ficha"], ficha)
        self.assertEqual(
            self.base.listar_edicoes("editor@exemplo.org")[0]["ficha"],
            edicao,
        )
        self.assertEqual(self.base.listar_edicoes("outro@exemplo.org"), [])
        nova_sessao = RepositorioSQL(self.url)
        try:
            self.assertEqual(
                nova_sessao.listar_edicoes("editor@exemplo.org")[0]["ficha"],
                edicao,
            )
        finally:
            nova_sessao.engine.dispose()

    def test_gravacao_confirmada_apaga_autosalvamento_da_ficha(self) -> None:
        """Gravacao confirmada apaga autosalvamento da ficha."""
        ficha = ficha_valida()
        self.base.gravar(ficha, 0, "Concluída", "editor@exemplo.org")
        nova = deepcopy(ficha)
        nova["unidade"] = "Alteração confirmada"
        self.base.salvar_edicao("editor@exemplo.org", nova, ficha, 1, "Concluída")
        salvo = self.base.gravar(nova, 1, "Concluída", "editor@exemplo.org")
        self.assertEqual(salvo["versao"], 2)
        self.assertEqual(self.base.listar_edicoes("editor@exemplo.org"), [])
        mudanca = self.base.listar()[0]["alteracoes_ultima_versao"]["unidade"]
        self.assertEqual(mudanca["depois"], "Alteração confirmada")

    def test_exclusao_remove_do_relatorio_e_autosalvamentos_de_todos(self) -> None:
        """Exclusao remove do relatorio e autosalvamentos de todos."""
        ficha = ficha_valida()
        self.base.gravar(ficha, 0, "Concluída", "editor@exemplo.org")
        for usuario in ("editor@exemplo.org", "outro@exemplo.org"):
            alterada = deepcopy(ficha)
            alterada["responsavel"] = usuario
            self.base.salvar_edicao(usuario, alterada, ficha, 1, "Concluída")
        self.base.excluir(ficha["processo"], 1, "editor@exemplo.org")
        self.assertEqual(self.base.listar(), [])
        self.assertEqual(self.base.listar_edicoes("editor@exemplo.org"), [])
        self.assertEqual(self.base.listar_edicoes("outro@exemplo.org"), [])
        outra_sessao = RepositorioSQL(self.url)
        try:
            self.assertEqual(outra_sessao.listar(), [])
        finally:
            outra_sessao.engine.dispose()

    def test_gravacoes_de_duas_instancias_nao_sobrescrevem_versao(self) -> None:
        """Gravacoes de duas instancias nao sobrescrevem versao."""
        ficha = ficha_valida()
        self.base.gravar(ficha, 0, "Concluída", "editor@exemplo.org")
        a = RepositorioSQL(self.url)
        b = RepositorioSQL(self.url)
        try:
            primeira = deepcopy(ficha)
            segunda = deepcopy(ficha)
            primeira["unidade"] = "A"
            segunda["unidade"] = "B"

            def tentar(argumentos: tuple[RepositorioSQL, dict, str]) -> str:
                """Tenta gravar uma versão anterior em uma conexão diferente."""
                repo, conteudo, autor = argumentos
                try:
                    repo.gravar(conteudo, 1, "Concluída", autor)
                    return "gravado"
                except Conflito:
                    return "conflito"
            with ThreadPoolExecutor(max_workers=2) as executor:
                resultados = list(
                    executor.map(
                        tentar,
                        [
                            (a, primeira, "a@exemplo.org"),
                            (b, segunda, "b@exemplo.org"),
                        ],
                    )
                )
            self.assertEqual(sorted(resultados), ["conflito", "gravado"])
            self.assertEqual(self.base.consultar(ficha["processo"])["versao"], 2)
        finally:
            a.engine.dispose()
            b.engine.dispose()

    def test_copia_de_ficha_nova_sem_sei_pode_ser_recuperada(self) -> None:
        """Copia de ficha nova sem sei pode ser recuperada."""
        ficha = nova_ficha()
        ficha["unidade"] = "Trabalho interrompido"
        original = nova_ficha()
        self.base.salvar_edicao("editor@exemplo.org", ficha, original, 0, "")
        copias = self.base.listar_edicoes("editor@exemplo.org")
        self.assertEqual(len(copias), 1)
        self.assertEqual(copias[0]["chave"], "__nova__")
        self.assertEqual(copias[0]["ficha"]["unidade"], "Trabalho interrompido")
        self.base.excluir_edicao("editor@exemplo.org", "__nova__")
        self.assertEqual(self.base.listar_edicoes("editor@exemplo.org"), [])


if __name__ == "__main__":
    unittest.main()
