# Relatório de verificação — Refatoração municipal

**Data:** 11/11/2026  
**Origem:** repositório público `lucianoaiengineer/icms-ecologico-web`, branch `main`, commit `bdf3128d73f926eb645cedf0eae5750e47a7ab04`.  
**Situação:** pacote local para revisão e publicação manual. O GitHub não foi modificado.

## Alterações

- Remoção da seção **TOTAL DOS PARÂMETROS** e dos indicadores correspondentes do formulário.
- Preservação do título **Parâmetros por municípios** com explicação breve.
- Quatro blocos expansíveis: **Zona de Amortecimento**, **RH ou Recurso Material**, **Empréstimo de Sede** e **Recursos Financeiro**.
- Cada bloco registra pontos do gestor, justificativa e pontos validados, com um único cadastro de nomes de municípios.
- **Adicionar registro** e **Remover registro** no primeiro bloco, propagando a lista aos outros três.
- Substituição das 13 posições fixas por registros efetivamente cadastrados.
- Preservação da fórmula de FQ: os 14 pontos gerais validados mais os quatro pontos municipais validados, divididos pela categoria, com `ROUND_HALF_UP` a quatro casas.
- Resultados em duas visões, com exportação CSV separada: resumo por ficha (9 colunas) e resultados por município (27 colunas).
- Conversão controlada de fichas antigas de 13 posições e pontuações simples, sem inventar pontos do gestor.
- Nenhuma instalação ou implantação nova de banco de dados.

## Verificação local

Foram executados **56 testes automatizados**, todos aprovados, cobrindo validações, FQ, atualização, histórico, exclusão, backup CSV, persistência SQL em SQLite de teste, relatórios dinâmicos e adaptação de fichas antigas. Os testes de interface baseados em `streamlit.testing` não foram executados neste ambiente, pois o pacote Streamlit não está instalado; sua execução é obrigatória antes da publicação.

Não foram testados em ambiente real: Streamlit no navegador, PostgreSQL remoto, serviços de autenticação, publicação no GitHub e recuperação de backup institucional.

## Publicação

Substituir **todos** os arquivos alterados em suas pastas originais. Não publicar somente `app.py`: `icms/regras.py`, `icms/relatorios.py`, documentação e testes precisam corresponder à nova versão.

Efetue uma cópia das fichas atuais antes da publicação e verifique a abertura de fichas antigas após a atualização.
