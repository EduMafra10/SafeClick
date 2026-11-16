BEGIN;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM public.versoes_politica WHERE versao IN ('1.1','1.2')) THEN
        RAISE EXCEPTION 'Publique a política 1.1 ou 1.2 antes de preparar a versão 1.3.';
    END IF;
END $$;

-- Arquiva outra versão; os documentos anteriormente aceitos não são alterados.
INSERT INTO public.versoes_politica (versao,vigente_desde,conteudo_html)
SELECT '1.3', DATE '2026-11-15',
    replace(replace(replace(conteudo_html,
        'Versão ' || versao || ' · vigente desde ' || to_char(vigente_desde,'DD/MM/YYYY'),
        'Versão 1.3 · vigente desde 15/11/2026'),
        'Não vendemos seus dados, não mostramos anúncios, não criamos ranking entre usuários e não usamos cookies de rastreamento.',
        'Não vendemos seus dados, não mostramos anúncios e não usamos cookies de rastreamento. O ranking e as avaliações públicas são opcionais e dependem das escolhas descritas na seção de participação.'),
        'Todos os usuários recebem as configurações mais protetivas por padrão: não há perfil público, ranking entre usuários, chat, publicidade, perfilamento ou cookies de rastreamento. Seus resultados em quizzes e simulações não são mostrados a outros usuários.',
        'Todos os usuários recebem configurações privadas por padrão. Não há perfil público, chat, publicidade ou cookies de rastreamento. A exposição opcional de pontuação e avaliações é limitada a maiores de 18 anos por autodeclaração e depende de autorização específica. Usuários que não participam continuam utilizando as atividades e o progresso privados.')
    || $participacao$
    <section id="participacao-publica"><h2>Participação opcional, avaliações e ranking</h2>
    <p>Esta versão acrescenta controles de publicação de avaliações e participação no ranking. Consulte o <a href="/ranking/privacidade">aviso de participação</a> e controle suas escolhas em <a href="/avaliacoes/minhas">Minhas avaliações</a> e <a href="/ranking/participacao">Participação no ranking</a>. Nenhuma escolha pública é ativada automaticamente.</p>
    <p>A avaliação de utilidade coleta nota de 1 a 5 e comentário opcional de até 500 caracteres. Fica vinculada à conta para impedir duplicidade, permitir atualização e exclusão. Novas avaliações enviadas com o aviso de participação podem ser consultadas pela equipe administrativa para melhoria dos materiais. Comentários anteriores ao aviso permanecem privados até atualização pelo autor.</p>
    <p>A publicação é uma escolha separada: o titular autoriza incluir a nota na média pública e, se desejar, submeter o comentário à moderação. Não mostramos nome, e-mail ou identificador da conta na consulta pública. O texto não deve incluir dados pessoais, senhas, contatos ou dados sensíveis, inclusive de terceiros. A moderação pode impedir ou retirar a publicação. A alteração do comentário exige nova revisão.</p>
    <p>No ranking, mediante adesão, publicamos pseudônimo aleatório, posição, pontuação e quantidade de atividades. Não é utilizado o nome do cadastro, e-mail ou apelido escolhido livremente. O vínculo interno com a conta permanece; pseudonimização não significa anonimização definitiva. O cálculo considera o melhor resultado válido por atividade publicada, sem somar repetições, conforme a regra acessível na página do ranking.</p>
    <p>A escolha de exposição pública é registrada com a versão do aviso e a data da autorização. É opcional e revogável, sem prejuízo do uso dos recursos privados. A participação pública está limitada a pessoas que declaram ter 18 anos ou mais. A autodeclaração não constitui verificação documental de idade. A disponibilização desses recursos a menores depende de avaliação específica da equipe sobre melhor interesse e requisitos aplicáveis.</p>
    <p>É possível desmarcar o compartilhamento no formulário da avaliação, excluir em “Minhas avaliações” e sair em “Participação no ranking”. As alterações retiram os registros das próximas consultas do sistema. Não controlamos cópias feitas por terceiros. Quando a conta solicita exclusão, a participação pública é retirada; quando a exclusão é concluída, avaliações e preferência do ranking são eliminadas. O histórico mínimo de auditoria permanece sujeito às regras de retenção desta política.</p>
    <p>A equipe deve validar e documentar a hipótese legal da consulta administrativa de comentários, a operação de moderação, os prazos de retenção e os procedimentos dos titulares. Os controles técnicos e as escolhas registradas não representam certificação de conformidade jurídica automática. O canal de privacidade já informado nesta política permanece disponível.</p>
    </section>
    $participacao$
FROM public.versoes_politica WHERE versao IN ('1.1','1.2') ORDER BY versao DESC LIMIT 1
ON CONFLICT (versao) DO NOTHING;

INSERT INTO public.politica_referencias (versao_politica,referencia_id,ordem)
SELECT '1.3',referencia_id,ordem FROM public.politica_referencias
WHERE versao_politica=(SELECT versao FROM public.versoes_politica WHERE versao IN ('1.1','1.2') ORDER BY versao DESC LIMIT 1)
ON CONFLICT DO NOTHING;

COMMIT;
