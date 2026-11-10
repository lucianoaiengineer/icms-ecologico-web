# ICMS Ecológico — proteção de edições e persistência

**Pacote de atualização:** ainda não publicado nem homologado em produção. Não modificar credenciais ou base real durante a avaliação.

## 1. O que mudou

- Um aviso de saída do navegador é solicitado quando existem edições não confirmadas. O navegador pode suprimir a mensagem; não há garantia de aviso quando a máquina desliga, o processo é encerrado ou a conexão cai.
- A passagem de **Ficha** para **Resultados** pede confirmação se houver alterações pendentes; a consulta de outro processo continua protegida.
- No modo `banco`, uma cópia automática separada dos dados oficiais é gravada após o Streamlit processar uma alteração de widget. Os autosaves são vinculados a usuário autenticado e SEI (ou `__nova__` para ficha sem SEI).
- Ao voltar com a mesma identidade verificada, o usuário pode **Recuperar edição** ou **Descartar cópia**. Se a ficha oficial mudou de versão, a recuperação é bloqueada.
- **Salvar rascunho**, **Cadastrar** e **Atualizar ficha** são as únicas ações que alteram uma ficha oficial. `Revisar preenchimento` continua sem modificar o registro oficial. A exclusão remove a ficha da tabela de resultados e todas as cópias automáticas ligadas àquele SEI.
- O modo de demonstração, seus backups CSV e o adaptador Sheets existente permanecem sem mudança de comportamento. Google Sheets não está em operação.

## 2. Armazenamento implementado

`icms/repositorio_sql.py` implementa três tabelas:

| Tabela | Finalidade |
| --- | --- |
| `icms_fichas` | Registros oficiais ativos, com SEI, versão, estado, autor e ficha em JSON. |
| `icms_historico` | Eventos de gravação e exclusão, diffs e SHA-256 do conteúdo. |
| `icms_edicoes_automaticas` | Cópias de edição ainda não confirmadas, segregadas por identidade e processo. |

As alterações oficiais usam transação de banco e atualização condicional por versão, incluindo auditoria na mesma transação. A restauração de um backup operacional depende do serviço de banco e **não** do `resultado_fq.csv`. A exclusão da ficha não exclui os eventos de histórico.

## 3. Configuração de homologação

1. Preparar PostgreSQL externo, com conexão TLS, usuário restrito e base de teste **sem dados reais**. Para teste controlado em servidor com volume persistente, SQLite pode ser usado, mas não em Streamlit Community Cloud como armazenamento durável.
2. Configurar `modo = "banco"`, `banco_url`, `[auth]`, `editores` e `leitores` nos **Secrets da hospedagem**. Não guardar valores reais em arquivos versionados.
3. Instalar o `requirements.txt` do pacote. A aplicação criará as tabelas necessárias na base de teste configurada.
4. Testar uma ficha concluída, modificação sem atualizar, encerramento e nova sessão com mesma conta; recuperar a edição, validar, atualizar; confirmar que o relatório só mudou depois da atualização.
5. Testar exclusão, acesso entre usuários, concorrência, reversão do código, disponibilidade após reiniciar a hospedagem e restauração de backup.

**Configuração de referência (marcadores, não funcional):**

```toml
modo = "banco"
banco_url = "postgresql+psycopg://USUARIO:SENHA@HOST:5432/BASE?sslmode=require"
editores = ["EDITOR_AUTORIZADO"]
leitores = []

[auth]
redirect_uri = "https://DOMINIO/oauth2callback"
cookie_secret = "SEGREDO_A_CONFIGURAR"
client_id = "CLIENTE_OIDC"
client_secret = "SEGREDO_OIDC"
server_metadata_url = "https://PROVEDOR/.well-known/openid-configuration"
```

**SQLite em host próprio:** exemplo de `banco_url = "sqlite:////var/lib/icms/icms.sqlite"`. O diretório deve ser persistente, protegido por permissões do sistema e incluído no backup do servidor. Evite apontar para disco efêmero em ambiente de nuvem.

## 4. Limitações e riscos residuais

- **O modo banco não será ativado automaticamente** ao publicar os arquivos. Sem banco externo, autenticação institucional e Secrets, a opção pública de demonstração permanece isolada e temporária.
- O Streamlit transmite alterações de texto ao Python normalmente após confirmação/perda de foco; uma tecla que não chegou ao servidor pode não estar no autosave. A proteção `beforeunload` depende das regras do navegador e não substitui persistência.
- As cópias automáticas não possuem revisão/mesclagem de edições simultâneas em diferentes abas do **mesmo usuário e processo**. A última cópia sincronizada prevalece. A gravação **oficial**, por sua vez, tem controle de versão no SQL.
- O código cria tabelas iniciais, mas não oferece migrações de esquema, monitoramento, backup/restauração operacional, nem integra demonstrações existentes. Esses temas continuam pendentes de homologação.
- A proteção institucional dos dados exige classificação, controle de privilégios do banco, perfis OIDC, limites de retenção e aprovação pela TI.
- O novo modo **não muda o status do Google Sheets**: permanece possibilidade futura, sem integração institucional operacional.

## 5. Testes verificados e pendências

No ambiente de preparação, **47 testes de Python foram executados e aprovados**: 26 originais de regras/repositório, 6 testes SQL, 12 de relatórios e 3 verificações estáticas. Os 18 testes de interface do projeto não puderam ser reexecutados, porque o Streamlit não estava instalado na execução local e o acesso ao índice de pacotes estava indisponível. Também **não foi realizado teste contra PostgreSQL real**.

**Para execução em ambiente com dependências instaladas:**

```bash
python -m unittest discover -s tests -v
```

A homologação deve comprovar: (a) autenticação e isolamento entre usuários; (b) gravação de edição interrompida e recuperação; (c) versão oficial não alterada antes de clicar Salvar/Atualizar; (d) exclusão imediata dos resultados; (e) bloqueio de conflito; (f) persistência depois de reiniciar a hospedagem; (g) backup, restauração e recuperação de desastres; (h) aviso visual no navegador/telefone.

## 6. Arquivos para atualização

- `app.py`: formulário e aviso de saída, recuperação de edições e seleção do modo `banco`; importa o SQL apenas no modo correspondente.
- `icms/repositorio_sql.py`: novo módulo SQL.
- `icms/relatorios.py` e `icms/edicoes.py`: lógica de relatório/CSV e identificação de edições.
- `assets/estilos.css`: estilos separados e atalhos próximos ao contêiner em widescreen.
- `requirements.txt`: novas dependências SQLAlchemy e psycopg.
- `.gitignore`: bloqueia a publicação acidental de bancos locais e arquivos transacionais SQLite.
- `tests/test_persistencia_sql.py`, `tests/test_relatorios.py` e `tests/test_estrutura.py`: regressões SQL, relatório e estrutura.
- `README.md`: documentação e tabela de estrutura prevista após a atualização.

O pacote de publicação inclui também `icms/regras.py`, `icms/repositorio.py`, os testes originais, `.streamlit/config.toml` e `pyproject.toml`. Preserve `CONFIGURACAO_ACESSO_E_RESULTADOS.md`, que já existe no GitHub e não precisa ser substituído. **Não publique somente `app.py`**: novos módulos, CSS e `requirements.txt` precisam estar presentes juntos.
