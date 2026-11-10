"""Verificações estáticas para evitar publicações incompletas e regressões visuais."""

from __future__ import annotations

import ast
import unittest
from pathlib import Path


RAIZ = Path(__file__).resolve().parents[1]


class TesteEstrutura(unittest.TestCase):
    """Confere referências obrigatórias sem executar o servidor Streamlit."""

    def test_modulo_sql_nao_e_importado_na_inicializacao(self) -> None:
        """A demonstração não deve depender de conexão SQL para abrir."""
        codigo = ast.parse((RAIZ / "app.py").read_text(encoding="utf-8"))
        imports_globais = [
            node.module
            for node in codigo.body
            if isinstance(node, ast.ImportFrom)
        ]
        self.assertNotIn("icms.repositorio_sql", imports_globais)
        self.assertTrue((RAIZ / "icms" / "repositorio_sql.py").is_file())
        self.assertTrue((RAIZ / "icms" / "relatorios.py").is_file())

    def test_atalhos_referenciados_ao_formulario(self) -> None:
        """A fórmula não usa a borda da janela como referência em widescreen."""
        css = (RAIZ / "assets" / "estilos.css").read_text(encoding="utf-8")
        self.assertIn("--icms-largura-formulario: 980px", css)
        self.assertIn("--icms-metade-formulario: 490px", css)
        self.assertIn("calc(50vw - var(--icms-metade-formulario)", css)
        self.assertIn("--icms-atalho-distancia: 14px", css)
        self.assertIn("@media (max-width: 1100px)", css)

    def test_aviso_navegador_habilita_javascript(self) -> None:
        """O script estático de saída deve ter execução habilitada no Streamlit."""
        codigo = (RAIZ / "app.py").read_text(encoding="utf-8")
        self.assertIn("unsafe_allow_javascript=True", codigo)
        self.assertIn("beforeunload", codigo)


if __name__ == "__main__":
    unittest.main()
