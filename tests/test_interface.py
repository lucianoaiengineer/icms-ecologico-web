"""Testes de fluxos do formulário sem conta externa."""

import os
import unittest
from pathlib import Path

import streamlit as st
from streamlit.testing.v1 import AppTest
from test_regras import ficha_valida


class TesteInterface(unittest.TestCase):
    """Verifica inicialização e ações essenciais do Streamlit."""

    def setUp(self) -> None:
        """Isola o repositório temporário entre os testes."""
        self.modo_anterior = os.environ.get("ICMS_MODO")
        os.environ["ICMS_MODO"] = "demonstracao"
        st.cache_resource.clear()
        caminho = Path(__file__).resolve().parents[1] / "app.py"
        self.aplicacao = AppTest.from_file(str(caminho), default_timeout=30).run()

    def tearDown(self) -> None:
        """Restaura o modo configurado antes do teste."""
        if self.modo_anterior is None:
            os.environ.pop("ICMS_MODO", None)
        else:
            os.environ["ICMS_MODO"] = self.modo_anterior

    def test_modo_nao_configurado_oferece_demonstracao_isolada(self) -> None:
        """Permite avançar em demonstração sem abrir a base oficial."""
        os.environ.pop("ICMS_MODO", None)
        try:
            caminho = Path(__file__).resolve().parents[1] / "app.py"
            aplicacao = AppTest.from_file(str(caminho), default_timeout=30).run()
            self.assertFalse(aplicacao.exception)
            botao = next(
                elemento
                for elemento in aplicacao.button
                if elemento.label == "Continuar na demonstração"
            )
            botao.click().run()
            self.assertFalse(aplicacao.exception)
            self.assertTrue(
                any(
                    "Modo demonstração" in elemento.value
                    for elemento in aplicacao.markdown
                )
            )
            self.assertTrue(
                any(
                    elemento.label == "Salvar rascunho" for elemento in aplicacao.button
                )
            )
        finally:
            os.environ["ICMS_MODO"] = "demonstracao"

    def test_tela_de_acesso_nao_abre_autocadastro_sem_configuracao(self) -> None:
        """Exibe o acesso restrito e mantém o botão inativo sem OIDC."""
        os.environ["ICMS_MODO"] = "sheets"
        caminho = Path(__file__).resolve().parents[1] / "app.py"
        aplicacao = AppTest.from_file(str(caminho), default_timeout=30).run()
        self.assertFalse(aplicacao.exception)
        botao = next(
            elemento
            for elemento in aplicacao.button
            if elemento.label == "Acesso institucional ainda não configurado"
        )
        self.assertTrue(botao.disabled)
        self.assertTrue(
            any(
                "confirmação de e-mail" in elemento.value
                for elemento in aplicacao.markdown
            )
        )

    def preparar_ficha(self) -> None:
        """Carrega somente dados sintéticos na sessão de teste."""
        self.aplicacao.session_state.ficha = ficha_valida()
        self.aplicacao.session_state.geracao = 99
        self.aplicacao.run()

    def acionar(self, rotulo: str) -> None:
        """Aciona o botão por seu texto visível."""
        next(
            botao for botao in self.aplicacao.button if botao.label == rotulo
        ).click().run()

    def test_inicio(self) -> None:
        """Confere a navegação inicial e os rótulos da ficha."""
        self.assertFalse(self.aplicacao.exception)
        self.assertEqual(
            list(self.aplicacao.radio[0].options),
            ["Ficha", "Resultados"],
        )
        rotulos = [campo.label for campo in self.aplicacao.text_input]
        self.assertLess(rotulos.index("Responsável técnico"), rotulos.index("URFBio"))
        self.assertTrue(
            any(
                expansor.label == "Backup temporário das fichas (CSV)"
                for expansor in self.aplicacao.expander
            )
        )
        self.assertFalse(
            any(
                "Descartar campos não salvos" in codigo.label
                for codigo in self.aplicacao.checkbox
            )
        )

    def test_nova_ficha_tem_confirmacao_clara(self) -> None:
        """Pede confirmação antes de descartar alterações da ficha atual."""
        self.preparar_ficha()
        self.acionar("Nova ficha")
        self.assertTrue(
            any(
                "alterações não gravadas" in aviso.value
                for aviso in self.aplicacao.warning
            )
        )
        self.acionar("Descartar alterações e iniciar nova ficha")
        self.assertEqual(self.aplicacao.session_state.ficha["processo"], "")

    def test_blocos_municipais(self) -> None:
        """Confere nomes compartilhados e pontuações independentes ao salvar."""
        self.preparar_ficha()
        blocos = [
            bloco
            for bloco in self.aplicacao.expander
            if bloco.label.startswith("Parâmetro (")
        ]
        self.assertEqual(
            [bloco.label for bloco in blocos],
            [
                f"Parâmetro ({codigo}) por Municípios"
                for codigo in ("10", "11", "11.1", "11.2")
            ],
        )
        for bloco in blocos:
            self.assertEqual(len(bloco.text_input), 13)
            self.assertEqual(len(bloco.number_input), 13)
        self.aplicacao.text_input(key="99_municipio_1").set_value("Município de teste")
        chaves = ("10", "11.1", "11.2", "11.3")
        for chave, valor in zip(chaves, (1, 2, 3, 4), strict=True):
            self.aplicacao.number_input(key=f"99_municipio_1_{chave}").set_value(valor)
        self.acionar("Salvar rascunho")
        self.assertFalse(self.aplicacao.exception)
        for bloco in [
            bloco
            for bloco in self.aplicacao.expander
            if bloco.label.startswith("Parâmetro (")
        ]:
            self.assertEqual(bloco.text_input[0].value, "Município de teste")
        next(
            codigo
            for codigo in self.aplicacao.text_input
            if codigo.label == "Localizar pelo processo SEI"
        ).set_value("0000.00.0000001/2026-00")
        self.acionar("Localizar ficha")
        self.assertFalse(self.aplicacao.exception)
        self.assertTrue(
            any("rascunho" in aviso.value.lower() for aviso in self.aplicacao.success)
        )
        self.assertFalse(self.aplicacao.exception)
        self.assertEqual(self.aplicacao.session_state.modulo, "Ficha")
        municipio = self.aplicacao.session_state.ficha["municipios"][0]
        self.assertEqual(municipio["nome"], "Município de teste")
        self.assertEqual([municipio[codigo] for codigo in chaves], [1, 2, 3, 4])

    def test_quadro_final_da_ficha_apresenta_13_municipios_e_fq(self) -> None:
        """Mostra os treze municípios e a pontuação final calculada."""
        self.preparar_ficha()
        tabela = next(
            elemento.value
            for elemento in self.aplicacao.markdown
            if 'class="tabela-planilha"' in elemento.value
            and "PONTUAÇÃO FINAL FQ" in elemento.value
        )
        self.assertEqual(tabela.count("<tr>"), 14)
        self.assertIn("Município demonstrativo", tabela)
        esperado = sum(
            ponto["validado"] for ponto in ficha_valida()["parametros"].values()
        ) + sum(
            ficha_valida()["municipios"][0][codigo]
            for codigo in ("10", "11.1", "11.2", "11.3")
        )
        self.assertIn(f">{esperado}<", tabela)
        pontuacao_final = f"{esperado / 89:.2f}".replace(".", ",")
        self.assertIn(f">{pontuacao_final}<", tabela)

    def test_totais_dos_parametros_e_dos_blocos_municipais(self) -> None:
        """Exibe totais do primeiro quadro e de cada fator municipal."""
        self.preparar_ficha()
        valores_gestor = [9, 0, 0, 9, 0, 4, 6, 1, 3, 6, 2, 2, 2, 3]
        for (codigo, _), valor in zip(
            ficha_valida()["parametros"].items(), valores_gestor, strict=True
        ):
            self.aplicacao.number_input(key=f"99_{codigo}_gestor").set_value(valor)
        for codigo, valor in zip(
            ("10", "11.1", "11.2", "11.3"), (1, 2, 3, 4), strict=True
        ):
            self.aplicacao.number_input(key=f"99_municipio_1_{codigo}").set_value(valor)
        self.aplicacao.run()

        totais = {
            elemento.label: str(elemento.value) for elemento in self.aplicacao.metric
        }
        self.assertEqual(totais["Total — Pontos Gestor"], "47")
        self.assertEqual(totais["Total — Pontos Validados"], "34")
        blocos_municipais = [
            elemento
            for elemento in self.aplicacao.expander
            if elemento.label.startswith("Parâmetro (")
        ]
        for bloco, valor in zip(blocos_municipais, (1, 2, 3, 4), strict=True):
            self.assertTrue(
                any(
                    elemento.value == f"**TOTAL: {valor}**"
                    for elemento in bloco.markdown
                )
            )

    def test_revisar_propaga_nomes_para_todos_os_parametros(self) -> None:
        """Mostra os nomes do parâmetro 10 nos outros blocos após revisar."""
        self.preparar_ficha()
        self.aplicacao.text_input(key="99_municipio_1").set_value("Município de teste")
        self.acionar("Revisar preenchimento")
        blocos = [
            bloco
            for bloco in self.aplicacao.expander
            if bloco.label.startswith("Parâmetro (")
        ]
        self.assertFalse(self.aplicacao.exception)
        self.assertEqual(
            [bloco.text_input[0].value for bloco in blocos],
            ["Município de teste"] * 4,
        )

    def test_rascunho(self) -> None:
        """Salva rascunho sem incluí-lo no resultado consolidado."""
        self.preparar_ficha()
        self.acionar("Salvar rascunho")
        self.assertFalse(self.aplicacao.exception)
        self.assertTrue(
            any("salva e verificada" in aviso.value for aviso in self.aplicacao.success)
        )
        self.aplicacao.radio[0].set_value("Resultados").run()
        self.assertFalse(
            any(
                'class="tabela-planilha"' in elemento.value
                for elemento in self.aplicacao.markdown
            )
        )
        self.assertTrue(
            any(
                "Não há fichas concluídas" in aviso.value
                for aviso in self.aplicacao.info
            )
        )

    def test_concluir_e_exibir_resultado(self) -> None:
        """Cadastra uma ficha e apresenta os dados no relatório consolidado."""
        self.preparar_ficha()
        for codigo, valor in zip(
            ("10", "11.1", "11.2", "11.3"), (3, 4, 5, 6), strict=True
        ):
            self.aplicacao.number_input(key=f"99_municipio_1_{codigo}").set_value(valor)
        self.acionar("Cadastrar")
        self.assertFalse(self.aplicacao.exception)
        self.assertTrue(
            any("Concluída salva" in aviso.value for aviso in self.aplicacao.success)
        )
        self.assertFalse(self.aplicacao.exception)
        self.aplicacao.radio[0].set_value("Resultados").run()
        resultado = next(
            elemento.value
            for elemento in self.aplicacao.markdown
            if 'class="tabela-planilha"' in elemento.value and "Nota1" in elemento.value
        )
        self.assertIn("Indicador", resultado)
        self.assertIn("Último cadastro", resultado)
        self.assertIn(">0.58<", resultado)
        self.assertIn("PARÂM 10", resultado)
        self.assertIn(">3<", resultado)
        for codigo in ("11.1", "11.2", "11.3"):
            self.assertIn(f"PARÂM {codigo}", resultado)
            self.assertIn(">4<", resultado)

    def test_cadastrar_nao_exige_checkbox_de_confirmacao(self) -> None:
        """Permite concluir a ficha sem checkbox adicional de confirmação."""
        self.preparar_ficha()
        self.acionar("Cadastrar")
        self.assertFalse(self.aplicacao.exception)
        self.assertTrue(
            any("Concluída salva" in aviso.value for aviso in self.aplicacao.success)
        )

    def test_atualizar_exige_alteracao_e_gera_versao_nova(self) -> None:
        """Só habilita atualização quando há mudança e incrementa a versão."""
        self.preparar_ficha()
        self.acionar("Cadastrar")
        next(
            elemento
            for elemento in self.aplicacao.text_input
            if elemento.label == "Localizar pelo processo SEI"
        ).set_value("0000.00.0000001/2026-00")
        self.acionar("Localizar ficha")
        atualizar = next(
            botao for botao in self.aplicacao.button if botao.label == "Atualizar ficha"
        )
        self.assertTrue(atualizar.disabled)

        chave_unidade = f"{self.aplicacao.session_state.geracao}_unidade"
        self.aplicacao.text_input(key=chave_unidade).set_value("Unidade atualizada")
        self.aplicacao.run()
        self.assertFalse(
            next(
                botao
                for botao in self.aplicacao.button
                if botao.label == "Atualizar ficha"
            ).disabled
        )
        self.acionar("Atualizar ficha")
        self.assertEqual(self.aplicacao.session_state.versao, 2)
        self.assertEqual(
            self.aplicacao.session_state.ficha["unidade"], "Unidade atualizada"
        )

    def test_pontos_gestor_atualizados_aparecem_e_ficam_destacados(self) -> None:
        """Publica a nova nota do gestor e destaca seu valor no resultado."""
        self.preparar_ficha()
        chave = f"{self.aplicacao.session_state.geracao}_1.1_gestor"
        self.aplicacao.number_input(key=chave).set_value(9)
        self.aplicacao.run()
        self.acionar("Cadastrar")

        next(
            elemento
            for elemento in self.aplicacao.text_input
            if elemento.label == "Localizar pelo processo SEI"
        ).set_value("0000.00.0000001/2026-00")
        self.acionar("Localizar ficha")
        chave = f"{self.aplicacao.session_state.geracao}_1.1_gestor"
        self.aplicacao.number_input(key=chave).set_value(8)
        self.aplicacao.run()
        self.acionar("Atualizar ficha")
        self.assertEqual(
            self.aplicacao.session_state.ficha["parametros"]["1.1"]["gestor"], 8
        )

        self.aplicacao.radio[0].set_value("Resultados").run()
        resultado = next(
            elemento.value
            for elemento in self.aplicacao.markdown
            if 'class="tabela-planilha"' in elemento.value
            and "Pontos Gestor 1.1" in elemento.value
        )
        self.assertIn(">8<", resultado)
        self.assertIn('<td class="celula-alterada">8</td>', resultado)

    def test_consultar_processo_nao_exige_confirmacao_para_consultar(self) -> None:
        """Abre formulário novo quando o processo consultado não existe."""
        campo = next(
            elemento
            for elemento in self.aplicacao.text_input
            if elemento.label == "Localizar pelo processo SEI"
        )
        campo.set_value("0000.00.0000099/2026-00")
        self.acionar("Localizar ficha")
        self.assertFalse(self.aplicacao.exception)
        self.assertTrue(
            any(
                "Processo não localizado" in aviso.value
                for aviso in self.aplicacao.success
            )
        )
        self.assertEqual(self.aplicacao.session_state.modulo, "Ficha")
        self.assertEqual(
            self.aplicacao.session_state.ficha["processo"],
            "0000.00.0000099/2026-00",
        )

    def test_consulta_protege_alteracoes_nao_gravadas(self) -> None:
        """Protege alterações locais antes de abrir outra ficha."""
        self.preparar_ficha()
        self.acionar("Salvar rascunho")
        self.aplicacao.text_input(key="99_unidade").set_value(
            "Alteração ainda não salva"
        )
        self.aplicacao.run()
        next(
            elemento
            for elemento in self.aplicacao.text_input
            if elemento.label == "Localizar pelo processo SEI"
        ).set_value("0000.00.0000001/2026-00")
        self.acionar("Localizar ficha")

        self.assertEqual(self.aplicacao.session_state.modulo, "Ficha")
        self.assertTrue(
            any(
                "alterações ainda não gravadas" in aviso.value
                for aviso in self.aplicacao.warning
            )
        )
        self.acionar("Descartar alterações e abrir ficha localizada")
        self.assertEqual(self.aplicacao.session_state.modulo, "Ficha")
        self.assertEqual(
            self.aplicacao.session_state.ficha["unidade"], "UC demonstrativa"
        )

    def test_excluir_ficha_carregada(self) -> None:
        """Confirma a exclusão da ficha carregada no módulo de cadastro."""
        self.preparar_ficha()
        self.acionar("Salvar rascunho")
        next(
            elemento
            for elemento in self.aplicacao.text_input
            if elemento.label == "Localizar pelo processo SEI"
        ).set_value("0000.00.0000001/2026-00")
        self.acionar("Localizar ficha")
        self.acionar("Excluir ficha")
        self.assertFalse(self.aplicacao.exception)
        self.acionar("Confirmar exclusão")
        self.assertFalse(self.aplicacao.exception)
        self.assertEqual(self.aplicacao.session_state.modulo, "Ficha")


if __name__ == "__main__":
    unittest.main()
