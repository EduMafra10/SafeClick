# SafeClick — Aprenda antes de clicar

Projeto de Conclusão de Curso de Sistemas de Informação da Universidade de Mogi das Cruzes (UMC).

O SafeClick é uma plataforma web educativa voltada a estudantes do ensino médio e universitários. Seu objetivo é ajudar os visitantes a reconhecer golpes digitais e adotar práticas mais seguras na internet.

## Funcionalidades da primeira entrega

O trabalho está dividido entre os três integrantes:

| Funcionalidade | Escopo planejado |
| --- | --- |
| Conteúdos educativos | Listagem de temas e páginas de leitura, com conteúdos consultados no PostgreSQL. Temas iniciais: phishing e proteção de senhas. |
| Quizzes interativos | Dois quizzes de cinco questões, com alternativas, pontuação e explicações. Consulta das questões e armazenamento das tentativas no PostgreSQL. |
| Simulações de golpes digitais | E-mail fictício de conta bloqueada, com três escolhas, consequências, explicações educativas e registro das tentativas. |

O estado descrito a seguir corresponde à funcionalidade de simulações. As funcionalidades dos outros integrantes serão documentadas conforme sua integração ao projeto.

## Estado atual da simulação

A versão básica permite:

- Ler um e-mail fictício de conta bloqueada e escolher entre três alternativas.
- Receber a consequência da escolha, uma explicação educativa e os sinais de risco do cenário.
- Registrar no PostgreSQL a identificação da simulação, a alternativa escolhida e a data e hora da tentativa.
- Rejeitar alternativas ausentes ou inválidas, retornando HTTP 400 sem gravar uma tentativa.
- Exibir um aviso e retornar HTTP 503 quando não for possível confirmar a gravação.
- Redirecionar após uma gravação bem-sucedida, evitando reenviar o formulário ao atualizar a página do resultado.

As tentativas são registradas sem vínculo com usuário nesta etapa. O campo `criada_em` usa `TIMESTAMPTZ`; o horário exibido pode variar conforme o fuso da sessão que consulta o banco.

O e-mail é fictício. A chamada “CONFIRMAR MEUS DADOS” não possui link para uma página externa, e o formulário solicita apenas a alternativa escolhida.

## Tecnologias utilizadas

- Python 3
- Flask e Jinja2
- HTML5
- PostgreSQL hospedado no Neon
- Psycopg 3 para comunicação com o banco
- python-dotenv, instalado pelo extra `Flask[dotenv]`, para carregar a configuração local ao executar pela CLI do Flask

As versões das dependências estão registradas em `requirements.txt`.

## Estrutura do projeto

```text
safeclick/
├── __init__.py
├── db.py
├── simulacoes.py
└── templates/
    └── simulacao.html
.env.example
.gitignore
criar_tentativas_simulacao.sql
requirements.txt
README.md
```

- `__init__.py`: cria a aplicação, carrega a configuração do banco e registra o Blueprint e o comando de verificação.
- `db.py`: abre a conexão, salva as tentativas e disponibiliza o comando `verificar-banco`.
- `simulacoes.py`: define as alternativas, valida as escolhas e controla a apresentação do resultado.
- `simulacao.html`: apresenta o cenário, o formulário, os resultados e os avisos de erro.
- `criar_tentativas_simulacao.sql`: cria a tabela usada pela simulação em um banco ainda não preparado.
- `.env.example`: modelo de configuração, sem credenciais.
- `.gitignore`: exclui do versionamento arquivos locais, incluindo `.env` e `.venv`.

## Como executar no Windows

É necessário ter Python instalado e acesso a um banco PostgreSQL. Após clonar o repositório e selecionar a branch que deseja executar, abra o PowerShell na pasta do projeto.

### 1. Criar o ambiente virtual

Na primeira configuração:

```powershell
py -m venv .venv
```

### 2. Instalar as dependências

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 3. Configurar a conexão

Se ainda não houver um `.env` local, crie-o a partir do modelo:

```powershell
if (-not (Test-Path -LiteralPath .env)) {
    Copy-Item -LiteralPath .env.example -Destination .env
}
```

No Neon, abra o projeto ao qual você tem acesso e use **Connect** para copiar a string de conexão do banco escolhido. No `.env`, preencha:

```dotenv
DATABASE_URL="COLE_AQUI_A_STRING_DE_CONEXAO_DO_NEON"
```

Substitua o texto de exemplo pela conexão completa, mantendo os parâmetros de segurança fornecidos pelo Neon. O `.env` fica apenas no computador e não deve ser enviado ao GitHub. O `.env.example` deve permanecer sem credenciais.

Cada integrante configura seu próprio arquivo local. Se todos usarem o mesmo banco e branch do Neon, compartilharão as tabelas e os dados, independentemente da branch Git em que estiverem trabalhando.

### 4. Preparar a tabela, se necessário

Em um banco novo, abra o **SQL Editor** do Neon, selecione o banco e a branch correspondentes à conexão configurada e execute o conteúdo de `criar_tentativas_simulacao.sql`.

Se `public.tentativas_simulacao` já existir, essa etapa já foi realizada. O script atual usa `CREATE TABLE` e não deve ser executado novamente sobre a tabela existente. Versionar o arquivo SQL no Git não executa o comando automaticamente no banco.

### 5. Verificar a conexão

```powershell
.\.venv\Scripts\python.exe -m flask --app safeclick verificar-banco
```

O comando deve informar que a conexão foi realizada com sucesso e exibir o nome do banco. Ele verifica o acesso ao banco; a criação da tabela é feita na etapa anterior.

### 6. Iniciar a aplicação

```powershell
.\.venv\Scripts\python.exe -m flask --app safeclick run --debug
```

Acesse [a aplicação local](http://127.0.0.1:5000/). A página inicial redireciona para `/simulacoes/conta-bloqueada`.

Mantenha o servidor em execução durante o uso. Para encerrá-lo, pressione `Ctrl+C`. O modo de depuração é destinado ao desenvolvimento local.

## Fluxo de uma tentativa

1. Um GET apresenta a página da simulação.
2. O formulário envia a escolha por POST.
3. O servidor valida a alternativa usando o dicionário `OPCOES`.
4. Uma escolha válida é gravada por uma consulta SQL parametrizada. A conexão confirma a transação ao sair normalmente do bloco `with`.
5. Após o sucesso da gravação, a rota responde com HTTP 303 e redireciona para um GET com o parâmetro `resultado`.
6. O GET apresenta o feedback sem executar uma nova gravação.

O parâmetro `resultado` seleciona o texto educativo a exibir; abrir essa URL diretamente não registra nem comprova uma tentativa. Um novo envio do formulário continua sendo uma nova tentativa. O redirecionamento trata a atualização da página após sucesso, não todos os possíveis envios duplicados.

## Verificações realizadas

- As três alternativas foram testadas manualmente, com conferência dos resultados e dos registros no Neon.
- Envios com alternativa ausente ou inválida retornaram HTTP 400, sem acrescentar registros.
- Uma falha de gravação foi simulada com um mock: a aplicação retornou HTTP 503 e exibiu o aviso esperado. Esse teste não representa uma indisponibilidade real do Neon.
- Após um envio bem-sucedido, a página do resultado foi atualizada e a contagem no banco permaneceu igual.

Para conferir o total de tentativas da simulação no SQL Editor:

```sql
SELECT COUNT(*) AS total
FROM public.tentativas_simulacao
WHERE simulacao = 'conta_bloqueada';
```

## Próximos passos

- Aplicar e revisar a estilização da página da simulação.
- Integrar as funcionalidades desenvolvidas pelos demais integrantes.
- Conferir a versão integrada e preparar a branch `entrega1409` para avaliação.

## Integrantes

- Eduardo Mafra dos Santos
- Humberto Ribeiro Bezerra
- João Henrique Alves de Souza
