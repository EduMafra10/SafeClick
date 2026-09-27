# Auditoria do SafeClick

A aplicação grava os eventos em `public.logs_auditoria`, no PostgreSQL. A página
`/auditoria/` mostra o histórico apenas ao perfil `administrador`. Visitantes
são redirecionados ao login e usuários autenticados sem esse perfil recebem HTTP 403.
A consulta permite filtrar por evento, ID do usuário e intervalo de datas em UTC,
com 50 registros por página. Cada consulta administrativa também é auditada.

## Dados registrados

Cada evento contém data e hora, ID do usuário quando identificado, nome do
evento, resultado, tipo e ID do registro relacionado e detalhes específicos.
O sistema não deve enviar senhas, hashes, cookies, tokens, URL de conexão,
conteúdo completo de formulários ou respostas de APIs para os detalhes.
O grupo deve incluir esses dados, sua finalidade, acesso e retenção na Política
de Privacidade específica do SafeClick.

O módulo `safeclick/auditoria_db.py` fornece `registrar_evento()` e
`usuario_autenticado_id()`. A segunda função consulta o Flask-Login e retorna
`None` antes do login. Os registros de quizzes, simulações e conteúdos incluem
o ID do usuário autenticado.
Para uma ação que grava no banco, passe a conexão existente a `registrar_evento`
para confirmar a operação e seu log na mesma transação. A importação local em
`safeclick/db.py` evita um ciclo com `auditoria_db.py`.

## Eventos integrados

- Cadastro, sessão de login, saída, conclusão de quiz, conclusão de simulação e
  leitura de conteúdo são registrados com o ID da conta. A criação ou revogação
  da sessão e o respectivo log usam a mesma transação.
- Falhas na senha não são vinculadas a uma conta somente pelo e-mail informado.
  Após a senha correta, uma falha no autenticador pode incluir o ID da conta.
  Os detalhes registram apenas a etapa e uma categoria de motivo.
- Acessos de usuários autenticados sem o perfil exigido registram
  `acesso.negado`. A própria página administrativa registra suas consultas.
- As chamadas à Twilio registram `api.consultada` com operação e resultado,
  sem códigos ou dados da resposta. Antes do login, esses eventos não têm ID
  de usuário. Uma falha ao gravar esse evento não altera o resultado da chamada
  externa; a falha também fica sinalizada no log do servidor.

## Integração pendente do grupo

Quando o Termo de Aceite estiver integrado, registrar `termo.aceito` com a
versão aceita na mesma transação do aceite. O log sozinho não substitui o
registro de consentimento.

Os nomes aceitos estão em `EVENTOS_PERMITIDOS`.

## Verificação

Execute `python -m unittest discover -s tests -v` com o ambiente virtual ativo.
Os testes verificam perfis de acesso, filtros, cadastro, login, saída, consultas
à Twilio e registros de tentativas. No navegador, entre com contas reais dos
perfis `usuario` e `administrador`, conclua um quiz, saia e confira os eventos
na página `/auditoria/` com a conta administrativa.
