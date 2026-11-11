"""Regressões visuais estruturais da ficha aprovada no ICMS Ecológico."""

from __future__ import annotations

import ast
import unittest
from pathlib import Path

from icms.regras import (
    MUNICIPAIS,
    NOMES_MUNICIPAIS,
    normalizar_nome_municipio,
    validar,
)
from tests.test_regras import ficha_valida

RAIZ = Path(__file__).resolve().parents[1]


class TesteVisualAprovado(unittest.TestCase):
    """Verifica arquivos e componentes necessários para o layout aprovado."""

    def test_banner_real_incluido_no_pacote(self) -> None:
        """O cabeçalho não pode depender de um arquivo externo ausente."""
        banner = RAIZ / "assets" / "cabecalho_aprovado.png"
        self.assertTrue(banner.is_file())
        self.assertGreater(banner.stat().st_size, 1000)

    def test_quatro_nomes_e_numeracao_interna(self) -> None:
        """Exibe apenas os quatro títulos aprovados, mantendo as chaves."""
        self.assertEqual(MUNICIPAIS, ("10", "11.1", "11.2", "11.3"))
        self.assertEqual(
            tuple(NOMES_MUNICIPAIS.values()),
            (
                "Zona de Amortecimento",
                "RH ou Recurso Material",
                "Empréstimo de Sede",
                "Recursos Financeiro",
            ),
        )

    def test_codigo_da_ficha_tem_estrutura_de_paineis(self) -> None:
        """A imagem é só o cabeçalho; os demais campos são reais e editáveis."""
        app = (RAIZ / "app.py").read_text(encoding="utf-8")
        ast.parse(app)
        self.assertIn('key="parametros_gerais_cartao"', app)
        self.assertIn('f"linha_parametro_', app)
        self.assertIn('f"bloco_municipal_', app)
        self.assertIn("with st.expander(", app)
        self.assertIn('"Adicionar registro"', app)
        self.assertIn('"Remover"', app)
        self.assertNotIn("TOTAL DOS PARÂMETROS", app)
        self.assertIn("st.text_area(", app)
        self.assertIn("st.number_input(", app)
        self.assertIn("on_change=padronizar_municipio_digitado", app)

    def test_estilos_nao_alteram_campos_fora_das_secoes(self) -> None:
        """Os campos compactos não devem afetar as demais telas."""
        css = (RAIZ / "assets" / "estilos.css").read_text(encoding="utf-8")
        self.assertIn('st-key-linha_parametro_', css)
        self.assertIn('st-key-linha_municipal_', css)
        self.assertIn('st-key-bloco_municipal_', css)
        self.assertIn('st-key-parametros_gerais_cartao', css)

    def test_normalizacao_de_municipios(self) -> None:
        """Converte letras e espaços sem remover acentos."""
        self.assertEqual(normalizar_nome_municipio("  JUATUBA  "), "juatuba")
        self.assertEqual(
            normalizar_nome_municipio("  SÃO   JOSÉ\tDA  LAPA "),
            "são josé da lapa",
        )

    def test_duplicidade_por_espacos_e_maiuculas_na_mesma_ficha(self) -> None:
        """Não se deve cadastrar duas variantes do nome na mesma ficha."""
        ficha = ficha_valida()
        outro = dict(ficha["municipios"][0])
        outro["nome"] = " município   demonstrativo  "
        ficha["municipios"].append(outro)
        self.assertTrue(any("repetido" in e for e in validar(ficha)))


if __name__ == "__main__":
    unittest.main()
