BEGIN;

DO $$
DECLARE documento text;
BEGIN
    SELECT conteudo_html INTO documento FROM public.versoes_politica WHERE versao='1.3';
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Publique a política 1.3 antes de preparar a versão 1.4.';
    END IF;
    documento := replace(documento,'Versão 1.3 · vigente desde 15/11/2026','Versão 1.4 · vigente desde 15/11/2026');
    documento := replace(documento,
        'O ranking e as avaliações públicas são opcionais e dependem das escolhas descritas na seção de participação.',
        'As avaliações públicas são opcionais e dependem das escolhas descritas na seção de participação. O progresso e os resultados individuais permanecem privados.');
    documento := replace(documento,'A exposição opcional de pontuação e avaliações','A exposição opcional de avaliações');
    documento := replace(documento,'Participação opcional, avaliações e ranking','Avaliações e participação opcional');
    documento := replace(documento,
        'Esta versão acrescenta controles de publicação de avaliações e participação no ranking. Consulte o <a href="/ranking/privacidade">aviso de participação</a> e controle suas escolhas em <a href="/avaliacoes/minhas">Minhas avaliações</a> e <a href="/ranking/participacao">Participação no ranking</a>. Nenhuma escolha pública é ativada automaticamente.',
        'Esta versão mantém as avaliações públicas opcionais e o progresso privado. A comparação pública de pontuações foi descontinuada. Consulte o <a href="/avaliacoes/privacidade">aviso de publicação de avaliações</a> e controle suas escolhas em <a href="/avaliacoes/minhas">Minhas avaliações</a>. Nenhuma escolha pública é ativada automaticamente.');
    documento := regexp_replace(documento,'<p>No ranking, mediante adesão,[^<]*</p>','','g');
    documento := replace(documento,
        'É possível desmarcar o compartilhamento no formulário da avaliação, excluir em “Minhas avaliações” e sair em “Participação no ranking”.',
        'É possível desmarcar o compartilhamento no formulário da avaliação ou usar “Minhas avaliações” para retirar a publicação ou excluir o registro.');
    documento := replace(documento,'avaliações e preferência do ranking são eliminadas','as avaliações são eliminadas');
    IF documento LIKE '%/ranking/%' OR documento LIKE '%No ranking, mediante adesão%' THEN
        RAISE EXCEPTION 'Revise as referências do documento antes de publicar a política 1.4.';
    END IF;
    INSERT INTO public.versoes_politica(versao,vigente_desde,conteudo_html)
    VALUES ('1.4', DATE '2026-11-15',documento)
    ON CONFLICT (versao) DO NOTHING;
END $$;

INSERT INTO public.politica_referencias(versao_politica,referencia_id,ordem)
SELECT '1.4',referencia_id,ordem FROM public.politica_referencias WHERE versao_politica='1.3'
ON CONFLICT DO NOTHING;

COMMIT;
