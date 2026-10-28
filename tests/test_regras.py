"""Verificações de cálculo, rascunhos e concorrência por versão."""

import unittest
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy

from icms.regras import (
    calcular,
    formatar_fq,
    normalizar_processo,
    nova_ficha,
    preparar,
    validar,
)
from icms.repositorio import Conflito, Repositorio


def ficha_valida() -> dict:
    """Monta uma entrada sintética com soma validada conhecida de 34."""
    ficha = nova_ficha()
    ficha.update(processo="0000.00.0000001/2026-00", unidade="UC demonstrativa")
    valores = [6, 0, 0, 9, 0, 0, 0, 0, 2, 6, 2, 2, 2, 5]
    for pontos, valor in zip(ficha["parametros"].values(), valores, strict=True):
        pontos.update(gestor=valor, validado=valor)
    ficha["municipios"][0].update(
        nome="Município demonstrativo",
        **{"10": 0, "11.1": 0, "11.2": 0, "11.3": 0},
    )
    return ficha


class TesteRegras(unittest.TestCase):
    """Confere regras relevantes sem acesso a contas externas."""

    def test_fator_base(self) -> None:
        """Confere o cálculo da pontuação final do município."""
        self.assertEqual(calcular(ficha_valida())["municipios"][0]["FQ"], "0,3820")

    def test_fq_usa_quatro_casas_com_arredondamento_comercial(self) -> None:
        """Exibe quatro casas decimais e arredonda meio para cima."""
        self.assertEqual(formatar_fq(1, 3), "0,3333")
        self.assertEqual(formatar_fq(1, 6), "0,1667")

    def test_valor_de_outro_municipio_nao_altera_primeiro(self) -> None:
        """Garante que as notas municipais sejam calculadas separadamente."""
        ficha = ficha_valida()
        ficha["municipios"][1].update(
            nome="Outro município",
            **{"10": 9, "11.1": 9, "11.2": 9, "11.3": 9},
        )
        calculo = calcular(ficha)
        self.assertEqual(calculo["municipios"][0]["Soma"], 34)
        self.assertEqual(calculo["municipios"][1]["Soma"], 70)
        self.assertEqual(calculo["totais"], {"10": 9, "11.1": 9, "11.2": 9, "11.3": 9})

    def test_divisor_zero(self) -> None:
        """Impede o cálculo quando a pontuação de categoria é inválida."""
        ficha = ficha_valida()
        ficha["pontuacao_categoria"] = 0
        with self.assertRaises(ValueError):
            calcular(ficha)

    def test_limite_pontuacao(self) -> None:
        """Rejeita pontos fora do intervalo inteiro de zero a nove."""
        for valor in (-1, 10, 1.5, True):
            ficha = ficha_valida()
            ficha["parametros"]["1.1"]["validado"] = valor
            self.assertTrue(validar(ficha))

    def test_vazio_nao_equivale_a_zero(self) -> None:
        """Mantém campos ausentes distintos de pontos informados como zero."""
        ficha = ficha_valida()
        ficha["municipios"][0]["10"] = None
        self.assertFalse(validar(ficha))
        self.assertTrue(validar(ficha, concluir=True))

    def test_pontos_sem_municipio(self) -> None:
        """Rejeita valores municipais sem município associado."""
        ficha = ficha_valida()
        ficha["municipios"][5]["10"] = 6
        self.assertTrue(validar(ficha))

    def test_municipio_duplicado(self) -> None:
        """Impede que o mesmo município apareça em duas posições."""
        ficha = ficha_valida()
        ficha["municipios"][1] = deepcopy(ficha["municipios"][0])
        self.assertTrue(validar(ficha))

    def test_normalizacao_preserva_zeros(self) -> None:
        """Padroniza o SEI sem descartar zeros à esquerda."""
        self.assertEqual(
            normalizar_processo("0000000000001202600"),
            "0000.00.0000001/2026-00",
        )

    def test_data_impossivel(self) -> None:
        """Rejeita datas de análise ou recebimento inexistentes."""
        ficha = ficha_valida()
        ficha["recebimento"] = "2026-02-30"
        self.assertTrue(validar(ficha))

    def test_rascunho_e_atualizacao(self) -> None:
        """Permite gravar e atualizar uma ficha mantendo suas versões."""
        repositorio = Repositorio()
        ficha = nova_ficha()
        ficha["processo"] = "0000.00.0000001/2026-00"
        salvo = repositorio.gravar(ficha, 0, "Rascunho", "usuario")
        self.assertEqual(salvo["versao"], 1)
        ficha["unidade"] = "UC alterada"
        repositorio.gravar(ficha, 1, "Rascunho", "usuario")
        self.assertEqual(len(repositorio.listar()), 1)
        self.assertEqual(len(repositorio.historico), 2)

    def test_rotulo_de_parametro_editavel_e_persistido(self) -> None:
        """Preserva o texto personalizado do parâmetro entre gravações."""
        repositorio = Repositorio()
        ficha = ficha_valida()
        ficha["parametros"]["1.1"]["rotulo"] = "Texto do parâmetro revisado"

        salvo = repositorio.gravar(ficha, 0, "Rascunho", "usuario")

        self.assertEqual(
            salvo["ficha"]["parametros"]["1.1"]["rotulo"],
            "Texto do parâmetro revisado",
        )

    def test_rotulo_padrao_e_reposto_em_fichas_antigas(self) -> None:
        """Completa rótulos padrão ausentes em fichas preexistentes."""
        ficha = nova_ficha()
        ficha["processo"] = "0000.00.0000001/2026-00"
        del ficha["parametros"]["1.1"]["rotulo"]

        preparada = preparar(ficha)

        self.assertEqual(
            preparada["parametros"]["1.1"]["rotulo"],
            "1.1 · Aspecto - Ecossistema/mapa",
        )

    def test_reenvio_identico(self) -> None:
        """Evita criar versão nova ao reenviar o mesmo conteúdo."""
        repositorio = Repositorio()
        ficha = ficha_valida()
        repositorio.gravar(ficha, 0, "Concluída", "usuario")
        repositorio.gravar(ficha, 0, "Concluída", "usuario")
        self.assertEqual(len(repositorio.historico), 1)

    def test_historico_identifica_apenas_campos_alterados(self) -> None:
        """Registra no histórico somente os valores que foram modificados."""
        repositorio = Repositorio()
        ficha = ficha_valida()
        repositorio.gravar(ficha, 0, "Rascunho", "usuario")
        ficha["unidade"] = "Unidade alterada"
        ficha["municipios"][0]["10"] = 3
        repositorio.gravar(ficha, 1, "Rascunho", "usuario")

        alteracoes = repositorio.historico[-1]["alteracoes"]
        self.assertEqual(
            set(alteracoes),
            {"unidade", "municipios[1].10"},
        )
        self.assertEqual(alteracoes["municipios[1].10"]["depois"], 3)

    def test_listagem_expoe_alteracoes_da_versao_atual(self) -> None:
        """Permite realçar no resultado os campos da última atualização salva."""
        repositorio = Repositorio()
        ficha = ficha_valida()
        repositorio.gravar(ficha, 0, "Concluída", "usuario")
        ficha["unidade"] = "Unidade atualizada"
        ficha["municipios"][0]["10"] = 3

        repositorio.gravar(ficha, 1, "Concluída", "usuario")

        registro = repositorio.listar()[0]
        self.assertEqual(
            set(registro["alteracoes_ultima_versao"]),
            {"unidade", "municipios[1].10"},
        )

    def test_backup_csv_restaura_fichas_versoes_e_historico(self) -> None:
        """Restaura dados demonstrativos sem perder a trilha de alterações."""
        repositorio_origem = Repositorio()
        ficha = ficha_valida()
        repositorio_origem.gravar(ficha, 0, "Concluída", "usuario")
        ficha["responsavel"] = "Responsável atualizado"
        repositorio_origem.gravar(ficha, 1, "Concluída", "usuario")

        arquivo_csv = repositorio_origem.exportar_backup_csv()
        repositorio_restaurado = Repositorio()
        quantidade = repositorio_restaurado.restaurar_backup_csv(arquivo_csv)

        self.assertEqual(quantidade, 1)
        registro = repositorio_restaurado.consultar(ficha["processo"])
        self.assertIsNotNone(registro)
        self.assertEqual(registro["ficha"], ficha)
        self.assertEqual(registro["versao"], 2)
        self.assertEqual(
            registro["alteracoes_ultima_versao"],
            {
                "responsavel": {
                    "antes": "",
                    "depois": "Responsável atualizado",
                }
            },
        )
        self.assertEqual(repositorio_restaurado.restaurar_backup_csv(arquivo_csv), 0)

    def test_backup_csv_rejeita_cabecalho_incompativel_sem_gravar(self) -> None:
        """Recusa um CSV alheio ao formato e mantém o repositório intacto."""
        repositorio = Repositorio()
        with self.assertRaises(ValueError):
            repositorio.restaurar_backup_csv(b"outro;cabe\xc3\xa7alho\n1;2\n")
        self.assertEqual(repositorio.listar(), [])

    def test_edicao_concorrente(self) -> None:
        """Bloqueia gravação concorrente baseada em versão desatualizada."""
        repositorio = Repositorio()
        ficha = ficha_valida()
        repositorio.gravar(ficha, 0, "Rascunho", "usuario")
        ficha["unidade"] = "Primeira alteração"
        repositorio.gravar(ficha, 1, "Rascunho", "usuario")
        ficha["unidade"] = "Segunda alteração"
        with self.assertRaises(Conflito):
            repositorio.gravar(ficha, 1, "Rascunho", "outro")

    def test_inclusao_simultanea_na_mesma_instancia(self) -> None:
        """Aceita somente uma das inclusões concorrentes do mesmo processo."""
        repositorio = Repositorio()

        def salvar(indice: int) -> str:
            """Tenta salvar uma ficha com a mesma chave primária."""
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
        """Bloqueia atualizações quando a base já contém processo duplicado."""
        repositorio = Repositorio()
        ficha = ficha_valida()
        salvo = repositorio.gravar(ficha, 0, "Rascunho", "usuario")
        repositorio.registros.append(deepcopy(salvo))
        with self.assertRaises(ValueError):
            repositorio.consultar(ficha["processo"])

    def test_exclusao_remove_ficha_e_preserva_auditoria(self) -> None:
        """Exclui a ficha ativa sem eliminar o evento de auditoria."""
        repositorio = Repositorio()
        ficha = ficha_valida()
        salvo = repositorio.gravar(ficha, 0, "Rascunho", "usuario")

        evento = repositorio.excluir(ficha["processo"], salvo["versao"], "usuario")

        self.assertIsNone(repositorio.consultar(ficha["processo"]))
        self.assertEqual(evento["status"], "Excluída")
        self.assertEqual(repositorio.historico[-1]["status"], "Excluída")

    def test_exclusao_com_versao_antiga_e_bloqueada(self) -> None:
        """Impede exclusão quando a ficha foi alterada após sua consulta."""
        repositorio = Repositorio()
        ficha = ficha_valida()
        repositorio.gravar(ficha, 0, "Rascunho", "usuario")
        ficha["unidade"] = "Unidade atualizada"
        repositorio.gravar(ficha, 1, "Rascunho", "usuario")

        with self.assertRaises(Conflito):
            repositorio.excluir(ficha["processo"], 1, "outro usuario")


if __name__ == "__main__":
    unittest.main()
