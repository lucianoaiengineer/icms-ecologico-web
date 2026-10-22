# Configuração do acesso e da consulta de resultados

## O que foi incluído nesta versão

- Tela de acesso centralizada na página, com cartão branco dimensionado para o
  conteúdo e fundo verde muito claro. Em telas estreitas, o cartão se ajusta à
  largura disponível.
- Entrada por provedor institucional OIDC. A aplicação não cria senhas nem envia
  senhas por e-mail; a recuperação de conta é feita pelo provedor configurado.
- Acesso restrito a e-mails verificados e previamente autorizados. As três
  contas iniciais devem ser adicionadas à lista de editores depois que seus
  endereços institucionais forem definidos. O perfil editor permite incluir,
  consultar, alterar e excluir fichas.
- Quando o modo institucional ainda não foi configurado, a tela oferece entrada
  explícita em demonstração. Os registros fictícios ficam isolados na sessão
  daquele navegador, não são gravados na planilha e desaparecem ao encerrar a
  sessão. Não use dados reais nesse modo.
- Tabela de resultados com altura de consulta ampliada, rolagem dentro da grade,
  colunas de processo e unidade fixadas à esquerda e opção de tela cheia.

## Configurações ainda necessárias para uso real

O código não contém credenciais, e-mails reais ou identificador de planilha.
Esses valores devem ser incluídos em **Settings → Secrets** no Streamlit Cloud,
após a instituição definir o provedor de identidade e a planilha autorizada.

Exemplo de estrutura TOML para um único provedor OIDC. Substitua cada marcador
pelos valores fornecidos pelo administrador do provedor e do Google Sheets:

```toml
modo = "sheets"
planilha_id = "<IDENTIFICADOR_DA_PLANILHA>"
editores = [
  "<EMAIL_INSTITUCIONAL_USER1>",
  "<EMAIL_INSTITUCIONAL_USER2>",
  "<EMAIL_INSTITUCIONAL_USER3>"
]
leitores = []
url_recuperacao = "<URL_DE_RECUPERACAO_DE_CONTA_DO_PROVEDOR>"
url_suporte = "<URL_DO_CANAL_INSTITUCIONAL_DE_SUPORTE>"

[auth]
redirect_uri = "https://icms-ecologico.streamlit.app/oauth2callback"
cookie_secret = "<SEGREDO_FORTE_GERADO_PARA_A_APLICACAO>"
client_id = "<CLIENT_ID_DO_PROVEDOR>"
client_secret = "<CLIENT_SECRET_DO_PROVEDOR>"
server_metadata_url = "<URL_DE_METADADOS_OIDC_DO_PROVEDOR>"

[gcp_service_account]
type = "service_account"
project_id = "<PROJETO_GOOGLE_CLOUD>"
private_key_id = "<ID_DA_CHAVE>"
private_key = "<CHAVE_PRIVADA>"
client_email = "<EMAIL_DA_CONTA_DE_SERVICO>"
client_id = "<ID_DA_CONTA_DE_SERVICO>"
token_uri = "https://oauth2.googleapis.com/token"
```

O formato de autenticação acima usa um provedor OIDC único. A instituição deve
fornecer os dados reais e registrar a URL de retorno da aplicação no provedor.
Os e-mails de `user1`, `user2` e `user3` são marcadores de configuração, não
logins funcionais. A conta de serviço do Google Sheets precisa receber acesso à
planilha que contém as abas `Fichas` e `Historico`.

Não coloque o conteúdo real dos Secrets no GitHub, neste arquivo ou em mensagens.

## Comportamento da consulta consolidada

- A tabela inclui apenas fichas concluídas; rascunhos continuam no módulo Ficha.
- A fonte é o repositório configurado para o aplicativo. No modo persistente,
  os dados vêm da planilha Google Sheets conectada; o arquivo Excel anterior é
  referência de visualização e regras, não a base duplicada do sistema.
- Os filtros existentes permitem localizar por processo ou unidade.
- A grade mantém o processo e a unidade visíveis durante a rolagem horizontal.
- As alterações devem ser realizadas pela ficha e pelo fluxo de atualização,
  preservando validações e histórico.

## Limite deste pacote

Esta entrega contém código preparado e testes locais. Ela não configura o
provedor de identidade, as três contas reais, a planilha institucional, os
Secrets do Streamlit Cloud nem publica uma nova versão da aplicação.
Até que esses itens sejam fornecidos e testados, não use o modo demonstração
para registrar dados reais.
