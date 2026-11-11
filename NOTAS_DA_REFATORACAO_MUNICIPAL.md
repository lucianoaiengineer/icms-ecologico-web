# Refatoração da ficha — ICMS Ecológico original

**Data:** 11/11/2026  
**Origem:** `lucianoaiengineer/icms-ecologico-web`, branch `main`, commit `bdf3128d73f926eb645cedf0eae5750e47a7ab04`.  
**Situação:** arquivos preparados localmente. **Nada foi enviado ao GitHub.**

## O que foi alterado

- A seção **TOTAL DOS PARÂMETROS** e os indicadores **Total — Pontos Gestor** e **Total — Pontos Validados** foram retirados da ficha.
- O título **Parâmetros por municípios** foi preservado com a orientação curta aprovada.
- Os quatro blocos expansíveis são intitulados exclusivamente **Zona de Amortecimento**, **RH ou Recurso Material**, **Empréstimo de Sede** e **Recursos Financeiro**.
- Os códigos internos são, respectivamente, `10`, `11.1`, `11.2` e `11.3`.
- Município cadastrado no primeiro bloco é reutilizado nos demais. Adicionar/remover registro altera a lista municipal compartilhada.
- Cada bloco possui **Pontos Gestor**, **Justificativa/Observação** e **Pontos Validados** próprios para cada município.
- Os nomes não podem ser duplicados na mesma ficha. Pontuações são inteiros de 0 a 9, incluindo zero. Não são aceitos pontos sem município identificado.
- A lista de municípios não tem mais 13 linhas fixas; o preenchimento acompanha os registros realmente necessários. O limite anterior de tamanho total da ficha continua sendo aplicado na gravação.
- O FQ permanece `soma dos 14 pontos validados gerais + quatro pontos validados do município`, dividido pela pontuação da categoria e arredondado em quatro casas por `ROUND_HALF_UP`.
- **Resultados** agora têm um resumo por ficha concluída (9 colunas) e detalhamento por município cadastrado (27 colunas), com dois CSVs.

## Compatibilidade

As fichas antigas com até 13 posições e quatro pontuações simples são adaptadas ao abrir ou salvar. Cada valor antigo passa a **Pontos Validados** do bloco correspondente. **Pontos Gestor permanece vazio** porque esse valor não existia na estrutura antiga. A conversão não inventa pontuações e preserva o FQ.

O backup e os arquivos antigos devem ser preservados até concluir a conferência da conversão. O sistema mantém o modo demonstração existente e não exige instalar ou contratar PostgreSQL.

## Verificação

- **56 testes unitários/integrados aprovados** no ambiente local.
- Compilação estática Python aprovada.
- Testes visuais e de interface Streamlit **não executados**, pois Streamlit não está instalado no ambiente de revisão.
- Nenhuma atualização no GitHub foi feita automaticamente.

## Publicação

Substituir os arquivos nas mesmas pastas do repositório após conferir a cópia de segurança dos registros. Não substituir somente `app.py`: os módulos `icms/regras.py` e `icms/relatorios.py` são indispensáveis à nova estrutura. O pacote completo inclui também CSS e dependências existentes, evitando erros de ausência de arquivos.

**Atenção:** o formato do CSV de resultados mudou em relação ao antigo relatório de 50 colunas. Para importação de dados antigos, utilizar o backup completo de fichas; o CSV de resultados não é um backup.
