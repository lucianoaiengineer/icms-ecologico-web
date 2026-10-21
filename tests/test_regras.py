"""Verificações de cálculo, rascunhos e concorrência por versão."""

import unittest
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy

from icms.regras import calcular, normalizar_processo, nova_ficha, validar
from icms.repositorio import Conflito, Repositorio


def ficha_valida() -> dict:
    """Monta uma entrada sintética com soma validada conhecida de 34."""
    ficha = nova_ficha()
    ficha.update(
        processo="0000.00.0000001/2026-00", unidade="UC demonstrativa"
    )
    valores = [6, 0, 0, 9, 0, 0, 0, 0, 2, 6, 2, 2, 2, 5]
    for pontos, valor in zip(ficha["parametros"].values(), valores):
        pontos.update(gestor=valor, validado=valor)
    ficha["municipios"][0].update(
        nome="Município demonstrativo",
        **{"10": 0, "11.1": 0, "11.2": 0, "11.3": 0},
    )
    return ficha


class TesteRegras(unittest.TestCase):
    """Confere regras relevantes sem acesso a contas externas."""

    def test_fator_base(self) -> None:
        self.assertEqual(
            calcular(ficha_valida())["municipios"][0]["FQ"], "0,38"
        )

    def test_valor_de_outro_municipio_nao_altera_primeiro(self) -> None:
        ficha = ficha_valida()
        ficha["municipios"][1].update(
            nome="Outro município",
            **{"10": 9, "11.1": 9, "11.2": 9, "11.3": 9},
        )
        calculo = calcular(ficha)
        self.assertEqual(calculo["municipios"][0]["Soma"], 34)
        self.assertEqual(calculo["municipios"][1]["Soma"], 70)
        self.assertEqual(
            calculo["totais"], {"10": 9, "11.1": 9, "11.2": 9, "11.3": 9}
        )

    def test_divisor_zero(self) -> None:
        ficha = ficha_valida()
        ficha["pontuacao_categoria"] = 0
        with self.assertRaises(ValueError):
            calcular(ficha)

    def test_limite_pontuacao(self) -> None:
        for valor in (-1, 10, 1.5, True):
            ficha = ficha_valida()
            ficha["parametros"]["1.1"]["validado"] = valor
            self.assertTrue(validar(ficha))

    def test_vazio_nao_equivale_a_zero(self) -> None:
        ficha = ficha_valida()
        ficha["municipios"][0]["10"] = None
        self.assertFalse(validar(ficha))
        self.assertTrue(validar(ficha, concluir=True))

    def test_pontos_sem_municipio(self) -> None:
        ficha = ficha_valida()
        ficha["municipios"][5]["10"] = 6
        self.assertTrue(validar(ficha))

    def test_municipio_duplicado(self) -> None:
        ficha = ficha_valida()
        ficha["municipios"][1] = deepcopy(ficha["municipios"][0])
        self.assertTrue(validar(ficha))

    def test_normalizacao_preserva_zeros(self) -> None:
        self.assertEqual(
            normalizar_processo("0000000000001202600"),
            "0000.00.0000001/2026-00",
        )

    def test_data_impossivel(self) -> None:
        ficha = ficha_valida()
        ficha["recebimento"] = "2026-02-30"
        self.assertTrue(validar(ficha))

    def test_rascunho_e_atualizacao(self) -> None:
        repositorio = Repositorio()
        ficha = nova_ficha()
        ficha["processo"] = "0000.00.0000001/2026-00"
        salvo = repositorio.gravar(ficha, 0, "Rascunho", "usuario")
        self.assertEqual(salvo["versao"], 1)
        ficha["unidade"] = "UC alterada"
        repositorio.gravar(ficha, 1, "Rascunho", "usuario")
        self.assertEqual(len(repositorio.listar()), 1)
        self.assertEqual(len(repositorio.historico), 2)

    def test_reenvio_identico(self) -> None:
        repositorio = Repositorio()
        ficha = ficha_valida()
        repositorio.gravar(ficha, 0, "Concluída", "usuario")
        repositorio.gravar(ficha, 0, "Concluída", "usuario")
        self.assertEqual(len(repositorio.historico), 1)

    def test_edicao_concorrente(self) -> None:
        repositorio = Repositorio()
        ficha = ficha_valida()
        repositorio.gravar(ficha, 0, "Rascunho", "usuario")
        ficha["unidade"] = "Primeira alteração"
        repositorio.gravar(ficha, 1, "Rascunho", "usuario")
        ficha["unidade"] = "Segunda alteração"
        with self.assertRaises(Conflito):
            repositorio.gravar(ficha, 1, "Rascunho", "outro")

    def test_inclusao_simultanea_na_mesma_instancia(self) -> None:
        repositorio = Repositorio()

        def salvar(indice: int) -> str:
            ficha = ficha_valida()
            ficha["unidade"] = f"UC {indice}"
            try:
                repositorio.gravar(ficha, 0, "Rascunho", str(indice))
                return "salvo"
            except Conflito:
                return "conflito"

        with ThreadPoolExecutor(max_workers=3) as executor:
            resultados = list(executor.map(salvar, range(3)))
        self.assertEqual(resultados.count("salvo"), 1)
        self.assertEqual(len(repositorio.listar()), 1)

    def test_duplicidade_preexistente(self) -> None:
        repositorio = Repositorio()
        ficha = ficha_valida()
        salvo = repositorio.gravar(ficha, 0, "Rascunho", "usuario")
        repositorio.registros.append(deepcopy(salvo))
        with self.assertRaises(ValueError):
            repositorio.consultar(ficha["processo"])

    def test_exclusao_remove_ficha_e_preserva_auditoria(self) -> None:
        repositorio = Repositorio()
        ficha = ficha_valida()
        salvo = repositorio.gravar(ficha, 0, "Rascunho", "usuario")

        evento = repositorio.excluir(
            ficha["processo"], salvo["versao"], "usuario"
        )

        self.assertIsNone(repositorio.consultar(ficha["processo"]))
        self.assertEqual(evento["status"], "Excluída")
        self.assertEqual(repositorio.historico[-1]["status"], "Excluída")

    def test_exclusao_com_versao_antiga_e_bloqueada(self) -> None:
        repositorio = Repositorio()
        ficha = ficha_valida()
        repositorio.gravar(ficha, 0, "Rascunho", "usuario")
        ficha["unidade"] = "Unidade atualizada"
        repositorio.gravar(ficha, 1, "Rascunho", "usuario")

        with self.assertRaises(Conflito):
            repositorio.excluir(ficha["processo"], 1, "outro usuario")


if __name__ == "__main__":
    unittest.main()
