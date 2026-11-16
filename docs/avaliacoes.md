# Avaliar conteúdos e quizzes

O RF17 registra uma nota de utilidade de 1 a 5 e um comentário opcional de até 500 caracteres. Após concluir uma leitura ou uma tentativa de quiz, a conta pode abrir o formulário, enviar e atualizar sua avaliação.

## Ativação em teste

1. Confirme que a conexão aponta para um PostgreSQL de teste. Siga a ordem de migrações do README, incluindo as tabelas de avaliações, `sql/remover_ranking.sql` e a política 1.4. Em um banco já atualizado até a política 1.3, aplique apenas a remoção do recurso descontinuado e `sql/registrar_politica_1_4_avaliacoes.sql`.
2. Defina `AVALIACOES_ATIVAS=true` no ambiente de teste e reinicie a aplicação. O padrão é `false`.
3. Com uma conta fictícia, marque um conteúdo como concluído e abra **Avaliar conteúdo**. Envie a nota e depois altere-a. Termine um quiz e repita pelo botão **Avaliar quiz**.
4. Abra **Gestão de conteúdo → Avaliações** com um administrador. Confira se a média e a quantidade aparecem para as atividades avaliadas.

## Dados e regras

- A identidade vem da sessão. A aplicação exige a conclusão pela própria conta e o estado publicado antes de aceitar a avaliação.
- Cada envio válido grava a avaliação e o evento `avaliacao.salva` na mesma transação. O evento registra a conta, o tipo de atividade, o resultado e a data. A nota, o comentário e o vínculo com o item ficam na tabela de avaliações. O administrador pode localizar o evento **Avaliação salva** em **Logs de auditoria**, na categoria **Aprendizado**.
- Quizzes tradicionais e atividades da Oficina usam a mesma regra. A avaliação pertence ao item estável do catálogo. Uma tentativa completa em versão anterior habilita avaliar o mesmo item quando publicado, sem criar uma avaliação adicional.
- O painel administrativo apresenta média e quantidade por atividade publicada a partir da primeira avaliação. Com uma única avaliação, a média corresponde à nota enviada. Os demais itens aparecem como **Sem avaliações**.
- O comentário fica disponível para edição pela própria conta e pode ser limpo deixando o campo vazio. A pessoa pode excluir sua avaliação ou retirar somente a divulgação em **Minhas avaliações**, inclusive se a atividade for despublicada ou a configuração de novas avaliações for desligada.
- Nenhuma avaliação anterior é publicada automaticamente. O novo formulário informa a consulta administrativa de novas avaliações; comentários anteriores permanecem privados até atualização pelo autor. O administrador continua vendo o resumo agregado de notas antigas.
- Publicar a nota na média e enviar o comentário à moderação são escolhas separadas, desmarcadas por padrão. Compartilhar exige declaração de 18 anos ou mais e versão atual do aviso. Menores continuam podendo avaliar de forma privada.
- O público consulta apenas notas autorizadas e comentários aprovados de atividades publicadas. Não recebe nome, e-mail ou ID do autor. O texto é escapado na renderização, nunca tratado como HTML fornecido pelo usuário.
- A moderação exige perfil administrador, CSRF, confirmação e revisão atual do registro. Alterar o texto público exige nova revisão. Atualização, retirada, exclusão e moderação são registradas na auditoria sem copiar o comentário ou a nota para o log.
- A solicitação de exclusão da conta retira a participação pública imediatamente. A exclusão definitiva elimina avaliações e preferências pelo gatilho da nova migração, preservando o tratamento já existente do histórico e da auditoria.

Antes de habilitar para participantes reais, valide com a equipe a hipótese legal, o procedimento de acesso e descarte de comentários, os pedidos pelo canal de privacidade e a atualização da política vigente. A migração cria as tabelas. A coleta começa quando a opção de configuração é habilitada e alguém envia uma avaliação.

Rotas e roteiro completo de verificação: [avaliações e progresso](avaliacoes_progresso.md).
