"""Proteções para adequar somente a amostra antiga de 13 municípios."""

from __future__ import annotations

import unittest
from pathlib import Path

from icms.demonstracao import (
    adequar_exemplos_legados,
    contar_exemplos_legados,
    indice_exemplo_legado,
)
from icms.regras import MUNICIPAIS, calcular, nova_linha_municipal
from icms.repositorio import Repositorio
from tests.test_regras import ficha_valida

RAIZ = Path(__file__).resolve().parents[1]


def ficha_antiga(numero: int) -> dict:
    """Simula a estrutura do backup de demonstração antigo, com 13 entradas."""
    ficha = ficha_valida()
    ficha["processo"] = f"9999.99.{9200000 + numero:07d}/2026-00"
    ficha["unidade"] = f"UC SINTÉTICA COMPLETA {numero:02d} — DEMONSTRAÇÃO"
    ficha["municipios"] = [
        {
            "nome": f"Município sintético {indice:02d}",
            **{codigo: (indice + n) % 10 for n, codigo in enumerate(MUNICIPAIS)},
        }
        for indice in range(1, 14)
    ]
    return ficha


class TesteAdequacaoDemonstracao(unittest.TestCase):
    """Evita trazer 13 linhas dos exemplos legados para cada ficha."""

    def test_ficha_nova_continua_com_uma_linha(self) -> None:
        """Nenhum limite fixo de 13 deve surgir em cadastro novo."""
        ficha = ficha_valida()
        self.assertEqual(len(ficha["municipios"]), 1)

    def test_exemplo_antigo_e_reconhecido(self) -> None:
        """Reconhece apenas o conjunto antigo de 13 nomes padronizados."""
        repo = Repositorio()
        salvo = repo.gravar(ficha_antiga(1), 0, "Concluída", "demonstracao")
        self.assertEqual(indice_exemplo_legado(salvo), 0)
        self.assertEqual(contar_exemplos_legados(repo.listar()), 1)

    def test_adequacao_preserva_uma_linha_por_processo_e_fq(self) -> None:
        """Cada ficha mantém um município distinto, com histórico auditado."""
        repo = Repositorio()
        for numero in (1, 2, 10):
            repo.gravar(ficha_antiga(numero), 0, "Concluída", "demonstracao")
        antes = {
            registro["ficha"]["processo"]: registro
            for registro in repo.listar()
        }
        self.assertEqual(contar_exemplos_legados(list(antes.values())), 3)
        self.assertEqual(adequar_exemplos_legados(repo, "teste_adequacao"), 3)
        vistos: set[str] = set()
        for registro in repo.listar():
            ficha = registro["ficha"]
            processo = ficha["processo"]
            indice = int(processo.split("/")[0][-2:]) - 1
            nome = ficha["municipios"][0]["nome"]
            self.assertEqual(len(ficha["municipios"]), 1)
            self.assertEqual(nome, f"município sintético {indice + 1:02d}")
            self.assertNotIn(nome, vistos)
            vistos.add(nome)
            self.assertEqual(registro["versao"], 2)
            self.assertEqual(len(calcular(ficha)["municipios"]), 1)
            self.assertEqual(
                ficha["municipios"][0]["10"]["validado"],
                antes[processo]["ficha"]["municipios"][indice]["10"]["validado"],
            )
        self.assertEqual(adequar_exemplos_legados(repo, "teste_adequacao"), 0)

    def test_backup_legado_restaurado_pode_ser_adequado(self) -> None:
        """A adequação funciona também após importar o backup CSV antigo."""
        fonte = Repositorio()
        for numero in (1, 2):
            fonte.gravar(ficha_antiga(numero), 0, "Concluída", "demonstracao")
        restaurado = Repositorio()
        self.assertEqual(
            restaurado.restaurar_backup_csv(fonte.exportar_backup_csv()), 2
        )
        self.assertEqual(contar_exemplos_legados(restaurado.listar()), 2)
        self.assertEqual(adequar_exemplos_legados(restaurado, "teste"), 2)
        self.assertEqual(
            [len(r["ficha"]["municipios"]) for r in restaurado.listar()],
            [1, 1],
        )

    def test_ficha_real_com_varios_municipios_nao_e_modificada(self) -> None:
        """Nunca apaga registros verdadeiros ou incluídos manualmente."""
        repo = Repositorio()
        ficha = ficha_valida()
        ficha["municipios"].append(nova_linha_municipal("Município 02"))
        for codigo in MUNICIPAIS:
            ficha["municipios"][1][codigo].update(gestor=1, validado=1)
        repo.gravar(ficha, 0, "Concluída", "teste")
        self.assertEqual(contar_exemplos_legados(repo.listar()), 0)
        self.assertEqual(adequar_exemplos_legados(repo, "teste"), 0)
        self.assertEqual(len(repo.listar()[0]["ficha"]["municipios"]), 2)
        self.assertEqual(repo.listar()[0]["versao"], 1)

    def test_nome_sintetico_sozinho_nao_autoriza_exclusao(self) -> None:
        """Ficha antiga fora do conjunto reconhecido não é modificada."""
        repo = Repositorio()
        ficha = ficha_antiga(3)
        ficha["unidade"] = "Unidade de conservação real"
        repo.gravar(ficha, 0, "Concluída", "teste")
        self.assertEqual(adequar_exemplos_legados(repo, "teste"), 0)
        self.assertEqual(len(repo.listar()[0]["ficha"]["municipios"]), 13)

    def test_nova_amostra_csv_tem_um_municipio_por_ficha(self) -> None:
        """O arquivo disponibilizado para novos testes já usa o modelo atual."""
        dados = (RAIZ / "backup_fichas_icms_10_sinteticas_completas.csv").read_bytes()
        repo = Repositorio()
        self.assertEqual(repo.restaurar_backup_csv(dados), 10)
        nomes = [
            registro["ficha"]["municipios"][0]["nome"]
            for registro in repo.listar()
        ]
        self.assertEqual(len(nomes), len(set(nomes)))
        self.assertEqual(len(nomes), 10)
        self.assertTrue(all(len(r["ficha"]["municipios"]) == 1 for r in repo.listar()))
        self.assertEqual(contar_exemplos_legados(repo.listar()), 0)


if __name__ == "__main__":
    unittest.main()
