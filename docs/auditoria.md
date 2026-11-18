# Auditoria do SafeClick

A aplicação grava os eventos em `public.logs_auditoria`, no PostgreSQL. A página
`/auditoria/` mostra o histórico apenas ao perfil `administrador`. Visitantes
são redirecionados ao login e usuários autenticados sem esse perfil recebem HTTP 403.
A consulta permite filtrar por evento ou categoria, resultado, ID/nome/e-mail do
usuário e intervalo de datas no horário de Brasília, com 50 registros por página.
Cada consulta administrativa também é auditada e pode ser incluída pelo filtro
próprio. A categoria **Avaliações e moderação** reúne os envios e as decisões
administrativas; o painel de avaliações também oferece um atalho para ela.

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
- Criar e editar avaliações gera `avaliacao.salva`, inclusive para avaliações
  privadas. Os detalhes distinguem criação/atualização, modalidade, revisão e
  opções de divulgação. O recurso identifica a atividade por seu ID estável,
  com os tipos `avaliacao_conteudo`, `avaliacao_quiz` ou `avaliacao_oficina`.
- Retirada da divulgação e exclusão pelo titular geram, respectivamente,
  `avaliacao.publicacao_retirada` e `avaliacao.excluida`.
- Abrir a revisão administrativa gera `avaliacao.previa_consultada`. Esta
  consulta não significa aprovação. A confirmação de aprovar ou bloquear gera
  `avaliacao.moderada`, com o ID interno do autor, a ação e a revisão moderada.
  O texto do comentário e a nota não são copiados para os detalhes dos logs.
- Alterar o ícone do perfil gera `usuario.perfil_atualizado`, somente quando
  o valor muda. Conquistas recém-concedidas geram `conquista.concedida`, com o
  código da conquista; conquistas já liberadas não geram eventos duplicados.
- Aceites geram `termo.aceito` com a versão, na mesma transação do registro de
  aceite. O evento não substitui o registro específico do aceite.

## Transações e limites

As gravações locais descritas acima usam a conexão da operação para confirmar
os dados e a auditoria juntos. Uma falha de auditoria reverte o salvamento da
avaliação. Consultas periódicas à quantidade de pendências não geram logs,
evitando um evento a cada atualização automática do menu.

Registros antigos são preservados. A identificação da atividade e as demais
informações novas valem para ações executadas após a atualização; eventos
históricos sem referência não são preenchidos com dados presumidos.

Os nomes aceitos estão em `EVENTOS_PERMITIDOS`.

## Verificação

Execute `python -m pytest -q` com o ambiente virtual ativo.
Os testes verificam perfis de acesso, filtros, cadastro, login, saída, consultas
à Twilio e registros de tentativas. No navegador, entre com contas reais dos
perfis `usuario` e `administrador`, conclua um quiz, saia e confira os eventos
na página `/auditoria/` com a conta administrativa. Crie/edite uma avaliação de
conteúdo, quiz e oficina, incluindo uma avaliação privada, e confira a categoria
**Avaliações e moderação** sem filtro de conta ou período. A suíte PostgreSQL
dedicada também verifica esses fluxos e o rollback quando a auditoria falha.
