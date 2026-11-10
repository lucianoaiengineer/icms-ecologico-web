# ICMS Ecológico — Gestão de Fichas e Fator de Qualidade

Aplicação web em **Streamlit/Python** para cadastrar, consultar, revisar, concluir e atualizar fichas identificadas pelo número de processo SEI, calcular o **Fator de Qualidade (FQ)** por município e consultar os resultados consolidados.

> **Estado do projeto:** versão de desenvolvimento, com verificações automatizadas locais documentadas. **Não há homologação institucional nem confirmação, neste registro, de que a aplicação hospedada execute exatamente o código da branch `main`.** A existência de uma URL pública não representa autorização para uso oficial ou para inserção de dados institucionais. **A integração com Google Sheets não está em funcionamento; continua sendo uma possibilidade futura. Este pacote acrescenta um modo SQL configurável, ainda não ativado na aplicação publicada.**
>
> **Repositório:** [lucianoaiengineer/icms-ecologico-web](https://github.com/lucianoaiengineer/icms-ecologico-web) · **branch:** `main`. Estrutura conferida em **09/11/2026**, antes da substituição deste README.

## Funcionalidades

- **Consulta pelo processo SEI:** localiza fichas na base interna da aplicação; se o processo ainda não existir, abre uma ficha nova com o SEI consultado. **Não há integração automática com o sistema SEI institucional.**
- **Ciclo da ficha:** cadastro, rascunho, retomada, revisão sem gravação, conclusão, atualização e exclusão com confirmação.
- **Pontuações:** 14 parâmetros gerais (pontos do gestor, justificativa e pontos validados) e 13 posições municipais, com quatro valores por município.
- **Cálculo do FQ:** nota calculada individualmente para cada município, com quatro casas decimais.
- **Resultados:** somente fichas concluídas, filtro por processo ou unidade, indicação da ficha concluída gravada mais recentemente e destaque das alterações da última versão.
- **Exportação:** relatório CSV para consulta e, separadamente, backup/restauração de fichas no modo demonstração.
- **Modos:** a demonstração continua temporária por sessão. O novo modo `banco` oferece persistência SQL (SQLite com volume persistente ou PostgreSQL externo) após configuração de autenticação, Secrets e banco. Google Sheets permanece **não operacional**, como alternativa futura.

## Ajustes incorporados ao código

A revisão de referência foi preparada em **06/11/2026**. Os arquivos principais conferidos do pacote correspondem aos presentes na `main` em 09/11/2026.

1. **Integridade municipal:** cada posição com nome de município aceita valores inteiros de **0 a 9**, inclusive zero. Sem nome (ou com espaços/`-`), nenhum valor é válido, nem mesmo zero. Valores indevidos impedem salvar rascunho ou ficha concluída; apagar um nome não elimina silenciosamente os pontos já registrados.
2. **Blocos municipais:** os quatro blocos visuais **10, 11, 11.1 e 11.2** começam recolhidos. Os nomes são digitados no primeiro bloco e repetidos nos outros. As chaves internas de armazenamento permanecem **`10`, `11.1`, `11.2` e `11.3`** para preservar compatibilidade com fichas gravadas.
3. **Abertura e edição:** a consulta pelo SEI unifica abertura e criação de fichas. O botão redundante **Nova ficha** foi retirado; a confirmação para descartar alterações ainda não salvas permanece. Foi removido o aviso verde de “ficha carregada”, sem retirar confirmações de gravação.
4. **Formulário:** o calendário de **Data de recebimento** foi aproximado do campo e as ações **Revisar preenchimento** e **Atualizar ficha** foram agrupadas à direita, com adaptação prevista para telas estreitas.
5. **Relatório e CSV:** foram retiradas as colunas de **Pontos Gestor**, **Pontos Validados**, seus totais e **PARÂM 10**. Permanecem identificação, **PARÂM 11.1**, **11.2**, **11.3**, 13 municípios e 13 notas. Os pontos removidos do relatório **continuam na ficha, na base e no cálculo**.
6. **Histórico visual:** o destaque verde identifica os campos relacionados à **última atualização salva daquela ficha**; persiste ao reabrir a página e é substituído quando uma nova atualização é salva. Regravar conteúdo e estado idênticos não cria nova versão.
7. **Demonstração e segurança de gravação:** o modo de demonstração oferece backup CSV completo; o repositório mantém versão, autor, diferenças e histórico de operações, com verificação da gravação.

## Estrutura real do repositório

A tabela descreve a **estrutura prevista após aplicar este pacote de atualização**. Ela não afirma que as novas alterações já foram publicadas no GitHub. Os itens previamente existentes foram conferidos na `main` em 09/11/2026.

| Item | Por quê |
| --- | --- |
| [`app.py`](app.py) | Entrada da aplicação Streamlit; interface, navegação, controle de acesso, ficha, resultados e CSV. |
| [`icms/`](icms/) | Pacote Python com `__init__.py`, `regras.py` (validação e FQ) e `repositorio.py` (repositório temporário e adaptador Google Sheets não operacional) e `repositorio_sql.py` (persistência SQL transacional e recuperação automática). |
| [`requirements.txt`](requirements.txt) | Dependências necessárias para executar a aplicação e componentes previstos para uma possível integração futura com autenticação e Google Sheets. |
| [`.streamlit/`](.streamlit/) | Contém `config.toml`, responsável pela configuração visual do tema da aplicação. |
| [`.gitignore`](.gitignore) | Exclui segredos locais, ambiente virtual, caches e arquivos de banco SQLite do versionamento. |
| [`tests/`](tests/) | Contém `test_regras.py`, `test_interface.py` e `test_persistencia_sql.py` para regras, interface e persistência SQL. |
| [`pyproject.toml`](pyproject.toml) | Configuração do Ruff para qualidade e padronização do código; não é requisito de execução da aplicação. |
| [`CONFIGURACAO_ACESSO_E_RESULTADOS.md`](CONFIGURACAO_ACESSO_E_RESULTADOS.md) | Guia técnico com orientações preparatórias sobre OIDC, perfis, Secrets, conta de serviço e consultas. **Não comprova que Google Sheets esteja em funcionamento.** |
| [`README.md`](README.md) | Documentação principal do projeto, com comportamento, instalação, estrutura real e limites de homologação atualizados. |

**Arquivos Python do pacote:** `app.py`, `icms/__init__.py`, `icms/regras.py`, `icms/repositorio.py`, `icms/repositorio_sql.py`, `tests/__init__.py`, `tests/test_regras.py`, `tests/test_interface.py` e `tests/test_persistencia_sql.py`. Os novos arquivos serão versionados somente após publicação autorizada.

**Limpeza já realizada:** os dois arquivos antigos `LEIA-ME...` não constam mais da `main`. Também **não constam** notebooks do Google Colab, `preparar_base.py`, `segredos.exemplo.toml`, `LEIA_PRIMEIRO.md` ou `VALIDACAO.md` citados no README anterior. Portanto, este guia não depende desses arquivos.

## Regras de negócio principais

### Identificação e preenchimento

- O processo SEI é normalizado para o formato `0000.00.0000000/0000-00` (19 algarismos). A aplicação verifica **formato e unicidade interna**, mas não valida dígitos verificadores contra o SEI externo.
- A pontuação padrão da categoria é **89**, editável no intervalo inteiro de **1 a 999**.
- A **Data de análise** usa `mm/aaaa`; a data de recebimento é mantida internamente em formato ISO.
- Rascunhos admitem campos ainda não preenchidos, mas não valores inválidos.
- Para **concluir**, são exigidos a unidade de conservação, os pontos do gestor e os pontos validados dos 14 parâmetros gerais e pelo menos um município identificado com os quatro valores preenchidos.
- Nomes de municípios duplicados são rejeitados sem distinguir maiúsculas de minúsculas. Não há cadastro oficial de municípios incluído no repositório.
- O retorno de uma ficha **Concluída** para **Rascunho** não é permitido nesta versão.

### Cálculo do Fator de Qualidade

Para cada município identificado:

```text
Soma do município = soma dos 14 pontos validados gerais
                  + soma dos 4 valores municipais daquela posição

FQ do município   = Soma do município / Pontuação da categoria
```

O FQ utiliza **quatro casas decimais** e arredondamento comercial (`Decimal` com `ROUND_HALF_UP`). Os **pontos do gestor não entram na soma do FQ**, e a pontuação de outro município não altera a nota individual.

### Resultados e mapeamento pendente

O relatório consolidado e o arquivo `resultado_fq.csv` incluem **35 colunas**: seis de identificação, três fatores, 13 municípios e 13 notas. O CSV utiliza ponto e vírgula (`;`), vírgula decimal e quatro casas nas notas; a data exportada atualmente usa **`mm/dd/aaaa`**. A coluna visual **Indicador** e as cores não são exportadas.

**Atenção — regra ainda sujeita a aceite da área de negócio:** por padrão, os três fatores visíveis (`PARÂM 11.1`, `11.2` e `11.3`) recebem o total da **chave interna `11.1`**. O parâmetro interno `10` permanece na ficha e no cálculo, mas não aparece no relatório. O mapa pode ser ajustado por `totais_resultado` nos Secrets. A correspondência com as referências **E44 e E60** e com as planilhas institucionais precisa ser validada antes do uso oficial; não confundir rótulos do formulário com chaves internas.

## Execução local em modo demonstração

A referência de testes documentada utiliza **Python 3.12.14** e **Streamlit 1.66.0**. Recomenda-se uma instalação compatível do Python 3.12 e o uso das dependências declaradas.

1. Obtenha o conteúdo do repositório e abra um terminal em sua pasta raiz.
2. Instale as dependências:

   ```bash
   python -m pip install -r requirements.txt
   ```

3. Execute a aplicação:

   ```bash
   python -m streamlit run app.py
   ```

4. Se não houver configuração institucional, use a opção **Continuar na demonstração** na tela inicial. Utilize **somente dados fictícios**.

O modo demonstração mantém os registros na sessão temporária do navegador. Para preservar os dados demonstrativos, use **Baixar backup completo das fichas** (`backup_fichas_icms.csv`) e, quando necessário, a opção de restaurá-lo. Esse backup inclui fichas, estados, versões e histórico. **`resultado_fq.csv` não é backup completo** e não reconstitui a base.

## Proteção das edições e persistência SQL (implementação preparada)

Este pacote acrescenta mecanismos para reduzir perdas de preenchimento, **sem alterar a ficha oficial antes de uma ação explícita de gravação**:

- **Saída da página:** um aviso nativo de navegador tenta alertar quando há campos alterados; por restrições do navegador, não é garantido em celular, interrupções de energia ou encerramento forçado.
- **Troca de módulo:** quando há alterações, entrar em Resultados exige confirmação. Consultar outro SEI continua exigindo confirmação de descarte.
- **Cópia automática de edição:** no modo `banco`, após o campo ser transmitido ao servidor e processado pelo Streamlit, o sistema registra a edição em uma tabela separada por usuário e processo. Isso não é uma versão oficial, nem entra no relatório.
- **Recuperação:** após abrir outra sessão com a mesma conta autorizada, o usuário pode recuperar ou descartar suas cópias de edição. A recuperação é bloqueada caso a versão da ficha oficial tenha mudado ou ela tenha sido excluída.
- **Gravação oficial:** **Salvar rascunho**, **Cadastrar** ou **Atualizar ficha** usam transações SQL, versões e histórico. A exclusão remove o registro ativo dos resultados e o autosalvamento correspondente, preservando o histórico de exclusão.

**Importante:** o código não garante salvar cada tecla no momento da digitação. Alterações ainda não transmitidas ao servidor podem ser perdidas em falha abrupta. A prevenção de perdas depende de o modo `banco` estar configurado, acessível e com backups.

### Configuração do modo `banco`

No Streamlit **Settings → Secrets**, defina `modo = "banco"`, `banco_url` e os parâmetros OIDC e listas `editores` e `leitores`. Um exemplo de **formato**, sem credenciais, é:

```toml
modo = "banco"
banco_url = "postgresql+psycopg://USUARIO:SENHA@HOST:5432/NOME_DA_BASE?sslmode=require"
editores = ["EDITOR_INSTITUCIONAL_AUTORIZADO"]
leitores = []

[auth]
redirect_uri = "https://DOMINIO_DA_APLICACAO/oauth2callback"
cookie_secret = "SEGREDO_A_SER_DEFINIDO_COM_SEGURANCA"
client_id = "ID_FORNECIDO_PELO_PROVEDOR"
client_secret = "SEGREDO_FORNECIDO_PELO_PROVEDOR"
server_metadata_url = "HTTPS_DO_DOCUMENTO_OIDC"
```

Esses valores são **marcadores explicativos**, não credenciais de funcionamento. Exija e-mail verificado e autorização antes de habilitar acesso a fichas reais. O código cria as tabelas `icms_fichas`, `icms_historico` e `icms_edicoes_automaticas` no banco apontado. Utilize uma **base exclusiva de homologação** para os primeiros testes.

Para testes em servidor próprio com disco persistente, uma URL SQLite no formato `sqlite:////caminho/persistente/icms.sqlite` também é aceita, mas não atende a operação oficial sem análise de backup e segurança. **Em Streamlit Community Cloud, arquivos SQLite locais não são persistentes após reinicialização ou redistribuição. Para operação durável nessa hospedagem, configure PostgreSQL externo.**

**Estado da implementação:** os testes de repositório SQL e das regras foram executados localmente. Autenticação OIDC, PostgreSQL real, reinicialização do Streamlit Cloud, homologação visual do aviso de saída e restauração de backup operacional **ainda dependem de testes no ambiente institucional**. O modo `banco` não se ativa sozinho ao enviar arquivos ao GitHub e não migra automaticamente rascunhos da demonstração.

Consulte [`GUIA_PERSISTENCIA.md`](GUIA_PERSISTENCIA.md) para preparação, limites e critérios de aceite.

## Google Sheets — possibilidade de implementação futura (não operacional)

**O Google Sheets não está em funcionamento como base de dados do projeto atualmente.** O código inclui um adaptador `RepositorioSheets` e mecanismos previstos para autenticação, autorização e persistência, mas sua presença **não significa que a conexão esteja ativa, configurada, testada ou homologada**. Seu uso é apenas uma **possibilidade de implementação futura**, condicionada à avaliação da equipe responsável.

Caso a integração seja adotada, será necessário preparar uma planilha específica com as abas técnicas **`Fichas`** e **`Historico`**, configurar de forma segura `modo`, `planilha_id`, `auth`, `gcp_service_account`, `editores`, `leitores` e, após validação de negócio, `totais_resultado`. A solução prevista utiliza **OIDC** para identificar usuários e uma **conta de serviço** para acessar a planilha, mas essas operações ainda dependem de testes com contas e recursos autorizados.

O arquivo [`CONFIGURACAO_ACESSO_E_RESULTADOS.md`](CONFIGURACAO_ACESSO_E_RESULTADOS.md) registra orientações técnicas para essa eventual implantação; **não é evidência de disponibilidade atual do serviço**.

**Nunca publique credenciais, chaves privadas, e-mails de usuários reais ou o conteúdo de `secrets.toml` no GitHub.** Se houver implantação futura, os Secrets deverão permanecer na configuração protegida da hospedagem.

Mesmo após eventual configuração, a trava `RLock` e a verificação de versão cobrem apenas a **mesma instância Python**. Não há garantia transacional entre réplicas, outros programas ou edições diretas no Google Sheets. Qualquer implantação compartilhada exigirá revisão da concorrência, testes de gravação e recuperação e homologação institucional.

## Testes e evidências disponíveis

A versão de referência contém **26 testes de regras/repositório** e **18 testes de interface**. Este pacote acrescenta **6 testes de persistência SQL**. Foram executados **32 testes locais** (26 de regras e 6 SQL); os 18 de interface dependem de instalação do Streamlit e não foram reexecutados neste ambiente. A documentação anterior registra a aprovação dos 44 testes em **06/11/2026**, no modo demonstração e com dados sintéticos. Trata-se de **resultado histórico documentado**, não de comprovação de execução no ambiente institucional.

Para executar os testes no ambiente preparado:

```bash
python -m unittest discover -s tests -v
```

Os testes locais não comprovam autenticação no provedor real, acesso à planilha institucional, escrita concorrente por instâncias independentes, compatibilidade final com Excel nem aprovação visual e de acessibilidade. **Não houve validação de funcionamento do Google Sheets como armazenamento institucional; essa integração permanece como possibilidade futura.**

## Pendências de homologação e implantação

| Prioridade | Identificação | Pendência para aceite |
| --- | --- | --- |
| **P0** | D01 — Regra dos fatores | Conferir E44, E60 e o mapeamento de `PARÂM 11.1`, `11.2` e `11.3` contra as planilhas vigentes. |
| **P0** | D02 — Dados e acesso | Aprovar classificação de dados, hospedagem, OIDC, listas de perfis, permissões e bloqueio integral do leitor. |
| **P0** | D03 — Concorrência | Garantir um único escritor ou implantar coordenação transacional adequada; impedir edição paralela externa da planilha. |
| **P0** | D04 — Registros antigos | Auditar e migrar eventuais pontos sem nome de município, inclusive zero, preservando zeros válidos. |
| **P0** | D05 — Recuperação | Definir retenção, periodicidade, responsáveis, perda tolerada e prazo de recuperação; testar restauração real do Sheets. |
| **P0** | D06 — Exclusão e histórico | Definir exclusão física/lógica, retenção, reutilização do SEI e continuidade das versões após exclusão. |
| **P1** | D07 — Interface | Homologar desktop, celular, teclado, foco, formatos e destaques; revisar o bloqueio de **Data de análise** para leitores. |
| **P0** | D08 — Publicação e suporte | Identificar versão efetivamente implantada; validar retorno de versão, suporte, monitoramento e documentação coerente. |

**Cenários que ainda exigem evidência de homologação:** CA01/CA25 (acesso e revogação), CA06 (identificação e datas), CA18 (CSV no Excel), CA19 (aceite visual dos destaques), CA21–CA22 (interface e acessibilidade), CA23 (gravação real no Sheets), CA24 (concorrência no ambiente final), CA26 (restauração), CA27 (falhas e retorno de versão) e CA28 (carga e monitoramento).

A liberação do piloto exige aceite funcional, validação técnica com credenciais e planilha **de teste**, restauração demonstrada, responsáveis definidos e autorização explícita para uso dos dados institucionais.

## Referências técnicas

- [Autenticação de usuários — Streamlit](https://docs.streamlit.io/develop/concepts/connections/authentication)
- [Requisições em lote — Google Sheets API](https://developers.google.com/workspace/sheets/api/guides/batch)
- [Dependências de aplicações — Streamlit Community Cloud](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies)

A documentação complementar de **requisitos e regras de negócio**, **fluxos e arquitetura** e **homologação e implantação** foi preparada separadamente em 06/11/2026. **Esses documentos não integram a árvore da `main` verificada** e, por isso, não são apresentados como arquivos existentes neste repositório.
