# Relatório de verificação — Ficha com visual aprovado

**Data:** 11/11/2026  
**Origem:** cópia da refatoração municipal baseada na `main` de `lucianoaiengineer/icms-ecologico-web`, verificada em 11/11/2026. Atualização visual isolada do código existente.  
**Situação:** pacote local para revisão e publicação manual. O GitHub não foi modificado.

## Alterações

- Faixa de cabeçalho ilustrada incorporada a partir da imagem de referência aprovada pelo usuário, com arquivo `assets/cabecalho_aprovado.png`.
- Cartão compacto de parâmetros gerais, quatro colunas, campos numéricos nativos e justificativas de menor altura.
- Quatro painéis municipais inicialmente abertos, em tons suaves de verde, com as denominações exatas e nomes reutilizados.
- Ação **Remover** integrada às linhas da Zona de Amortecimento e **Adicionar registro** após os municípios.
- Texto azul informativo sob **Parâmetros por municípios** e aviso de normalização dos nomes.
- Normalização dos nomes municipais digitados: minúsculas, sem espaços externos e um único espaço entre palavras; a identificação histórica não é substituída automaticamente apenas para exibição.

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

Foram executados **62 testes automatizados**, todos aprovados, cobrindo validações, FQ, atualização, histórico, exclusão, backup CSV, persistência SQL em SQLite de teste, relatórios dinâmicos e adaptação de fichas antigas. Os testes de interface baseados em `streamlit.testing` não foram executados neste ambiente, pois o pacote Streamlit não está instalado; sua execução é obrigatória antes da publicação.

Não foram testados em ambiente real: renderização pixel a pixel do layout aprovado e interações no Streamlit no navegador, PostgreSQL remoto, serviços de autenticação, publicação no GitHub e recuperação de backup institucional.

## Publicação

Substituir **todos** os arquivos alterados em suas pastas originais. Não publicar somente `app.py`: `icms/regras.py`, `icms/relatorios.py`, documentação e testes precisam corresponder à nova versão.

Efetue uma cópia das fichas atuais antes da publicação e verifique a abertura de fichas antigas após a atualização.

**Atenção:** repositórios de demonstração são isolados por sessão. A exclusividade global de município entre fichas distintas ainda precisa de implementação/homologação específica; os dados sintéticos anteriores repetem nomes entre processos.
