BEGIN;

-- Preserva avaliações, respostas e a visão usada pelo progresso privado.
CREATE OR REPLACE FUNCTION public.limpar_participacao_conta() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.excluida_em IS NOT NULL THEN
        DELETE FROM public.avaliacoes_conteudo WHERE usuario_id=NEW.id;
        DELETE FROM public.avaliacoes_quiz WHERE usuario_id=NEW.id;
    ELSIF NEW.exclusao_solicitada_em IS NOT NULL THEN
        UPDATE public.avaliacoes_conteudo SET publicar_nota=FALSE,publicar_comentario=FALSE,
            moderacao='nao_solicitada',autorizado_em=NULL,moderado_por=NULL,moderado_em=NULL,
            revisao=revisao+1 WHERE usuario_id=NEW.id;
        UPDATE public.avaliacoes_quiz SET publicar_nota=FALSE,publicar_comentario=FALSE,
            moderacao='nao_solicitada',autorizado_em=NULL,moderado_por=NULL,moderado_em=NULL,
            revisao=revisao+1 WHERE usuario_id=NEW.id;
    END IF;
    RETURN NEW;
END $$;

DROP TRIGGER IF EXISTS participacao_conta_privacidade ON public.usuarios;
CREATE TRIGGER participacao_conta_privacidade
AFTER UPDATE OF exclusao_solicitada_em,excluida_em ON public.usuarios
FOR EACH ROW EXECUTE FUNCTION public.limpar_participacao_conta();

-- Remove somente a preferência da funcionalidade descontinuada.
DROP TABLE IF EXISTS public.preferencias_ranking;

COMMIT;
