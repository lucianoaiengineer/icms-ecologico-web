# ICMS Ecológico — Padrões e publicação segura

## Problema corrigido

Na `main` conferida em 10/11/2026, commit `b92ad132`, `app.py` importava
`icms.repositorio_sql`, mas o módulo não estava versionado. O `requirements.txt`
também não declarava SQLAlchemy e psycopg. Isso causou `ModuleNotFoundError`
no Streamlit Cloud. Esta revisão disponibiliza o módulo e suas dependências,
e também adia a importação SQL até que o modo `banco` seja selecionado.

**Não substitua apenas `app.py`.** A aplicação possui vários módulos relacionados;
publicar apenas parte deles pode impedir a inicialização ou alterar cálculos.

## Organização do código

- `app.py`: interface Streamlit e orquestração das operações.
- `assets/estilos.css`: visual, responsividade e atalhos de início/fim.
- `icms/regras.py`: normalização do SEI, validações e FQ.
- `icms/repositorio.py`: memória da demonstração, histórico e adaptador Sheets não operacional.
- `icms/repositorio_sql.py`: transações e cópias recuperáveis no banco.
- `icms/relatorios.py`: composição do relatório, tabela HTML, CSV e destaques.
- `icms/edicoes.py`: identificador de edições recuperáveis, sem dependência SQL.
- `tests/`: testes separados para regra, interface, banco, relatório e estrutura.

## Convenções aplicadas

- **PEP 8:** largura-alvo de 88 caracteres definida em `pyproject.toml`, imports organizados e nomes em `snake_case` para funções e variáveis.
- **Docstrings:** módulos, classes e funções documentados em português, descrevendo responsabilidade e principais invariantes.
- **Tipagem:** anotações de parâmetros e retornos nas funções, utilizando `dict[str, Any]`, `list[...]`, tipos opcionais e interfaces do domínio onde apropriado.
- **Separação de responsabilidades:** cálculos e dados no pacote `icms`, visual em CSS e ponto de entrada no Streamlit.
- **Segurança:** segredos fora do GitHub e HTML dos dados escapado na tabela; exclusão e gravação permanecem vinculadas a permissões e versões.
- **Importação opcional de SQL:** a demonstração não depende da existência de um driver de PostgreSQL para carregar a interface.

A conformidade integral de lint e análise estática deverá ser confirmada com Ruff e
ferramentas de tipagem no ambiente de desenvolvimento; **não foi declarada uma
aprovação de Ruff ou mypy neste pacote**, pois essas ferramentas não estavam
instaladas na análise. As verificações locais confirmaram sintaxe, docstrings,
anotações de retorno e limites de linha do código incluído.

## Atalhos laterais

O formulário é centralizado com largura máxima de **980 px**. Em telas largas,
os atalhos são posicionados **14 px depois da sua borda direita**. Por exemplo,
em uma janela de 1920 px o formulário ocupa aproximadamente x=470 a x=1450,
e os atalhos começam em x=1464. Em telas de até 1100 px, a regra responsiva
aproxima-os da borda direita disponível. O comportamento deve ser confirmado
visualmente no navegador usado pela instituição.

## Arquivos a publicar juntos

Os caminhos abaixo são relativos à raiz do repositório:

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
tests/__init__.py
tests/test_regras.py
tests/test_interface.py
tests/test_persistencia_sql.py
tests/test_relatorios.py
tests/test_estrutura.py
README.md
GUIA_PERSISTENCIA.md
PADROES_E_PUBLICACAO.md
```

O repositório possui também `CONFIGURACAO_ACESSO_E_RESULTADOS.md`: **preserve esse
arquivo**. Nenhum arquivo de credenciais deve ser publicado.

## Validação antes de implantar

1. Conferir os caminhos acima em uma branch de atualização ou PR.
2. Instalar o `requirements.txt` completo e executar `python -m unittest discover -s tests -v` com Streamlit disponível.
3. Verificar login/demo e formulários, incluindo posição dos atalhos no monitor widescreen.
4. Excluir uma ficha de teste e confirmar sua ausência imediata em Resultados e no CSV.
5. Se o modo SQL for adotado, usar primeiro uma base isolada de homologação, verificar controle de acesso, concorrência e recuperação; não utilizar SQLite efêmero em nuvem como base oficial.
6. Só então publicar uma versão identificada e registrar o resultado da homologação.

**Estado da conferência local:** 47 testes aprovados (26 de regras, 6 SQL,
12 de relatório, 3 estruturais). A execução dos 18 testes de interface, a
homologação no navegador e a conexão com PostgreSQL real ainda estão pendentes.
