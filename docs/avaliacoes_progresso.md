# Avaliações e progresso

## Estrutura e atualização

A aplicação mantém Flask, Jinja, Flask-Login, Flask-WTF/CSRF, psycopg/PostgreSQL, CSS próprio, Chart.js local e auditoria transacional. O ranking foi descontinuado: não há rotas, navegação, adesão, classificação ou publicação de pontuação. O progresso individual continua privado.

Em banco já preparado até a política 1.3, aplique:

1. `sql/remover_ranking.sql`: elimina apenas a tabela de preferências do recurso removido e atualiza o gatilho de exclusão de conta. Preserva avaliações, tentativas e a visão `resultados_validos_atividades`, utilizada pelo progresso privado.
2. `sql/registrar_politica_1_4_avaliacoes.sql`: registra a política 1.4, retira as referências à classificação pública e direciona o aviso para `/avaliacoes/privacidade`. As políticas anteriores e as referências legais permanecem arquivadas.
3. Execute `sql/registrar_politica_1_5_termos_1_1.sql` para disponibilizar a política 1.5 e os termos 1.1 esperados pelo site.
4. Reinicie o Flask. Para permitir novas avaliações e consulta pública, mantenha `AVALIACOES_ATIVAS=true`. O progresso, o aviso e os controles de retirada/exclusão da própria avaliação continuam disponíveis independentemente da coleta de novas avaliações.

Em um banco novo, siga toda a ordem de scripts do README. O aviso de compartilhamento de avaliações permanece na versão `participacao-2026-11-v1`.

```powershell
.\.venv\Scripts\python.exe -m flask --app safeclick run
```

## Avaliações

- Cada conta avalia a utilidade de uma leitura concluída ou de um quiz/Oficina respondido, com nota de 1 a 5 e comentário opcional de até 500 caracteres. A identidade vem da sessão. A unicidade por conta e item é garantida no PostgreSQL.
- A conta pode editar a avaliação sem duplicá-la. Publicar a nota e submeter o comentário à moderação são escolhas separadas e desmarcadas por padrão, limitadas a maiores de 18 anos por autodeclaração. A declaração não representa comprovação documental de idade. Quem não compartilha continua usando os recursos privados.
- `/avaliacoes/publicas` oferece consulta sem login, busca, filtros e paginação. As atividades mostram um componente recolhido que carrega as avaliações ao abrir, com link de acesso mesmo sem JavaScript.
- O público vê somente notas autorizadas e comentários aprovados de atividades publicadas. Não recebe nome, e-mail ou número da conta do autor. Textos são escapados na renderização para evitar execução de HTML fornecido pelo usuário.
- **Minha conta → Minhas avaliações** permite editar quando publicado, retirar divulgação mantendo o registro privado ou excluir. Retirada e exclusão também funcionam se o item for despublicado ou se a coleta de avaliações estiver desligada.
- `/avaliacoes/privacidade` informa finalidade, consulta administrativa, publicação, moderação, retirada e exclusão. Nenhuma avaliação anterior é divulgada automaticamente. Comentários antigos permanecem privados até atualização notificada pelo autor.

## Painel administrativo

Em **Administração → Avaliações**, o resumo apresenta atividades publicadas, atividades avaliadas, quantidade de respostas e médias desde a primeira avaliação. Inclui notas privadas; a consulta pública considera apenas as notas autorizadas.

As barras de distribuição mostram a quantidade de notas de 1 a 5 no resumo
administrativo e no detalhe público da atividade. Cada consulta usa a mesma
seleção de avaliações de sua média; notas privadas não entram nas barras públicas.
As barras têm rótulos acessíveis e não alteram o cálculo da média.

Quando há comentários autorizados aguardando aprovação, um ícone de comentário com relógio aparece
ao lado de **Avaliações** no menu e o botão **Comentários e moderação** recebe
destaque. A verificação ocorre ao abrir a página, ao retornar a ela e a cada
30 segundos enquanto estiver visível. O ícone leva à lista de pendentes. O
endpoint `/administracao/avaliacoes/pendentes` exige administrador, retorna apenas
a quantidade e não mantém cache. Não há envio de e-mail ou notificação externa.

**Comentários e moderação** permite filtrar avaliações por situação. Cartões identificam a atividade, a conta pelo número interno, a nota, o comentário e o estado: aguardando moderação, publicado, publicação bloqueada ou privado. Os botões seguem a identidade visual da área administrativa, com destaque para revisão e ação secundária para bloqueio.

Somente comentários cuja publicação foi autorizada podem ser moderados. Revisão e bloqueio abrem uma página de confirmação com o texto completo, checkbox obrigatório, CSRF e número da revisão. Uma alteração concorrente impede confirmar uma versão antiga. Editar o texto público exige outra revisão. Bloquear retira somente o comentário da consulta pública, preservando a nota e o registro da avaliação.

A confirmação inclui uma prévia que reutiliza o componente do cartão público,
com nota, data e comentário, sem dados do perfil no cabeçalho. A conta autora
é identificada separadamente apenas na área administrativa. Abrir essa revisão
e confirmar sua decisão são eventos distintos na auditoria. O atalho **Auditoria
de avaliações** reúne também os registros de criação, edição, retirada e exclusão.
Não é necessária migração adicional de banco para as barras, a prévia ou os avisos.

Avaliações anteriores sem autorização de divulgação, aviso vigente e declaração
de idade continuam privadas. O administrador pode moderar comentários já
autorizados, mas a moderação não preenche essas escolhas pelo participante.
O próprio autor pode renovar suas escolhas em **Minha conta → Minhas avaliações**,
editando a avaliação de uma atividade que continue publicada.

## Atualização da Visão geral

Os indicadores da administração são consultados ao abrir a página e novamente a
cada 10 segundos enquanto a aba estiver visível. Há botão **Atualizar agora** e
horário da última consulta bem-sucedida em Brasília. Ao voltar à aba ou recuperar
a conexão, a página solicita dados novamente. Falhas mantêm o último painel e
exibem um aviso; o horário anterior não é apresentado como atualizado.

`GET /administracao/visao-geral/dados` exige perfil administrador, valida o período
e retorna somente o fragmento do painel e o horário, sem cache. Uma transação
PostgreSQL `REPEATABLE READ, READ ONLY` mantém os indicadores e as médias de
avaliações no mesmo snapshot. O gráfico é atualizado junto com os cartões e
tabelas, preservando o filtro e o foco dos links. Sem JavaScript, é necessário
recarregar a página. Trata-se de atualização periódica, não de transmissão
instantânea de cada evento. Dados ainda não confirmados no banco só entram numa
consulta posterior à confirmação.

As consultas automáticas de indicadores e de pendências validam a sessão sem
renovar o prazo de inatividade. O clique em **Atualizar agora** sinaliza uma
interação manual e renova somente uma sessão que ainda esteja válida. Permanecem
as verificações de autenticador, conta ativa, inatividade e expiração máxima.

A contagem de usuários ativos exclui contas excluídas ou com exclusão solicitada,
assim como o total de usuários cadastrados. O indicador de atividades com nota
abaixo de 3 considera todas as atividades avaliadas; a tabela de menores médias
continua limitada às cinco primeiras. A exportação Excel consulta os mesmos
indicadores em um snapshot novo. Consultas automáticas não criam eventos de
auditoria repetitivos; a exportação permanece auditada.

O CSS `avaliacoes_admin.css` é carregado apenas nas páginas de avaliações da administração. Reutiliza cores e botões existentes, com navegação consistente, indicadores, estados vazios, paginação e adaptação para telas menores. A autorização permanece validada no servidor.

## Progresso privado

**Meu progresso** conserva gráficos e filtros de período, acrescentando:

- desempenho por modalidade: quizzes/Oficina, simulações e desafio de senhas;
- sugestão de revisão quando a última tentativa de uma atividade fica abaixo de 70%;
- até três leituras ainda não concluídas, considerando todo o histórico de leitura.

Os resultados são recalculados e validados pela edição realizada. Tentativas incompletas, respostas inconsistentes, cartões repetidos da Oficina e partidas incompletas não entram nos indicadores adicionais. A seção de histórico recente e seus filtros locais foram retirados da dashboard, junto com a consulta usada apenas nessa listagem. Os dados originais, os gráficos, os filtros de período, as conquistas e as sugestões de revisão são preservados. Resultados de atividades despublicadas continuam armazenados e compondo os indicadores privados. Administradores também têm progresso próprio; suas atividades continuam fora dos indicadores gerais.

Os botões de conteúdos, quizzes, avaliações e progresso compartilham o padrão em `visual_base.css`: ação principal escura, secundária com contorno e foco visível. Links de ação nas avaliações e nas sugestões do painel usam esses componentes; links no meio dos textos mantêm aparência de link. A atualização é apenas da interface e da consulta do painel, sem migração de banco.

## Privacidade e segurança

Avaliações mantêm as proteções existentes: sessão, autorização, CSRF, validação de campos, limite de alterações por conta, concorrência e auditoria na mesma transação. O log não copia o texto do comentário ou a nota para os detalhes do evento. A conta é conferida e bloqueada para leitura durante o salvamento, impedindo novo envio depois de desativação concorrente.

A consulta administrativa de novas avaliações é informada no formulário. A equipe deve validar sua hipótese legal, os procedimentos de moderação, retenção, backups e atendimento ao canal de privacidade. A moderação deve conferir pertinência, respeito e ausência de dados pessoais, senhas, contatos ou dados sensíveis, inclusive de terceiros. O sistema não classifica automaticamente todo o significado dos textos nem certifica conformidade jurídica automática.

Solicitar exclusão da conta retira a divulgação das avaliações imediatamente; concluir a exclusão elimina as avaliações. O histórico mínimo de auditoria e as versões dos documentos anteriores são preservados conforme as regras do projeto. Consultas públicas e pessoais usam `Cache-Control: no-store`; a retirada vale nas consultas seguintes, sem controle sobre cópias realizadas por terceiros.

## Validação

```powershell
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
.\.venv\Scripts\python.exe -m compileall -q safeclick
node --check safeclick/static/js/participacao.js
git diff --check
```

A suíte normal não usa o Neon. Para executar `tests/test_participacao_postgres.py`, configure `SAFECLICK_TEST_DATABASE_URL` com um PostgreSQL local e um banco dedicado inicialmente vazio chamado `safeclick_participacao_test`. A fixture recusa a conexão normal do site. Sem essa variável, os testes de integração são ignorados. Eles cobrem avaliações, moderação, exclusão, migrações reaplicáveis, preservação dos dados, retirada do ranking, políticas arquivadas e histórico privado válido.

Verifique manualmente o resumo, os filtros, os cartões, a confirmação de revisão/bloqueio, a consulta pública e a navegação por teclado. Com usuário comum, acessar a moderação deve retornar 403; rotas antigas `/ranking/`, `/ranking/participacao` e `/ranking/privacidade` devem retornar 404, inclusive para administradores. Confira o layout em computador e celular após reiniciar o servidor.
