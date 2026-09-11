SafeClick — Aprenda antes de clicar

Projeto de Conclusão de Curso de Sistemas de Informação da Universidade de Mogi das Cruzes (UMC).

O SafeClick é uma plataforma web educativa voltada a estudantes do ensino médio e universitários. Seu objetivo é ajudar os usuários a reconhecer golpes digitais e adotar práticas mais seguras na internet.

Estado atual

O projeto está em desenvolvimento. A primeira entrega está organizada em três funcionalidades, cada uma sob responsabilidade de um integrante.

| Funcionalidade | Escopo da primeira entrega | Situação |
| --- | --- | --- |
| Conteúdos educativos | Listagem dos temas e páginas de leitura, com conteúdos consultados no PostgreSQL. Inicialmente: phishing e proteção de senhas. | Planejada; implementação ainda não iniciada. |
| Quizzes interativos | Dois quizzes de cinco questões, com perguntas, alternativas, pontuação e explicações. Consulta das questões e armazenamento das tentativas no PostgreSQL. | Planejada; implementação ainda não iniciada. |
| Simulações de golpes digitais | Cenário fictício de e-mail de conta bloqueada, com escolha de ação, consequências, explicações e registro da tentativa. | Em desenvolvimento, por Eduardo Mafra |

Até o momento, foi iniciada a estrutura da aplicação Flask e implementado o fluxo de apresentação e processamento das escolhas da primeira simulação.

A gravação das tentativas da simulação no PostgreSQL ainda está pendente. Nesta primeira entrega, elas serão registradas sem vínculo com usuário, conforme o planejamento do grupo.

Tecnologias utilizadas nesta etapa

- Python 3
- Flask
- Jinja2
- HTML5

Estrutura do projeto

```text
safeclick/
├── __init__.py
├── simulacoes.py
└── templates/
    └── simulacao.html
.gitignore
requirements.txt
README.md
```

- `__init__.py`: inicializa a aplicação e registra as rotas.
- `simulacoes.py`: define as alternativas e processa a escolha do visitante.
- `simulacao.html`: apresenta o cenário, o formulário e o resultado.
- `requirements.txt`: lista as dependências da aplicação.
- `.gitignore`: define os arquivos locais que não devem ser versionados.

Como executar no Windows

É necessário ter Python instalado. No PowerShell, abra a pasta do projeto e execute:

 1. Criar o ambiente virtual

```powershell
py -m venv .venv
```

2. Instalar as dependências

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

 3. Iniciar a aplicação

```powershell
.\.venv\Scripts\python.exe -m flask --app safeclick run --debug
```

Acesse http://127.0.0.1:5000/ no navegador.

Mantenha o servidor em execução durante o uso. Para encerrá-lo, pressione `Ctrl+C` no terminal. O modo de depuração é destinado ao desenvolvimento local.
Próximas etapas

- Verificar as três alternativas e o tratamento de escolhas inválidas.
- Integrar o PostgreSQL por meio do Psycopg.
- Registrar as tentativas e tratar falhas de gravação.

Integrantes

- Eduardo Mafra dos Santos
- Humberto Ribeiro Bezerra
- João Henrique Alves de Souza
