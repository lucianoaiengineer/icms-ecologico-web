# Persistência e recuperação de edições

O sistema disponibiliza uma **demonstração temporária** e um **modo de banco SQL**. A configuração de um banco persistente é necessária para preservar fichas entre sessões e reinicializações da aplicação.

## Modos disponíveis

| Modo | Uso | Armazenamento |
| --- | --- | --- |
| `demonstracao` | Testes com dados fictícios | Memória isolada da sessão; backup CSV manual. |
| `banco` | Homologação e eventual operação institucional | SQLite em volume persistente ou PostgreSQL externo. |

O código não configura automaticamente servidores, contas, credenciais, backups nem permissões de infraestrutura.

## Estrutura SQL

| Tabela | Conteúdo |
| --- | --- |
| `icms_fichas` | Fichas oficiais ativas, versão, autor, situação e conteúdo em JSON. |
| `icms_historico` | Eventos de gravação e exclusão, diferenças e hash de conteúdo. |
| `icms_edicoes_automaticas` | Edições provisórias por usuário e processo, ainda não publicadas. |

As operações oficiais usam transações com controle de versão. Uma gravação rejeitada por conflito deve ser revista antes de novo envio. O histórico técnico não é uma assinatura digital imutável.

## O que a cópia automática faz

Ao alterar um campo e permitir que o Streamlit processe a mudança, o modo `banco` pode registrar uma **cópia de edição**. Essa cópia não substitui a ficha oficial e não afeta o relatório.

Quando o mesmo usuário retornar, a aplicação poderá oferecer **Recuperar edição**. A recuperação é bloqueada se a versão oficial tiver sido alterada. Edições ainda não transmitidas ao servidor podem ser perdidas.

## Preparação para homologação

1. Criar uma base **de teste** isolada, com usuário de acesso restrito e conexão protegida.
2. Configurar `modo = "banco"`, `banco_url`, listas de perfis e `[auth]` nos Secrets da hospedagem.
3. Instalar todas as dependências de `requirements.txt`.
4. Testar cadastro, rascunho, conclusão, atualização, exclusão, concorrência e recuperação após nova sessão.
5. Comprovar backup e restauração do banco em ambiente separado.
6. Registrar a versão implantada, os responsáveis e os resultados da homologação.

Para uso hospedado no Streamlit Community Cloud, recomenda-se **PostgreSQL externo**. Não utilize SQLite em disco efêmero como base oficial.

### Exemplo de endereço do banco

```toml
modo = "banco"
banco_url = "postgresql+psycopg://USUARIO:SENHA@HOST:5432/BASE?sslmode=require"
```

Em servidor próprio, com diretório persistente e protegido, a aplicação também aceita `sqlite:////caminho/persistente/icms.sqlite`.

## Limitações que exigem atenção

- O aviso de saída do navegador não cobre todas as interrupções, como falta de energia.
- Duas abas do mesmo usuário podem substituir a última cópia provisória uma da outra; a gravação oficial continua protegida por versão.
- O sistema não inclui política operacional pronta de retenção, migrações de esquema, cópias automáticas de segurança do banco ou restauração institucional.
- A demonstração não migra suas fichas automaticamente para o banco SQL.
- A implantação institucional depende de homologação visual, funcional, de segurança e de recuperação.

Consulte também [Configuração de acesso e resultados](CONFIGURACAO_ACESSO_E_RESULTADOS.md).
