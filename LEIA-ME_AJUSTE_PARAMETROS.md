# Ajuste da ficha de parâmetros — ICMS Ecológico

Alteração preparada em 06/11/2026 sobre os arquivos da branch `main` do repositório `lucianoaiengineer/icms-ecologico-web`.

## Comportamento corrigido

- Município identificado aceita valores inteiros de 0 a 9, inclusive zero.
- Sem município, qualquer valor preenchido, inclusive zero, impede a gravação do rascunho ou da ficha concluída.
- Os campos de valor ficam desabilitados até que a posição tenha nome de município. Nome vazio, apenas espaços ou o marcador `-` não identifica município.
- Os quatro blocos municipais 10, 11, 11.1 e 11.2 iniciam recolhidos e podem ser abertos manualmente.
- O botão redundante `Nova ficha` foi removido. A consulta por SEI continua abrindo a ficha existente ou uma ficha nova com o processo informado.
- A confirmação antes de descartar alterações não gravadas na consulta foi preservada, tanto ao abrir um registro existente quanto ao iniciar uma ficha de processo ainda não cadastrado.
- Campo vazio continua diferente de zero. Os nomes compartilhados e as chaves internas dos quatro blocos foram preservados.
- Se o nome de uma posição que já possui valores for apagado, os valores não são apagados silenciosamente: a validação impede salvar até corrigir essa posição.

## Arquivos de execução alterados

- `app.py`: remoção do botão `Nova ficha`, estado inicial dos expansores, orientação de preenchimento e bloqueio de valores sem nome.
- `icms/regras.py`: validação também rejeita zero sem município.

Esses dois arquivos substituem os correspondentes nas mesmas pastas do projeto existente. O pacote contém apenas a atualização, não o sistema completo. As dependências não mudaram.

## Verificação

Foram executados 43 testes automatizados de regras, persistência e interface com Streamlit AppTest, todos aprovados. A versão de Streamlit utilizada foi a definida no projeto: 1.66.0.

As verificações adicionais estão em `tests/test_regras.py` e `tests/test_interface.py`. A execução usou o modo de demonstração, com os dados sintéticos dos testes existentes, sem acesso à base institucional.

## Publicação

Os arquivos deste pacote estão corrigidos. Eles ainda não foram publicados no repositório nem na aplicação Streamlit.
