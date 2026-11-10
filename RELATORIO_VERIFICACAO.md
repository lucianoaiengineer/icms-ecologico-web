# ICMS Ecológico — Resultado da conferência local

**Data da revisão:** 10/11/2026.
**Base GitHub consultada:** branch `main`, commit `b92ad132a59c29b679347bfa09a3e77b0df45ade`.
**Ambiente de testes deste pacote:** Python 3.13.5 com SQLAlchemy e pandas instalados.

## Verificações executadas

| Escopo | Resultado |
| --- | --- |
| `tests/test_regras.py` | 26 testes aprovados |
| `tests/test_persistencia_sql.py` | 6 testes aprovados |
| `tests/test_relatorios.py` | 12 testes aprovados |
| `tests/test_estrutura.py` | 3 testes aprovados |
| `compileall` de código e testes | Aprovado |
| Análise por AST das 13 unidades Python | Todas as funções possuem docstring e anotação de retorno |
| Comprimento das linhas Python | Nenhuma linha acima de 88 caracteres |

**Total de testes executados: 47 (47 aprovados, zero falhas).**

## Não executado ou não comprovado

- **18 testes de interface** (`tests/test_interface.py`): não executados; o pacote Streamlit não está instalado neste ambiente e o índice externo de pacotes não está acessível.
- **Ruff e mypy:** não executados; ferramentas indisponíveis. As verificações feitas não substituem lint e checagem de tipos completos.
- **Teste visual:** posição dos atalhos em monitor widescreen, navegação por teclado e responsividade devem ser conferidas no navegador após a publicação.
- **Banco PostgreSQL real / autenticação OIDC:** não configurados ou testados nesta execução.
- **Google Sheets:** permanece fora de operação, como integração eventual futura.

## Publicação necessária

O `ModuleNotFoundError` informado ocorreu porque `app.py` foi publicado sem `icms/repositorio_sql.py`. Esta revisão entrega o módulo, as dependências e o CSS/relatórios separados. **A correção só terá efeito no site depois que todos os arquivos novos e modificados forem colocados nas pastas corretas da branch usada na publicação.** Não foi feita alteração no GitHub pelo assistente.

## Atualização do relatório (10/11/2026)

O relatório e o CSV passaram de 35 para **50 colunas**. Agora incluem os 14 pontos validados gerais (`PARÂM 1.1` até `PARÂM 9`), o somatório municipal `PARÂM 10` e os três fatores `11.1`–`11.3`, além de identificação, 13 municípios e 13 notas. A fórmula do FQ não foi alterada. Os testes adicionais verificaram a ordem das colunas, a origem dos pontos validados, os totais municipais e os destaques de alterações.

**Nota:** os três parâmetros 11.1–11.3 mantêm o mapeamento padrão configurado no código. A conferência com a planilha institucional (E44/E60) permanece pendente.
