`markdown
# SafeClick — Aprenda antes de clicar

Projeto de Conclusão de Curso de Sistemas de Informação da Universidade de Mogi das Cruzes (UMC).

O SafeClick é uma plataforma web educativa voltada a estudantes do ensino médio e universitários. Seu objetivo é ajudar os visitantes a reconhecer golpes digitais e adotar práticas mais seguras na internet.

## Funcionalidades

- **Conteúdos educativos:** listagem de temas e páginas de leitura sobre phishing e proteção de senhas, consultadas no PostgreSQL.
- **Quizzes interativos:** dois quizzes com cinco perguntas, quatro alternativas por pergunta e uma resposta correta. O servidor consulta o gabarito, calcula a pontuação e salva a tentativa e suas cinco respostas na mesma transação. O resultado apresenta escolhas e explicações.
- **Simulações de golpes digitais:** e-mail fictício de conta bloqueada, com três alternativas, consequências, explicações e sinais de risco. Cada envio válido registra a simulação, a escolha e a data e hora.

As páginas utilizam HTML, Jinja2 e CSS, seguindo o padrão visual do grupo.

## Tecnologias

Python, Flask, Jinja2, HTML, CSS, PostgreSQL hospedado no Neon e Psycopg 3, sem ORM.

As dependências estão em `requirements.txt`. O extra `Flask[dotenv]` permite carregar o arquivo local `.env` ao executar pela CLI do Flask.

## Organização

- `safeclick/__init__.py`: cria a aplicação, carrega as configurações e registra as três funcionalidades.
- `safeclick/db.py`: conexão com o banco, gravação das tentativas da simulação e comando de verificação.
- `safeclick/simulacoes.py`: cenário, validação das escolhas e feedback da simulação.
- `safeclick/conteudos.py` e `safeclick/conteudos_db.py`: páginas de leitura e consultas dos conteúdos.
- `safeclick/quizzes.py`: perguntas, validação, correção e gravação dos quizzes.
- `safeclick/templates/`: páginas HTML.
- `safeclick/static/css/`: estilos das funcionalidades.
- `criar_tentativas_simulacao.sql` e `sql/`: scripts de preparação do banco.
- `.env.example`: modelo de configuração, sem credenciais.

## Executar no Windows

Abra o PowerShell na pasta principal do projeto, onde está o arquivo `requirements.txt`.

### 1. Preparar o ambiente

Se ainda não existir um ambiente virtual:

powershell
py -m venv .venv


Instale as dependências:

powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt


### 2. Configurar o arquivo local

Crie o `.env` somente se ele ainda não existir:

powershell
if (-not (Test-Path -LiteralPath .env)) {
    Copy-Item -LiteralPath .env.example -Destination .env
}


Preencha as duas configurações, substituindo os textos de exemplo:

dotenv
DATABASE_URL="COLE_AQUI_A_CONEXAO_DO_NEON"
SECRET_KEY="COLE_AQUI_UMA_CHAVE_ALEATORIA"


Obtenha a conexão pelo botão Connect do Neon, selecionando o projeto, a branch e o banco usados pelo grupo. Mantenha os parâmetros fornecidos na conexão.

Se ainda não tiver uma SECRET_KEY, gere uma:

powershell
.\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_hex(32))"


Copie o resultado para a SECRET_KEY do seu `.env` e mantenha essa chave entre as execuções. Ela é necessária para a sessão dos quizzes.

Cada integrante configura seu arquivo local. O `.env` e a pasta `.venv` são ignorados pelo Git; o `.env.example` deve permanecer sem valores reais.

### 3. Preparar o banco, quando necessário

Em um banco novo, execute o conteúdo destes arquivos no SQL Editor do Neon, nesta ordem:

1. `criar_tentativas_simulacao.sql`
2. `sql/criar_conteudos.sql`
3. `sql/inserir_conteudos_iniciais.sql`
4. `sql/criar_quizzes.sql`
5. `sql/inserir_quizzes_iniciais.sql`
6. `sql/adicionar_token_tentativas.sql`

Se o banco já estiver preparado, confira o que existe antes de executar os scripts. Não repita os scripts de criação da simulação e dos quizzes sobre tabelas existentes. Use `sql/verificar_estrutura_quizzes.sql` para inspecionar a estrutura dos quizzes.

O script de token adiciona a coluna e o índice usados para impedir a gravação duplicada do mesmo formulário de quiz.

Um merge no Git não executa scripts no Neon. Integrantes conectados ao mesmo banco e à mesma branch do Neon compartilham os dados, mesmo trabalhando em branches Git diferentes.

### 4. Verificar a conexão

powershell
.\.venv\Scripts\python.exe -m flask --app safeclick verificar-banco


Esse comando verifica o acesso ao banco; ele não confirma que todas as tabelas e os dados iniciais estão preparados.

### 5. Iniciar a aplicação

powershell
.\.venv\Scripts\python.exe -m flask --app safeclick run


Abra os endereços:

- Simulação: http://127.0.0.1:5000/simulacoes/conta-bloqueada
- Conteúdos: http://127.0.0.1:5000/conteudos/
- Quizzes: http://127.0.0.1:5000/quizzes/

A página inicial http://127.0.0.1:5000/ redireciona para a simulação.

Mantenha o terminal aberto durante o uso. Para encerrar o servidor, pressione Ctrl+C.

## Comportamentos e limites desta etapa

- As tentativas não possuem vínculo com cadastro ou login. O identificador de uma tentativa não representa um usuário.
- Na simulação, escolhas ausentes ou inválidas retornam HTTP 400 sem gravação. Uma falha ao confirmar o registro retorna HTTP 503 com um aviso.
- Após gravar a simulação, o servidor redireciona com HTTP 303. Atualizar a página do resultado não grava outra tentativa; enviar o formulário novamente pode registrar uma nova tentativa.
- O parâmetro resultado da URL apenas seleciona o feedback educativo. Abrir essa URL diretamente não registra nem comprova uma tentativa.
- O e-mail da simulação é fictício e sua chamada para confirmar dados não abre uma página externa.
- Nos quizzes, um token identifica o envio do formulário. O resultado corresponde à última tentativa associada à sessão do navegador; tentar novamente permite um novo envio.
- Perguntas e gabaritos usados em tentativas devem permanecer estáveis até existir um tratamento para versões do conteúdo.
- Datas das tentativas usam TIMESTAMPTZ. A exibição do horário depende do fuso usado na consulta.

## Verificação da integração

Na simulação, já foram conferidos os três resultados e registros no Neon, a rejeição de escolhas ausentes ou inválidas e a atualização da página sem nova gravação. A resposta HTTP 503 foi verificada com falha simulada por mock. O layout da simulação foi conferido entre 320 e 1440 pixels e com navegação por teclado.

Após integrar alterações, conferir:

- A abertura das três funcionalidades.
- A listagem dos dois temas e suas páginas de leitura.
- Os dois quizzes, pontuações diferentes e explicações.
- Uma tentativa e cinco respostas gravadas por envio válido de quiz.
- A rejeição de respostas inválidas e o comportamento de reenvio do mesmo formulário.
- A gravação da simulação e a atualização do resultado sem nova tentativa.

A versão para avaliação é reunida na branch `entrega1409`. Cada integrante demonstra a funcionalidade que desenvolveu em seu próprio vídeo.

## Integrantes

- Eduardo Mafra dos Santos
- Humberto Ribeiro Bezerra
- João Henrique Alves de Souza
`