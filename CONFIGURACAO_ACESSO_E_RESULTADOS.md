# Configuração de acesso e resultados

Este guia apresenta os requisitos de acesso ao **Sistema Web de Gestão de Fichas do ICMS Ecológico** e os cuidados necessários para uso de registros institucionais.

## Perfis e autenticação

No modo **banco**, o usuário deve entrar com uma identidade verificada por um provedor **OIDC**. O sistema consulta listas de e-mails autorizados para definir seu perfil:

- **Editor:** consulta, cadastra, atualiza e exclui fichas conforme as validações.
- **Leitor:** consulta fichas e resultados; não deve gravar ou excluir.

O sistema não cria senhas. A recuperação de conta deve ser oferecida pelo provedor de identidade definido pela instituição.

## Configuração protegida

A hospedagem precisa receber, em **Secrets**, a URL do banco, os perfis e as informações OIDC. Os valores abaixo são apenas marcadores de formato:

```toml
modo = "banco"
banco_url = "postgresql+psycopg://USUARIO:SENHA@HOST:5432/BASE?sslmode=require"
editores = ["EDITOR_AUTORIZADO"]
leitores = ["LEITOR_AUTORIZADO"]
url_recuperacao = "https://DOMINIO-INSTITUCIONAL/recuperacao"
url_suporte = "https://DOMINIO-INSTITUCIONAL/suporte"

[auth]
redirect_uri = "https://DOMINIO-DA-APLICACAO/oauth2callback"
cookie_secret = "SEGREDO_A_CONFIGURAR"
client_id = "IDENTIFICADOR_DO_PROVEDOR"
client_secret = "SEGREDO_DO_PROVEDOR"
server_metadata_url = "https://PROVEDOR/.well-known/openid-configuration"
```

**Nunca publique Secrets, senhas, chaves ou dados pessoais no GitHub.** A conexão, os perfis e as permissões devem ser conferidos com contas de teste autorizadas.

## Consulta de resultados

O módulo **Resultados** utiliza somente **fichas concluídas** do repositório selecionado. Rascunhos e cópias automáticas de edição não entram nesse relatório.

Há duas grades: **Resumo das fichas**, com uma linha por processo concluído (9 colunas), e **Resultados por município**, com uma linha por município cadastrado (27 colunas). Os filtros permitem localizar processos, unidades e municípios; cada grade possui seu próprio CSV. Não são criadas colunas para posições municipais vazias. A fórmula do FQ utiliza apenas os pontos validados dos 14 parâmetros gerais e dos quatro blocos do município.

A exclusão confirmada remove a ficha do conjunto ativo consultado e do CSV gerado depois da operação. O histórico de exclusão continua registrado.

## Condições de liberação

Antes do uso institucional, é necessário homologar login, autorização de leitores e editores, gravação e leitura com PostgreSQL, recuperação de edições, backup, restauração e o mapeamento dos fatores de qualidade.

Uma instalação em modo demonstração **não constitui base institucional**: os dados são temporários e devem ser fictícios.
