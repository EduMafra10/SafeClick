# Avaliações e progresso

## Estrutura e atualização

A aplicação mantém Flask, Jinja, Flask-Login, Flask-WTF/CSRF, psycopg/PostgreSQL, CSS próprio, Chart.js local e auditoria transacional. O ranking foi descontinuado: não há rotas, navegação, adesão, classificação ou publicação de pontuação. O progresso individual continua privado.

Em banco já preparado até a política 1.3, aplique:

1. `sql/remover_ranking.sql`: elimina apenas a tabela de preferências do recurso removido e atualiza o gatilho de exclusão de conta. Preserva avaliações, tentativas e a visão `resultados_validos_atividades`, utilizada pelo progresso privado.
2. `sql/registrar_politica_1_4_avaliacoes.sql`: registra a política 1.4, retira as referências à classificação pública e direciona o aviso para `/avaliacoes/privacidade`. As políticas anteriores e as referências legais permanecem arquivadas.
3. Reinicie o Flask. Para permitir novas avaliações e consulta pública, mantenha `AVALIACOES_ATIVAS=true`. O progresso, o aviso e os controles de retirada/exclusão da própria avaliação continuam disponíveis independentemente da coleta de novas avaliações.

Em um banco novo, siga toda a ordem de scripts do README. Migrações antigas são preservadas como histórico e devem ser seguidas pela migração de remoção. Não reaplique uma migração antiga isoladamente depois da retirada. O aviso das avaliações mantém a versão `participacao-2026-11-v1`: sua finalidade e suas opções não foram ampliadas. A política atual é a 1.4.

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

**Comentários e moderação** permite filtrar avaliações por situação. Cartões identificam a atividade, a conta pelo número interno, a nota, o comentário e o estado: aguardando moderação, publicado, publicação bloqueada ou privado. Os botões seguem a identidade visual da área administrativa, com destaque para revisão e ação secundária para bloqueio.

Somente comentários cuja publicação foi autorizada podem ser moderados. Revisão e bloqueio abrem uma página de confirmação com o texto completo, checkbox obrigatório, CSRF e número da revisão. Uma alteração concorrente impede confirmar uma versão antiga. Editar o texto público exige outra revisão. Bloquear retira somente o comentário da consulta pública, preservando a nota e o registro da avaliação.

O CSS `avaliacoes_admin.css` é carregado apenas nas páginas de avaliações da administração. Reutiliza cores e botões existentes, com navegação consistente, indicadores, estados vazios, paginação e adaptação para telas menores. A autorização permanece validada no servidor.

## Progresso privado

**Meu progresso** conserva gráficos e filtros de período, acrescentando:

- desempenho por modalidade: quizzes/Oficina, simulações e desafio de senhas;
- as vinte tentativas válidas mais recentes, com busca e filtro por tipo;
- sugestão de revisão quando a última tentativa de uma atividade fica abaixo de 70%;
- até três leituras ainda não concluídas, considerando todo o histórico de leitura.

Os novos resultados são recalculados e validados pela edição realizada. Tentativas incompletas, respostas inconsistentes, cartões repetidos da Oficina e partidas incompletas não entram no novo histórico. Os dados originais e os gráficos anteriores não são apagados. Resultados de atividades despublicadas permanecem no histórico privado. Administradores também têm progresso próprio; suas atividades continuam fora dos indicadores gerais.

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
