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
`None` antes do login. Quizzes, simulações e conteúdos já a utilizam.
Para uma ação que grava no banco, passe a conexão existente a `registrar_evento`
para confirmar a operação e seu log na mesma transação. A importação local em
`safeclick/db.py` evita um ciclo com `auditoria_db.py`.

## Integrações pendentes do grupo

- O cadastro já registra `usuario.cadastrado` com a conta na mesma transação.
- No login, registrar `login.sucesso` após confirmar a identidade. Registrar
  `login.falha` sem associar a tentativa a uma conta apenas pelo e-mail digitado.
- No logout, guardar o ID autenticado e registrar `logout.realizado` antes de
  limpar a sessão.
- Em acessos proibidos de outras áreas, registrar `acesso.negado`.
- Na integração externa, registrar `api.consultada` com serviço e resultado,
  sem copiar credenciais, URL com parâmetros ou dados da resposta.
- No aceite, registrar `termo.aceito` com a versão aceita, junto do registro
  do aceite no banco. O log sozinho não substitui o aceite.

Os nomes aceitos estão em `EVENTOS_PERMITIDOS`. A rota de auditoria já registra
`auditoria.consultada` e uma tentativa de acesso por usuário comum como
`acesso.negado`.

## Verificação

Execute `python -m unittest discover -s tests -v` com o ambiente virtual ativo.
Os testes verificam acesso anônimo, perfil comum, perfil administrador, filtros
inválidos e identificação pela sessão. Depois de integrar o login, teste no
navegador com contas reais dos dois perfis e confira os registros no Neon.
