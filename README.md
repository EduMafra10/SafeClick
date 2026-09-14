# SafeClick — Quizzes interativos

Projeto de Conclusão de Curso de Sistemas de Informação da Universidade de Mogi das Cruzes (UMC).

Esta versão contém a funcionalidade de quizzes da primeira entrega. O projeto continua em desenvolvimento.

## Funcionalidade

- Dois quizzes: phishing e proteção de senhas.
- Cinco perguntas por quiz, com quatro alternativas e uma resposta correta.
- Validação e correção no Flask, com gabarito consultado no PostgreSQL.
- Tentativa e cinco respostas gravadas na mesma transação.
- Token de envio único para impedir tentativas duplicadas do mesmo formulário.
- Resultado com pontuação, escolhas e explicações educativas.
- CSS próprio seguindo o padrão visual do grupo.

As tentativas desta etapa não possuem vínculo com cadastro ou login. O resultado apresentado corresponde à última tentativa associada à sessão do navegador.

## Tecnologias

Python, Flask, Psycopg, PostgreSQL/Neon, Jinja2, HTML e CSS, sem ORM.

## Organização

```text
safeclick/
├── __init__.py                 # Inicialização e rota inicial
├── db.py                       # Conexão e verificação do banco
├── quizzes.py                  # Rotas, validação, correção e gravação
├── static/css/quizzes.css      # Estilo dos quizzes
└── templates/quizzes/
    ├── base.html
    ├── lista.html
    ├── responder.html
    └── resultado.html
sql/
├── criar_quizzes.sql
├── inserir_quizzes_iniciais.sql
├── adicionar_token_tentativas.sql
└── verificar_estrutura_quizzes.sql
```

## Executar no Windows

Na raiz do projeto, caso ainda não tenha um ambiente virtual:

```powershell
py -m venv .venv
```

Instale as dependências:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Configure o arquivo local `.env` com `DATABASE_URL` da branch Neon desejada e uma `SECRET_KEY` aleatória e estável. Não envie esse arquivo para o GitHub.

Para gerar a chave:

```powershell
.\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_hex(32))"
```

Em um banco novo, execute os scripts nesta ordem:

1. `sql/criar_quizzes.sql`
2. `sql/inserir_quizzes_iniciais.sql`
3. `sql/adicionar_token_tentativas.sql`

Use `sql/verificar_estrutura_quizzes.sql` para inspecionar a estrutura. Não execute novamente o script de criação em um banco que já contém essas tabelas.

Verifique a conexão e inicie o servidor:

```powershell
.\.venv\Scripts\python.exe -m flask --app safeclick verificar-banco
.\.venv\Scripts\python.exe -m flask --app safeclick run
```

Abra http://127.0.0.1:5000/ — a página inicial encaminha para `/quizzes/`.

## Revisão da entrega

Confira os dois quizzes, notas diferentes, rejeição de respostas inválidas e cinco respostas gravadas por tentativa. Atualizar o resultado não deve criar uma nova tentativa; “Tentar novamente” permite um novo envio.

Os scripts SQL são versionados pelo Git, mas precisam ser executados no banco de destino. Um merge não altera automaticamente a Neon.

As perguntas e o gabarito usados em tentativas devem permanecer estáveis até a implementação de um tratamento para versões do conteúdo.

## Integrantes

- Eduardo Mafra dos Santos
- Humberto Ribeiro Bezerra
- João Henrique Alves de Souza
