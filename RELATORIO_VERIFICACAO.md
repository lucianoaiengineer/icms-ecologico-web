# Relatório de verificação — ICMS Ecológico

**Revisão preparada:** 10/11/2026  
**Referência de origem:** branch `main` do repositório `lucianoaiengineer/icms-ecologico-web`, conferida nesta data.  
**Objetivo desta revisão:** simplificar os modos de armazenamento, retirar o adaptador descontinuado e revisar a documentação pública.

## Alterações conferidas

- O ponto de entrada `app.py` seleciona somente `demonstracao` ou `banco`.
- `icms/repositorio.py` conserva apenas o repositório de memória, seu histórico e o backup da demonstração.
- `icms/repositorio_sql.py` permanece responsável pelas transações SQL e edições recuperáveis.
- `requirements.txt` contém somente as dependências utilizadas pelos modos disponíveis.
- O teste de interface com acesso não configurado agora cobre o modo `banco`.
- `README.md`, `CONFIGURACAO_ACESSO_E_RESULTADOS.md`, `GUIA_PERSISTENCIA.md` e `PADROES_E_PUBLICACAO.md` foram revisados para o funcionamento atual.
- `assets/estilos.css`, os relatórios de 50 colunas e as regras de cálculo foram preservados.

## Resultados locais

| Verificação | Resultado |
| --- | --- |
| Regras e repositório temporário | **26 testes aprovados** |
| Persistência SQL | **6 testes aprovados** |
| Relatório e CSV | **12 testes aprovados** |
| Estrutura e modos permitidos | **5 testes aprovados** |
| Compilação estática dos módulos Python | **Aprovada** |

**Total efetivamente executado nesta revisão: 49 testes, sem falhas.**

## O que ainda não foi comprovado

- Os testes de interface Streamlit não foram executados neste ambiente, pois o pacote Streamlit não está instalado.
- A autenticação com o provedor institucional e a conexão a PostgreSQL real não foram verificadas.
- Não foram realizados testes visuais de navegador, implantação na nuvem ou restauração institucional de backup.
- Ruff e verificação completa de tipagem não foram executados nesta revisão.

Os testes automatizados realizados **não equivalem à homologação de produção**.

## Publicação

Os arquivos deste pacote precisam ser publicados nas pastas correspondentes. Isso inclui `assets/estilos.css`, os módulos `icms/` e o `requirements.txt` atualizado. Não substitua apenas `app.py`.

As atualizações descritas neste relatório foram preparadas localmente; **não foram aplicadas automaticamente ao GitHub ou à aplicação hospedada**.
