# Padrões de desenvolvimento e publicação

## Organização do projeto

O `app.py` coordena a interface Streamlit. Os estilos ficam em `assets/estilos.css`; regras, persistência e relatórios ficam em módulos próprios dentro de `icms/`.

| Arquivo ou pasta | Responsabilidade |
| --- | --- |
| `app.py` | Interface, navegação e fluxos de preenchimento. |
| `assets/estilos.css` | Layout, responsividade e atalhos laterais. |
| `icms/regras.py` | Validação e Fator de Qualidade. |
| `icms/repositorio.py` | Repositório temporário e histórico da demonstração. |
| `icms/repositorio_sql.py` | Transações SQL e edições recuperáveis. |
| `icms/relatorios.py` | Resultados, CSV e destaques. |
| `icms/edicoes.py` | Identificação das cópias provisórias. |
| `tests/` | Verificação das regras, relatórios, persistência, estrutura e interface. |

## Convenções adotadas

- **PEP 8:** nomes expressivos, imports organizados e largura-alvo de 88 caracteres conforme `pyproject.toml`.
- **Docstrings:** funções, classes e módulos documentados.
- **Tipagem:** anotações nos parâmetros e retornos, preservando a legibilidade.
- **Separação de responsabilidades:** regras de negócio independentes da camada visual.
- **Segurança:** credenciais fora do GitHub; autenticação e autorização para o modo de banco persistente.

Os padrões devem ser verificados por testes e ferramentas de análise estática; documentá-los não equivale a comprovar conformidade total.

## Publicação completa

Para evitar erros de importação ou arquivos ausentes, publique **todos os caminhos do pacote** na estrutura apresentada. Não substitua apenas o `app.py`.

```text
app.py
assets/estilos.css
icms/__init__.py
icms/edicoes.py
icms/regras.py
icms/relatorios.py
icms/repositorio.py
icms/repositorio_sql.py
requirements.txt
.gitignore
.streamlit/config.toml
pyproject.toml
tests/
README.md
CONFIGURACAO_ACESSO_E_RESULTADOS.md
GUIA_PERSISTENCIA.md
PADROES_E_PUBLICACAO.md
RELATORIO_VERIFICACAO.md
```

**Revisão da documentação antiga:** retire do repositório os guias históricos `LEIA-ME_AJUSTE_PARAMETROS.md` e `LEIA-ME_BACKUP_E_DADOS_SINTETICOS.md` depois de verificar que não são mais necessários. Ambos se referem a entregas anteriores; o primeiro descreve um relatório que já não corresponde às 50 colunas atuais.

Os arquivos `tests/regras.py`, `tests/repositorio.py` e `tests/repositorio_sql.py` existentes em algumas publicações devem ser avaliados antes de removê-los: a suíte oficial está nos arquivos `test_*.py`.

## Validação antes de disponibilizar

1. Conferir todos os arquivos na branch de implantação.
2. Executar `python -m unittest discover -s tests -v` com as dependências instaladas.
3. Verificar abertura, consulta, edição, exclusão e exportação com dados fictícios.
4. Homologar o acesso institucional e a persistência em banco isolado.
5. Verificar visualmente a interface em computador e celular, incluindo atalhos de início e fim.
6. Registrar versão, evidências de teste, backup e procedimento de retorno.

**Não use dados reais na demonstração nem considere a implantação homologada apenas porque o site iniciou.**
