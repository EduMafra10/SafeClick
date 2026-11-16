# Avaliações públicas, progresso e ranking

## Arquitetura e ativação

A implementação usa os componentes existentes: Flask, Jinja, Flask-Login, Flask-WTF/CSRF, psycopg/PostgreSQL, auditoria transacional, limitador de tentativas, CSS próprio e Chart.js local. Não depende de serviço externo novo. Quizzes e Oficina continuam usando o catálogo versionado; atividades e gabaritos não são alterados por esta atualização.

No banco que já possui as migrações anteriores do README, execute nesta ordem:

1. `sql/adicionar_avaliacoes_publicas_ranking.sql`: amplia as duas tabelas de avaliação, cria `preferencias_ranking`, a visão `resultados_validos_atividades` e o gatilho de retirada/exclusão da participação.
2. `sql/registrar_politica_1_3_participacao.sql`: arquiva a política 1.3 a partir da 1.2, quando existente, ou da 1.1 em uma instalação nova. Copia as referências legais da versão de origem e preserva os documentos anteriores, inclusive as atualizações de exclusão de conta já registradas no Neon.
3. Mantenha `AVALIACOES_ATIVAS=true` para permitir novas avaliações e a consulta pública; reinicie o Flask. O padrão da configuração permanece desativado. Ranking e progresso são independentes dessa opção. Os controles de retirada e exclusão de avaliações continuam disponíveis se a coleta for desligada.

Os dois scripts podem ser reaplicados. As versões de aviso e política são `participacao-2026-11-v1` e `1.3`. Em uma próxima mudança de finalidade, publique outra versão e planeje a renovação das escolhas. Commit/push não executa migrações do Neon.

```powershell
.\.venv\Scripts\python.exe -m flask --app safeclick run
```

## Onde acessar

- **Conteúdos** e **Quizzes** têm link para avaliações públicas; nas atividades, o bloco recolhido **Avaliações desta atividade** carrega os dados ao abrir. Sem JavaScript, o link para a página completa continua disponível.
- `/avaliacoes/publicas`: busca por título, tipo, média e quantidade de notas autorizadas. `/avaliacoes/publicas/conteudo/<id>` e `/avaliacoes/publicas/quiz/<id>` mostram comentários aprovados, com paginação. A consulta não exige login.
- A pessoa conclui a própria leitura ou tentativa de quiz/Oficina antes de avaliar. O formulário conserva a nota de utilidade de 1 a 5, comentário opcional de até 500 caracteres, navegação seguinte e edição sem duplicidade.
- **Minha conta → Minhas avaliações** (`/avaliacoes/minhas`): editar quando publicado, retirar divulgação mantendo o registro privado ou excluir a própria avaliação. Atividades arquivadas também permitem retirada e exclusão.
- **Administração → Avaliações → Consultar comentários e moderar publicações**: resumo de todas as notas; lista de novas avaliações notificadas, filtros e revisão de comentários. Não expõe automaticamente comentários antigos. Moderação exige confirmação e revisão atual para evitar publicar texto alterado depois da leitura.
- **Meu progresso** (`/painel/`): gráficos anteriores preservados, período, melhores resultados no histórico completo, desempenho por modalidade, vinte tentativas recentes com busca/filtro, sugestões de revisão abaixo de 70% na última tentativa e três leituras ainda não concluídas. Histórico e recomendações por tentativa respeitam o período; leituras e pontuação total consideram todo o histórico, como indicado na tela. Administradores também têm progresso privado, sem entrar nos indicadores gerais nem no ranking.
- **Ranking** (`/ranking/`): classificação pública paginada. **Minha conta → Participação no ranking** (`/ranking/participacao`) permite adesão e retirada.

## Pontuação e validade

A pontuação de desempenho é separada da avaliação de utilidade. O ranking soma o **melhor percentual válido de cada atividade atualmente publicada**, com até **100 pontos por atividade**:

- Quiz tradicional e Oficina: `100 × acertos / questões`, arredondado a duas casas. Recalcula a correção pelas respostas da edição realizada. Exige todas as questões respondidas, alternativas pertencentes às questões, gabarito consistente e pontuação armazenada compatível. A Oficina não admite reutilizar o mesmo cartão. Versões de um mesmo item do catálogo contam como uma única atividade.
- Simulação: escolha segura vale 100; escolha de risco vale 0. Exige versão, cenário e alternativa correspondentes, com resultado de segurança conhecido.
- Desafio de senhas **Qual vazou mais?**: `100 × acertos / 5`; somente partidas completas de cinco rodadas com token registrado. O laboratório inteiro conta como uma atividade.
- Repetições não somam pontos. Conteúdos lidos, conquistas e notas de utilidade não pontuam. Registros incompletos ou inconsistentes não entram no ranking nem no novo histórico validado; o histórico original e os dados não são apagados.
- Itens removidos ou despublicados deixam a soma pública; seus resultados privados continuam no histórico. Publicar novas atividades pode ampliar a pontuação máxima disponível. Questões novas na mesma edição lógica não criam pontos adicionais.
- Ordem: maior soma; em empate, maior quantidade de atividades válidas diferentes. Persistindo igualdade, os participantes compartilham a posição. O pseudônimo ordena apenas a apresentação, sem desfazer o empate. Não há desempate por horário.
- Só contas de perfil `usuario`, ativas, com adesão atual, autodeclaração de maioridade e pelo menos uma atividade válida aparecem. Administradores ficam fora. Sair do ranking preserva o progresso; nova adesão gera outro pseudônimo.

## Privacidade e segurança

O padrão é privado. Divulgação de nota, de comentário e de pontuação são escolhas independentes da realização das atividades. O ranking utiliza pseudônimo aleatório gerado pelo servidor, sem apelido livre, nome ou e-mail. Os comentários públicos não mostram identificador do autor nem ligação com o ranking; a data exibida é apenas o dia. Pseudonimização não elimina o vínculo interno nem representa anonimização definitiva.

O aviso descreve consulta administrativa das novas avaliações para melhoria dos materiais. Comentários privados anteriores não são liberados à administração sem atualização notificada pelo titular. A lista administrativa usa somente número da conta como identificador de gestão. A equipe precisa validar a hipótese legal dessa consulta, a rotina de moderação e a informação de privacidade antes de disponibilizar a participantes reais.

A exposição pública exige declaração de 18 anos ou mais. É um limite conservador do produto, sem comprovação documental. Não amplia a idade mínima geral nem impede uso privado por quem tem 16 ou 17 anos conforme os Termos atuais. Eventual disponibilização pública a menores exige avaliação específica do melhor interesse e das exigências aplicáveis; não é resolvida somente por um checkbox.

Antes de aprovar um texto, o administrador deve conferir pertinência, respeito e ausência de dados pessoais, senhas, contatos e dados sensíveis, inclusive de terceiros. O sistema escapa HTML; não classifica automaticamente o significado de todos os textos. A equipe precisa garantir capacidade de moderação e atendimento ao canal de privacidade já documentado. Enquanto isso, é possível manter avaliações privadas.

As escritas usam sessão, autorização no servidor, CSRF, validação estrita de campos e limitação de alterações (avaliação: 20; preferência: 10 por janela de cinco minutos, por conta). Avaliações têm unicidade por conta e item no banco. Revisão numérica impede decisões de moderação sobre versões desatualizadas. Mudança de nota/opções, exclusão, retirada, moderação e adesão são auditadas na mesma transação, sem reproduzir nota, comentário, nome, e-mail ou pseudônimo no campo de detalhes.

Consultas públicas e pessoais enviam `Cache-Control: no-store`; páginas de participação também indicam `noindex, nofollow`. Isso não impede cópias feitas por terceiros. A retirada passa a valer nas novas consultas do sistema. Solicitação de exclusão da conta revoga a divulgação imediatamente; exclusão definitiva elimina avaliações e preferência do ranking. O histórico mínimo de auditoria segue a retenção já definida na política. A equipe deve confirmar prazos operacionais, backups, descarte e atendimento dos direitos dos titulares, inclusive a data de descarte das contas de teste já prevista na política.

Referências para essa validação: [direitos dos titulares — ANPD](https://www.gov.br/anpd/pt-br/assuntos/titular-de-dados-1/direito-dos-titulares) e [texto atualizado da LGPD — Câmara dos Deputados](https://www2.camara.leg.br/legin/fed/lei/2018/lei-13709-14-agosto-2018-787077-normaatualizada-pl.html). Os controles técnicos não certificam conformidade jurídica automática.

## Testes automatizados

```powershell
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
```

A suíte normal não se conecta ao Neon. `tests/test_participacao_rotas.py` cobre consulta sem login, proteção de páginas e moderação, CSRF, opt-in, adulteração de campos, retirada, limite de alterações, XSS e ausência de identificação pública. `tests/test_painel.py` cobre o painel e a preservação dos gráficos anteriores se falhar um indicador adicional.

`tests/test_participacao_postgres.py` executa SQL real somente em PostgreSQL **local**, banco dedicado e inicialmente vazio chamado `safeclick_participacao_test`. Sem a variável abaixo, os testes de integração são ignorados. Não use a URL do Neon ou o banco normal do site. Os testes criam e removem apenas as tabelas da própria fixture.

```powershell
$env:SAFECLICK_TEST_DATABASE_URL='postgresql://USUARIO_LOCAL@127.0.0.1:PORTA/safeclick_participacao_test'
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider tests/test_participacao_postgres.py
Remove-Item Env:SAFECLICK_TEST_DATABASE_URL
```

A integração cobre migração reaplicável, legado privado, UPSERT, revogação, moderação concorrente, rollback de auditoria, eliminação por exclusão de conta, fórmulas, tentativas inválidas, repetição, Oficina, versões, empate, despublicação, isolamento por usuário, filtro de período e arquivamento da política sem alterar a anterior.

Validação de 15/11/2026: suíte completa com o PostgreSQL local habilitado, **476 testes e 1.238 subtestes aprovados**. Os 32 avisos são de depreciação da API de escolhas do WTForms; não houve falhas. Também passaram `python -m compileall -q safeclick`, `node --check safeclick/static/js/participacao.js`, `node --check safeclick/static/js/painel.js` e `git diff --check`. As consultas HTTP públicas foram verificadas com a conexão configurada do Neon, preservando as seis avaliações existentes como privadas e sem criar adesões reais ao ranking. A captura desktop do ranking foi conferida com dados fictícios; a inspeção visual completa em celular permanece no roteiro manual.

## Verificação manual

1. Entre com conta de teste, conclua uma leitura e um quiz. Envie avaliações privadas e confira o resumo administrativo. Atualize a mesma avaliação e confira que a quantidade não aumentou.
2. Leia o aviso, autorize a nota e envie comentário para moderação. Em sessão sem login, confira que somente a nota está pública. Como administrador, revise e aprove; confirme o comentário público sem identificador. Edite o texto e confirme que volta a aguardar revisão.
3. Retire a publicação em **Minhas avaliações**, inclusive após despublicar o item; confira que continua privada e desaparece da consulta pública. Exclua outra avaliação e confira a auditoria.
4. Com usuário comum, tente acessar diretamente a moderação: deve retornar 403. Sem login, controles de escrita devem solicitar autenticação. Não envie dados pessoais reais nos textos de teste.
5. Faça quiz, Oficina, simulação e desafio de senhas. Abra o progresso, teste períodos e filtros, confira sugestões e resultados. Entre no ranking com conta comum e autodeclaração; repita um resultado e confirme que não ganhou pontos adicionais. Saia e confirme que o histórico privado permanece.
6. Confira visualização móvel, navegação por teclado, estados sem dados, erro/repetição e a Política de Privacidade 1.3. Valide as decisões de privacidade e as regras de classificação com a equipe/orientador.
