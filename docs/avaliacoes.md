# Avaliar conteúdos e quizzes

O RF17 registra uma nota de utilidade de 1 a 5 e um comentário opcional de até 500 caracteres. Após concluir uma leitura ou uma tentativa de quiz, a conta pode abrir o formulário, enviar e atualizar sua avaliação.

## Ativação em teste

1. Confirme que a conexão aponta para um PostgreSQL de teste. Aplique `sql/criar_avaliacoes.sql` após as migrações de conclusões e de catálogo.
2. Defina `AVALIACOES_ATIVAS=true` no ambiente de teste e reinicie a aplicação. O padrão é `false`.
3. Com uma conta fictícia, marque um conteúdo como concluído e abra **Avaliar conteúdo**. Envie a nota e depois altere-a. Termine um quiz e repita pelo botão **Avaliar quiz**.
4. Abra **Gestão de conteúdo → Avaliações** com um administrador. Confira se a média e a quantidade aparecem para as atividades avaliadas.

## Dados e regras

- A identidade vem da sessão. A aplicação exige a conclusão pela própria conta e o estado publicado antes de aceitar a avaliação.
- Cada envio válido grava a avaliação e o evento `avaliacao.salva` na mesma transação. O evento registra a conta, o tipo de atividade, o resultado e a data. A nota, o comentário e o vínculo com o item ficam na tabela de avaliações. O administrador pode localizar o evento **Avaliação salva** em **Logs de auditoria**, na categoria **Aprendizado**.
- Quizzes tradicionais e atividades da Oficina usam a mesma regra. A avaliação pertence ao item estável do catálogo. Uma tentativa completa em versão anterior habilita avaliar o mesmo item quando publicado, sem criar uma avaliação adicional.
- O painel administrativo apresenta média e quantidade por atividade publicada a partir da primeira avaliação. Com uma única avaliação, a média corresponde à nota enviada. Os demais itens aparecem como **Sem avaliações**.
- O comentário fica disponível para edição pela própria conta e pode ser limpo deixando o campo vazio. As avaliações saem com a conta por chaves estrangeiras em cascata. No caso de conteúdo, a cascata passa pelo registro de conclusão. A rotina de exclusão da conta também precisa tratar dependências já existentes, como as tentativas de quiz, na mesma transação.

Antes de habilitar para participantes reais, valide com a equipe a hipótese legal, o procedimento de acesso e descarte de comentários, os pedidos pelo canal de privacidade e a atualização da política vigente. A migração cria as tabelas. A coleta começa quando a opção de configuração é habilitada e alguém envia uma avaliação.
