# SafeClick — Aprenda antes de clicar

Projeto de Conclusão de Curso de Sistemas de Informação da Universidade de Mogi das Cruzes (UMC).

O SafeClick é uma plataforma web educativa voltada a estudantes do ensino médio e universitários. Seu objetivo é ajudar os usuários a reconhecer golpes digitais e adotar práticas mais seguras na internet.

A versão desta etapa está reunida na branch **`entrega2809`**.

## Funcionalidades implementadas

- **Cadastro:** criação de conta com nome, e-mail e senha, validação dos campos e armazenamento da senha com hash `scrypt`.
- **Login com autenticação em dois fatores:** validação de e-mail e senha, seguida da confirmação de um código do aplicativo autenticador pela API Twilio Verify.
- **Controle de sessão e acesso:** encerramento da sessão, expiração por tempo e exigência de autenticação para acessar conteúdos, quizzes e simulações.
- **Conteúdos educativos:** listagem de temas e páginas de leitura sobre phishing e proteção de senhas.
- **Quizzes interativos:** perguntas de múltipla escolha, correção no servidor, pontuação, explicações e gravação das respostas.
- **Simulação de golpe digital:** cenário de e-mail fictício de conta bloqueada, com alternativas, consequências e orientações.
- **Registro das atividades:** novas tentativas de quizzes e simulações vinculadas ao usuário autenticado.

As telas de login, cadastro e segundo fator seguem o mesmo padrão visual. Os campos de senha possuem opção para mostrar ou ocultar o conteúdo digitado.

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
| `safeclick/db.py` | Conexão com o banco e registro das tentativas de simulação. |
| `safeclick/conteudos.py` e `safeclick/conteudos_db.py` | Páginas e consultas dos conteúdos educativos. |
| `safeclick/quizzes.py` | Exibição, correção e gravação dos quizzes. |
| `safeclick/simulacoes.py` | Cenário, escolhas e feedback da simulação. |
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

O modelo atual contém as configurações básicas do banco e da chave da aplicação. Acrescente as variáveis da Twilio e do cookie, conforme a estrutura abaixo:

```dotenv
DATABASE_URL="COLE_AQUI_A_CONEXAO_DO_NEON"
SECRET_KEY="COLE_AQUI_A_CHAVE_DA_APLICACAO"

TWILIO_ACCOUNT_SID="COLE_AQUI_O_ACCOUNT_SID"
TWILIO_AUTH_TOKEN="COLE_AQUI_O_AUTH_TOKEN"
TWILIO_VERIFY_SERVICE_SID="COLE_AQUI_O_SERVICE_SID"

SESSION_COOKIE_SECURE=false
```

Os textos acima são exemplos. Substitua-os pelos valores do ambiente utilizado pelo grupo.

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
2. `sql/adicionar_mfa_usuarios.sql`
3. `sql/criar_logins_pendentes.sql`
4. `sql/criar_controle_autenticacao.sql`
5. `criar_tentativas_simulacao.sql`
6. `sql/criar_conteudos.sql`
7. `sql/inserir_conteudos_iniciais.sql`
8. `sql/criar_quizzes.sql`
9. `sql/inserir_quizzes_iniciais.sql`
10. `sql/adicionar_token_tentativas.sql`
11. `sql/vincular_tentativas_usuarios.sql`

Se o banco já estiver preparado, confira quais scripts foram aplicados. Não repita indiscriminadamente os scripts de criação, alteração ou carga inicial.

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
| Simulação | [Abrir simulação](http://127.0.0.1:5000/simulacoes/conta-bloqueada) |
| Conteúdos | [Abrir conteúdos](http://127.0.0.1:5000/conteudos/) |
| Quizzes | [Abrir quizzes](http://127.0.0.1:5000/quizzes/) |

As páginas educativas exigem autenticação. A página inicial direciona para a simulação; usuários sem sessão são encaminhados ao login.

Mantenha o terminal aberto durante o uso. Para encerrar o servidor, pressione `Ctrl + C`.

## Funcionamento do login e da API externa
Documentação técnica e projeto lógico: [Integração com a API Twilio Verify](docs/integracao-twilio.md).

O fluxo principal é:

**E-mail e senha → código do autenticador → validação pela Twilio Verify → criação da sessão → página de simulação.**

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
5. Redirecionamento para a simulação após o login.
6. Acesso autenticado a conteúdos, quizzes e simulações.
7. Gravação das novas tentativas com `usuario_id`.
8. Encerramento da sessão e bloqueio do acesso direto às páginas protegidas.

Validações com falhas simuladas não substituem a conferência do ambiente final com Neon e Twilio.

## Pendências e limites desta etapa

- Recuperação de senha por e-mail adiada; serviço ainda não definido.
- Recuperação de acesso após perda do autenticador pendente.
- Integração da página administrativa de auditoria com o trabalho do grupo.
- Conferência e integração dos termos de uso e da política de privacidade na versão conjunta.
- Validação do ambiente publicado e das configurações de HTTPS.

## Integrantes

- Eduardo Mafra dos Santos
- Humberto Ribeiro Bezerra
- João Henrique Alves de Souza
