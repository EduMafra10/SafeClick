# SafeClick — Aprenda antes de clicar

Projeto de Conclusão de Curso de Sistemas de Informação da Universidade de Mogi das Cruzes (UMC).

O SafeClick é uma plataforma web educativa voltada a estudantes do ensino médio e universitários. Seu objetivo é ajudar os usuários a reconhecer golpes digitais e adotar práticas mais seguras na internet.

A versão desta etapa está reunida na branch **`entrega0911`**.

## Funcionalidades implementadas

**Conta e acesso**

- **Cadastro:** nome, e-mail com confirmação, senha com pelo menos 15 caracteres e aceite dos Termos de Uso; senha guardada com hash `scrypt`.
- **Login com autenticação em dois fatores:** e-mail e senha, seguidos do código de um aplicativo autenticador pela API Twilio Verify.
- **Recuperação de senha:** link de uso único enviado por e-mail (Gmail), válido por 30 minutos.
- **Minha conta:** alteração do nome, ícone de perfil entre personagens prontos, troca de senha com aviso por e-mail e encerramento das outras sessões.
- **Exclusão de conta:** pedido com prazo de 30 dias para reativar pelo link enviado por e-mail; depois disso, os dados pessoais são anonimizados.

**Atividades educativas**

- **Conteúdos educativos:** textos sobre golpes digitais e segurança, com marcação de leitura concluída.
- **Quizzes e Oficina SafeClick:** perguntas de múltipla escolha e oficinas de cartões, corrigidas no servidor, com explicações.
- **Simulações de golpes:** e-mail, SMS, conversa e loja falsos, com consequências de cada escolha e as pistas do golpe numeradas na própria mensagem.
- **Laboratório de senhas:** analisador de força (no próprio navegador), gerador de senhas e frases-senha e o desafio "Qual vazou mais?", que usa a Pwned Passwords API.
- **Meu progresso e conquistas:** painel com o desempenho por período e conquistas desbloqueadas pelas atividades.
- **Avaliações:** nota de 1 a 5 e comentário opcional sobre conteúdos e quizzes, ativadas pela variável `AVALIACOES_ATIVAS`.

**Área administrativa**

- **Visão geral:** indicadores de uso em 7, 30 ou 90 dias, sem contar administradores, com as questões que os usuários mais erram e exportação para planilha do Excel.
- **Contas:** busca, filtros por perfil, autenticador e situação, último acesso, redefinição do autenticador e promoção a administrador.
- **Catálogo:** editor de conteúdos, quizzes, oficinas, simulações e páginas, com prévia igual à tela do usuário e publicação de versões.
- **Auditoria:** registro de cadastro, login, saída, acessos negados, atividades e ações administrativas, com filtros.

## Tecnologias

- Python e Flask.
- Jinja2, HTML, CSS e JavaScript.
- PostgreSQL hospedado no Neon.
- Psycopg 3, com consultas SQL parametrizadas e sem ORM.
- Flask-Login para integração da autenticação com a aplicação.
- Flask-WTF para formulários e proteção CSRF.
- Werkzeug para geração e verificação dos hashes de senha.
- Twilio Verify para o segundo fator.
- Biblioteca `qrcode` para gerar o QR Code localmente.
- Gmail (SMTP) para os e-mails de recuperação de senha, troca de senha e exclusão de conta.
- Pwned Passwords API (Have I Been Pwned) para o desafio do laboratório de senhas.
- `@zxcvbn-ts` para o analisador de força de senha no navegador.
- Chart.js para os gráficos.
- openpyxl para gerar a planilha da Visão geral.
- Pytest para os testes automatizados.
- Flake8 para a padronização do código Python.
- Vercel para a hospedagem.

As versões das dependências estão registradas em `requirements.txt`.

## Organização do projeto

| Arquivo ou pasta | Responsabilidade |
| --- | --- |
| `safeclick/__init__.py` | Criação da aplicação, configurações e registro das funcionalidades. |
| `safeclick/autenticacao.py` | Cadastro, login, segundo fator e saída da conta. |
| `safeclick/formularios.py` | Campos, validações e formulários protegidos por CSRF. |
| `safeclick/usuarios_db.py` | Cadastro e consultas dos usuários. |
| `safeclick/logins_db.py` | Pendências entre a senha e a confirmação do segundo fator. |
| `safeclick/mfa.py` | Configuração e confirmação do autenticador. |
| `safeclick/twilio_api.py` | Comunicação com a API Twilio Verify. |
| `safeclick/sessoes.py` | Sessões autenticadas e verificação de perfis. |
| `safeclick/limites.py` | Limites de tentativas de login e configuração do autenticador. |
| `safeclick/auditoria.py` e `safeclick/auditoria_db.py` | Página administrativa, consulta e gravação dos eventos de auditoria. |
| `safeclick/db.py` | Conexão com o banco e registro das tentativas de simulação. |
| `safeclick/conteudos.py` e `safeclick/conteudos_db.py` | Páginas e consultas dos conteúdos educativos. |
| `safeclick/quizzes.py` | Exibição, correção e gravação dos quizzes. |
| `safeclick/simulacoes.py` | Cenário, escolhas e feedback da simulação. |
| `safeclick/privacidade.py` | Páginas de Política de Privacidade e Termos de Uso. |
| `safeclick/recuperacao.py` | Recuperação de senha por e-mail. |
| `safeclick/conta.py` e `safeclick/exclusao_conta.py` | Minha conta, exclusão e reativação da conta. |
| `safeclick/senhas.py` | Laboratório de senhas e desafio "Qual vazou mais?". |
| `safeclick/painel.py` e `safeclick/conquistas.py` | Meu progresso e conquistas. |
| `safeclick/avaliacoes.py` | Avaliações de conteúdos e quizzes. |
| `safeclick/administracao.py` e `safeclick/catalogo_admin.py` | Visão geral, contas e editor do catálogo. |
| `safeclick/visao_geral_db.py` e `safeclick/visao_geral_excel.py` | Indicadores da Visão geral e planilha do Excel. |
| `safeclick/emails.py` | Envio dos e-mails pelo Gmail. |
| `scripts/dados_demonstracao.py` | Cria e apaga as contas fictícias de demonstração. |
| `app.py` e `vercel.json` | Ponto de entrada e configuração da hospedagem na Vercel. |
| `safeclick/templates/` | Templates HTML. |
| `safeclick/static/` | Estilos e JavaScript. |
| `sql/` | Scripts de criação e atualização do banco. |
| `criar_tentativas_simulacao.sql` | Criação inicial da tabela de tentativas da simulação. |

## Executar no Windows

Abra o PowerShell na pasta principal do projeto, onde está o arquivo `requirements.txt`.

### 1. Preparar o ambiente

Se ainda não existir um ambiente virtual:

```powershell
py -m venv .venv
```

Instale as dependências:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 2. Configurar as variáveis de ambiente

Crie o arquivo `.env` somente se ele ainda não existir:

```powershell
if (-not (Test-Path -LiteralPath .env)) {
    Copy-Item -LiteralPath .env.example -Destination .env
}
```

O `.env.example` traz todas as variáveis, separadas por seção e com valores de exemplo no formato esperado. No `.env`, troque cada valor de exemplo pelo valor real do ambiente utilizado pelo grupo. As variáveis são lidas em `safeclick/config.py`:

- `APP_ENV=desenvolvimento` exige somente a `SECRET_KEY` para iniciar;
- `APP_ENV=producao` exige também o banco, a Twilio e o e-mail, uma `SECRET_KEY` com pelo menos 32 caracteres e um `APP_BASE_URL` com `https://`, e ativa o cookie seguro.

Se faltar alguma variável obrigatória, a aplicação não inicia e informa quais estão faltando.

- **Neon:** obtenha a conexão selecionando o projeto, a branch e o banco corretos. Preserve os parâmetros fornecidos pelo serviço.
- **Twilio:** utilize as credenciais da conta e o identificador de um serviço Verify configurado para TOTP.
- **SECRET_KEY:** mantenha a chave existente quando o ambiente já estiver configurado.

Para uma instalação nova, caso ainda não exista uma `SECRET_KEY`, gere uma:

```powershell
.\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_hex(32))"
```

Essa chave é utilizada na assinatura do cookie, na proteção CSRF e no controle de tentativas.

O `.env` e a pasta `.venv` são ignorados pelo Git. Não inclua credenciais reais no `.env.example`, no código ou na documentação.

No teste local por HTTP, utilize `SESSION_COOKIE_SECURE=false`. Na publicação por HTTPS, configure `SESSION_COOKIE_SECURE=true`. Essa variável não ativa HTTPS por conta própria.

### 3. Preparar o banco

**Em um banco novo**, execute os scripts no SQL Editor do Neon nesta ordem:

1. `sql/criar_usuarios.sql`
2. `sql/criar_logs_auditoria.sql`
3. `sql/adicionar_mfa_usuarios.sql`
4. `sql/criar_logins_pendentes.sql`
5. `sql/criar_controle_autenticacao.sql`
6. `criar_tentativas_simulacao.sql`
7. `sql/criar_conteudos.sql`
8. `sql/inserir_conteudos_iniciais.sql`
9. `sql/criar_quizzes.sql`
10. `sql/inserir_quizzes_iniciais.sql`
11. `sql/adicionar_token_tentativas.sql`
12. `sql/vincular_tentativas_usuarios.sql`
13. `sql/criar_recuperacoes_senha.sql`
14. `sql/criar_aceites_termos.sql`
15. `sql/registrar_termos_1_0.sql`
16. `sql/criar_politica_e_leis.sql`
17. `sql/registrar_politica_e_leis.sql`
18. `sql/inserir_conteudos_adicionais.sql`
19. `sql/criar_gestao_simulacoes.sql`
20. `sql/criar_conclusoes_conteudo.sql`
21. `sql/criar_desafios_senha.sql`
22. `sql/adicionar_gestao_catalogo.sql`
23. `sql/adicionar_formato_quizzes.sql`
24. `sql/criar_conquistas.sql`
25. `sql/criar_avaliacoes.sql`
26. `sql/adicionar_icone_usuarios.sql`
27. `sql/adicionar_exclusao_conta.sql`
28. `sql/adicionar_avaliacoes_publicas_ranking.sql`
29. `sql/registrar_politica_1_3_participacao.sql`
30. `sql/remover_ranking.sql`
31. `sql/registrar_politica_1_4_avaliacoes.sql`
32. `sql/registrar_politica_1_5_termos_1_1.sql`

O [guia do RF17](docs/avaliacoes.md) explica como habilitar e testar as avaliações em ambiente de teste e preparar a coleta real.

O [guia de avaliações e progresso](docs/avaliacoes_progresso.md) descreve as avaliações públicas, a moderação, o progresso privado e os testes PostgreSQL. O ranking foi retirado. Em um banco já atualizado até o item 29, aplique os itens 30 e 31 antes de reiniciar esta versão. Os scripts anteriores permanecem como histórico das migrações.

Se o banco já estiver preparado, confira quais scripts foram aplicados. Não repita indiscriminadamente os scripts de criação, alteração ou carga inicial.

Em um banco novo, após a preparação, carregue os quatro cenários iniciais:

```powershell
.\.venv\Scripts\python.exe -m flask --app safeclick importar-cenarios-iniciais
```

Para usar o catálogo da **Área administrativa** e preparar um banco existente, siga o [guia de gestão do catálogo](docs/gestao_catalogo.md).

A revisão didática dos quizzes e oficinas está em `dados/revisao_didatica/` e é publicada pelo script `scripts/aplicar_revisao_didatica.py`, que primeiro confere o banco e só grava com `--aplicar`.

A Política de Privacidade e os Termos de Uso ficam arquivados no banco (`versoes_politica` e `versoes_termos`), com as leis citadas em `referencias_legais`. Para mudar um texto, publique uma nova versão no banco antes de alterar `VERSAO_POLITICA` ou `VERSAO_TERMOS` em `safeclick/privacidade.py`.

O arquivo `sql/verificar_estrutura_quizzes.sql` auxilia na inspeção da estrutura dos quizzes.

Um commit ou merge no Git não executa scripts no Neon. Integrantes conectados ao mesmo banco e à mesma branch do Neon compartilham os dados, mesmo trabalhando em branches Git diferentes.

### 4. Verificar a configuração

Confira a conexão com o banco:

```powershell
.\.venv\Scripts\python.exe -m flask --app safeclick verificar-banco
```

Confira a comunicação com o serviço Twilio:

```powershell
.\.venv\Scripts\python.exe -m flask --app safeclick verificar-twilio
```

Confira o carregamento das rotas:

```powershell
.\.venv\Scripts\python.exe -m flask --app safeclick routes
```

Esses comandos verificam conexão e carregamento. Eles não substituem o teste completo de cadastro, ativação do autenticador e login.

### 5. Iniciar a aplicação

```powershell
.\.venv\Scripts\python.exe -m flask --app safeclick run
```

Acesse:

| Página | Endereço local |
| --- | --- |
| Login | [Abrir login](http://127.0.0.1:5000/login) |
| Cadastro | [Criar conta](http://127.0.0.1:5000/cadastro) |
| Meu progresso | [Abrir painel](http://127.0.0.1:5000/painel/) |
| Conteúdos | [Abrir conteúdos](http://127.0.0.1:5000/conteudos/) |
| Quizzes | [Abrir quizzes](http://127.0.0.1:5000/quizzes/) |
| Simulações | [Abrir simulações](http://127.0.0.1:5000/simulacoes/) |
| Laboratório de senhas | [Abrir laboratório](http://127.0.0.1:5000/laboratorio-senhas/) |
| Minha conta | [Abrir conta](http://127.0.0.1:5000/conta/) |
| Área administrativa | [Abrir Visão geral](http://127.0.0.1:5000/administracao/) |

As páginas educativas exigem autenticação. A página inicial leva o usuário ao painel Meu progresso e o administrador à Visão geral; usuários sem sessão são encaminhados ao login.

Mantenha o terminal aberto durante o uso. Para encerrar o servidor, pressione `Ctrl + C`.

## Funcionamento do login e da API externa
Documentação técnica e projeto lógico: [Documentação da integração Twilio](safeclick/docs/integracao-twilio.md)

O fluxo principal é:

**E-mail e senha → código do autenticador → validação pela Twilio Verify → criação da sessão → Meu progresso.**

No primeiro acesso:

1. O usuário cria uma conta e informa suas credenciais no login.
2. O SafeClick valida a senha e inicia uma pendência de login.
3. O usuário solicita o QR Code e o lê em um aplicativo autenticador.
4. O primeiro código confirma a ativação do aplicativo.
5. O usuário aguarda o próximo código e o informa para concluir o login.
6. A sessão é criada após a aprovação do segundo fator.

Nos acessos seguintes, o usuário informa a senha e o código do aplicativo já vinculado. Não é necessário gerar outro QR Code.

O servidor do SafeClick realiza as chamadas à API. A senha e seu hash não são enviados à Twilio. O vínculo externo utiliza um UUID associado à conta local.

O QR Code é gerado dentro da aplicação. As credenciais da Twilio permanecem no servidor.

A integração utiliza os recursos de fator e desafio da Verify API. A ativação exige o estado `verified`; a conclusão do login exige um desafio com estado `approved`.

Referências oficiais:

- [Twilio Verify TOTP](https://www.twilio.com/docs/verify/quickstarts/totp)
- [Recurso Factor](https://www.twilio.com/docs/verify/api/factor)
- [Recurso Challenge](https://www.twilio.com/docs/verify/api/challenge)

O login com segundo fator depende da disponibilidade da API e das condições da conta Twilio.

## Proteções implementadas

- Senhas entre 15 e 128 caracteres no cadastro, preservando os espaços digitados.
- Armazenamento das senhas com hash `scrypt`.
- Validação dos formulários no servidor e proteção CSRF.
- Limite de cinco envios válidos de formulário de login por e-mail em cinco minutos; envios corretos também contam.
- Limite de três solicitações de configuração do autenticador por usuário em cinco minutos.
- Pendência de login com prazo de cinco minutos e até cinco envios de código.
- Sessões com expiração após 30 minutos de inatividade ou oito horas desde sua criação.
- Revogação da sessão atual no banco ao sair da conta.
- Cookies com `HttpOnly`, `SameSite=Lax` e opção `Secure` conforme o ambiente.
- Cabeçalho `Cache-Control: no-store` nas respostas de autenticação e páginas autenticadas.
- Verificação de sessão e perfil antes do acesso aos módulos educativos.
- Consulta do resultado do quiz restrita ao usuário proprietário da tentativa.
- Histórico de auditoria restrito ao perfil `administrador`.
- Troca de senha somente com a senha atual, encerrando as outras sessões da conta.
- Cabeçalhos de segurança (`X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy`, `Permissions-Policy` e HSTS em HTTPS).
- Páginas de erro próprias, em português, sem detalhes internos.
- Conteúdos do catálogo com formatação simples convertida no servidor; HTML digitado é exibido como texto.

O cadastro público cria contas com perfil `usuario`. O perfil `administrador` não pode ser escolhido pelo formulário de cadastro.

## Registro das atividades

As novas tentativas de quizzes e simulações recebem o identificador do usuário autenticado.

Registros antigos, anteriores à inclusão desse vínculo, podem permanecer com `usuario_id` vazio. A atualização do banco não atribui automaticamente esses registros a uma conta.

Nos quizzes:

- O servidor consulta o gabarito e calcula a pontuação.
- A tentativa e suas respostas são gravadas na mesma transação.
- Um token identifica o envio para evitar gravação duplicada do mesmo formulário.
- O resultado corresponde à última tentativa associada à sessão, com conferência do usuário proprietário.

Na simulação:

- Escolhas ausentes ou inválidas são rejeitadas.
- Após a gravação, o servidor redireciona para o resultado.
- Atualizar a página do resultado não registra outra tentativa.
- Um novo envio válido pode registrar outra tentativa.
- O parâmetro de resultado na URL seleciona o feedback educativo; abrir esse endereço não comprova uma nova tentativa.

## Verificação após integrar alterações

Os testes manuais realizados durante o desenvolvimento confirmaram cadastro, configuração do autenticador, login com segundo fator, bloqueio por limite de login e encerramento da sessão.

Após uma nova integração, confira:

1. Cadastro de uma conta de teste.
2. Rejeição de credenciais inválidas.
3. Configuração inicial do autenticador e login com novo código.
4. Solicitação do segundo fator nos acessos seguintes.
5. Redirecionamento para Meu progresso após o login.
6. Acesso autenticado a conteúdos, quizzes, simulações e laboratório.
7. Gravação das novas tentativas com `usuario_id`.
8. Encerramento da sessão e bloqueio do acesso direto às páginas protegidas.
9. Consulta dos registros na página `/auditoria/` com uma conta administrativa.

Validações com falhas simuladas não substituem a conferência do ambiente final com Neon e Twilio.

## Testes automatizados

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Os testes não usam o banco real nem as APIs externas: as chamadas são simuladas. A suíte cobre autenticação, conta, quizzes, oficinas, simulações, laboratório, painel, avaliações, auditoria e área administrativa.

Para conferir a padronização do código (regras em `.flake8`):

```powershell
.\.venv\Scripts\python.exe -m flake8
```

O resultado esperado é nenhum aviso.

## Dados de demonstração

Para apresentar a Visão geral com histórico, o script cria 10 contas fictícias (`@demonstracao.example`), que não fazem login, com atividades dos últimos 30 dias:

```powershell
.\.venv\Scripts\python.exe scripts\dados_demonstracao.py --criar
.\.venv\Scripts\python.exe scripts\dados_demonstracao.py --apagar
```

O script usa o banco configurado no `.env`. Informe na apresentação que esses dados são de demonstração.

## Hospedagem na Vercel

O `app.py` expõe a aplicação para a Vercel, e o `vercel.json` fixa a região de São Paulo (`gru1`), próxima ao banco do Neon. Configure as variáveis do `.env.example` no painel da Vercel com `APP_ENV=producao`, `SESSION_COOKIE_SECURE=true` e `APP_BASE_URL` com o endereço `https://` publicado. Na Vercel, os e-mails são enviados antes da resposta e o IP do usuário é lido pelo proxy.

## Pendências e limites desta etapa

- Validação do ambiente publicado na Vercel.
- O login depende da disponibilidade da Twilio, e os e-mails dependem dos limites de envio do Gmail.

## Integrantes

- Eduardo Mafra dos Santos
- Humberto Ribeiro Bezerra
- João Henrique Alves de Souza
