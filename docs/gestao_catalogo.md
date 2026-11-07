# Gestão de conteúdo do SafeClick

O menu **Minha conta → Gestão de conteúdo** abre a rota `/administracao/`. A área usa o perfil `administrador` do SafeClick, a sessão existente e formulários protegidos por CSRF. Uma conta comum recebe 403 ao abrir a URL de administração ou tentar enviar alterações.

## Preparar o banco

1. Selecione um banco de teste e confira se o SQL Editor e o `DATABASE_URL` da aplicação apontam para o mesmo banco e a mesma branch do Neon.
2. Para um banco novo, siga a ordem do [README](../README.md). Para um banco que já tem quizzes, conteúdos, simulações e histórico, execute **somente** as migrações ainda pendentes. A migração [adicionar_gestao_catalogo.sql](../sql/adicionar_gestao_catalogo.sql) deve ser aplicada **uma vez**, depois dos scripts de criação e cargas iniciais. Ela roda dentro de uma transação.
3. Confira a migração pelo SQL Editor:

```sql
SELECT to_regclass('public.catalogo_quizzes') AS catalogo;
SELECT id, estado, versao_publicada_id
FROM public.catalogo_quizzes
ORDER BY id;
```

Os quizzes antigos devem aparecer como `publicada`, com o mesmo ID público. As tentativas e as respostas antigas mantêm suas referências. Os conteúdos existentes preservam o HTML e os IDs, e as simulações mantêm as versões do catálogo atual. Não reaplique as cargas SQL antigas de quizzes após a migração: o painel passa a publicar as novas versões.

4. Reinicie o SafeClick depois de aplicar a migração. Se houver mais de uma instância conectada ao mesmo banco, atualize todas para esta versão antes de publicar novas revisões. O código anterior não conhece os estados do catálogo nem a separação de versões dos quizzes.

Para usar o formato Oficina e os comentários por alternativa, execute também [adicionar_formato_quizzes.sql](../sql/adicionar_formato_quizzes.sql) depois da migração do catálogo. A migração acrescenta campos às versões e às alternativas. Os quizzes anteriores continuam no formato de perguntas e respostas.

## Usar o editor

- **Conteúdos educativos**: informe título, endereço e corpo. O editor aceita texto; linhas em branco separam parágrafos. Uma revisão com texto novo é escapada antes da publicação. Se mudar apenas o título de um conteúdo antigo, a formatação existente é preservada. O endereço não muda depois da criação para manter os links.
- **Quizzes**: adicione até 20 perguntas e até 8 alternativas por pergunta. Use **Subir**, **Descer** e **Remover** para organizar os itens. Para publicar, cada pergunta deve ter enunciado, de 2 a 8 alternativas preenchidas, exatamente uma correta e uma explicação. Os dois quizzes originais continuam com cinco perguntas e quatro alternativas por pergunta. Cada publicação cria uma edição que não altera tentativas anteriores.
- **Simulações**: escolha o formato, escreva a mensagem fictícia e os sinais de risco e defina o texto, consequência e explicação de cada escolha. Inclua pelo menos uma escolha segura e uma de risco. O formato loja permite um produto opcional.
- **Páginas**: publique ajuda, orientações e outras páginas editoriais em `/paginas/`, acessível pelo link em **Conteúdos**. Essas páginas não registram conclusão no progresso. As rotas de login, o laboratório e os documentos de privacidade mantêm seus fluxos próprios.

Em todos os tipos, **Salvar rascunho** não muda o que os usuários veem. Use **Visualizar versão salva** para revisar e **Publicar** para disponibilizar. **Despublicar** retira o item do site sem apagar o histórico. **Remover** apaga somente rascunhos inéditos sem vínculos; itens já publicados passam ao filtro **Removido**. **Restaurar** devolve o item à gestão como despublicado. As ações de publicação e remoção têm uma página de confirmação. Para aplicar alterações no editor de quizzes ou simulações, mantenha o JavaScript ativado.

Em **Quizzes → Importar rascunhos**, selecione um arquivo JSON em UTF-8 com até 12 itens. Cada objeto precisa de `titulo` e `questoes`. Cada questão inclui `enunciado`, `explicacao` e `alternativas` com `texto`, `correta` e, opcionalmente, `explicacao`. Ao comentar uma alternativa, preencha o comentário de todas as opções da mesma pergunta. O campo `formato` aceita `perguntas` ou `oficina`. Na oficina, use o mesmo banco de cartões em todos os trechos e uma resposta correta distinta para cada trecho. O lote preserva títulos já cadastrados. As criações e publicações registram a conta administrativa autenticada.

## Verificar no ambiente de teste

1. Entre com um administrador e crie um quiz com duas perguntas. Reordene perguntas e alternativas, marque uma correta em cada uma, salve e confira a prévia.
2. Em outro perfil do navegador, entre com uma conta comum. Confirme que as rotas administrativas retornam 403, que a prévia não está acessível e que o rascunho não aparece na lista.
3. Publique o quiz e responda com a conta comum. Edite o gabarito, publique outra versão e confirme que o resultado anterior mantém a nota, o gabarito e a explicação originais. Despublique e confirme que novas respostas são bloqueadas.
4. Crie e publique um conteúdo, uma página e uma simulação fictícia. Confira cada endereço no site. Despublique ou remova e verifique que os itens somem dos catálogos.
5. Abra **Logs de auditoria** e filtre pela categoria **Administração**. As ações guardam o ID do responsável, do item e da versão, quando aplicável, sem copiar o corpo do conteúdo ou as respostas dos alunos.

A suíte local pode ser executada com `python -m pytest -q` após instalar as dependências de `requirements-dev.txt`.
