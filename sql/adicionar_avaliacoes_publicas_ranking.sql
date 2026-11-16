BEGIN;

-- Avaliações anteriores continuam privadas e sem autorização de publicação.
ALTER TABLE public.avaliacoes_conteudo
    ADD COLUMN IF NOT EXISTS publicar_nota BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS publicar_comentario BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS maior_de_idade BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS aviso_versao TEXT,
    ADD COLUMN IF NOT EXISTS autorizado_em TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS atualizada_em TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS revisao BIGINT NOT NULL DEFAULT 1,
    ADD COLUMN IF NOT EXISTS moderacao TEXT NOT NULL DEFAULT 'nao_solicitada',
    ADD COLUMN IF NOT EXISTS moderado_por INTEGER REFERENCES public.usuarios(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS moderado_em TIMESTAMPTZ;

ALTER TABLE public.avaliacoes_quiz
    ADD COLUMN IF NOT EXISTS publicar_nota BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS publicar_comentario BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS maior_de_idade BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS aviso_versao TEXT,
    ADD COLUMN IF NOT EXISTS autorizado_em TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS atualizada_em TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS revisao BIGINT NOT NULL DEFAULT 1,
    ADD COLUMN IF NOT EXISTS moderacao TEXT NOT NULL DEFAULT 'nao_solicitada',
    ADD COLUMN IF NOT EXISTS moderado_por INTEGER REFERENCES public.usuarios(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS moderado_em TIMESTAMPTZ;

DO $$
DECLARE tabela TEXT;
BEGIN
    FOREACH tabela IN ARRAY ARRAY['avaliacoes_conteudo', 'avaliacoes_quiz'] LOOP
        IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = tabela || '_publicacao_valida') THEN
            EXECUTE format('ALTER TABLE public.%I ADD CONSTRAINT %I CHECK (
                revisao > 0 AND moderacao IN (''nao_solicitada'', ''pendente'', ''aprovada'', ''rejeitada'')
                AND (NOT publicar_comentario OR (publicar_nota AND comentario IS NOT NULL AND btrim(comentario) <> ''''))
                AND (NOT publicar_nota OR (maior_de_idade AND aviso_versao IS NOT NULL AND autorizado_em IS NOT NULL))
                AND (moderacao <> ''aprovada'' OR publicar_comentario)
            )', tabela, tabela || '_publicacao_valida');
        END IF;
    END LOOP;
END $$;

CREATE TABLE IF NOT EXISTS public.preferencias_ranking (
    usuario_id INTEGER PRIMARY KEY REFERENCES public.usuarios(id) ON DELETE CASCADE,
    apelido TEXT NOT NULL UNIQUE CHECK (apelido ~ '^Participante [A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{4}$'),
    aviso_versao TEXT NOT NULL,
    maior_de_idade BOOLEAN NOT NULL CHECK (maior_de_idade),
    autorizado_em TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS avaliacoes_conteudo_publicas_idx
    ON public.avaliacoes_conteudo (conteudo_id, atualizada_em DESC) WHERE publicar_nota;
CREATE INDEX IF NOT EXISTS avaliacoes_quiz_publicas_idx
    ON public.avaliacoes_quiz (catalogo_id, atualizada_em DESC) WHERE publicar_nota;

-- Recalcula quizzes a partir das respostas e da edição efetivamente respondida.
CREATE OR REPLACE VIEW public.resultados_validos_atividades AS
WITH gabaritos AS (
    SELECT q.id, q.quiz_id, COUNT(a.id) AS alternativas,
           COUNT(a.id) FILTER (WHERE a.correta) AS corretas
    FROM public.questoes q LEFT JOIN public.alternativas a ON a.questao_id = q.id
    GROUP BY q.id
), edicoes AS (
    SELECT quiz_id, COUNT(*) AS total,
           bool_and(corretas = 1 AND alternativas BETWEEN 2 AND 8) AS valido
    FROM gabaritos GROUP BY quiz_id
), respostas AS (
    SELECT t.id, t.usuario_id, t.criada_em, v.catalogo_id, v.titulo, v.formato,
           t.total_questoes AS total, COUNT(a.id) FILTER (WHERE a.correta) AS acertos,
           c.estado = 'publicada' AND c.removido_em IS NULL AS disponivel
    FROM public.tentativas_quiz t
    JOIN public.quizzes v ON v.id = t.quiz_id
    JOIN public.catalogo_quizzes c ON c.id = v.catalogo_id
    JOIN edicoes e ON e.quiz_id = v.id
    LEFT JOIN public.respostas_tentativa_quiz r ON r.tentativa_id = t.id
    LEFT JOIN public.questoes q ON q.id = r.questao_id AND q.quiz_id = v.id
    LEFT JOIN public.alternativas a ON a.id = r.alternativa_id AND a.questao_id = q.id
    WHERE t.usuario_id IS NOT NULL AND t.total_questoes > 0 AND e.valido
    GROUP BY t.id, v.id, c.id, e.total
    HAVING COUNT(a.id) = e.total AND COUNT(r.questao_id) = e.total
       AND t.total_questoes = e.total
       AND t.pontuacao = COUNT(a.id) FILTER (WHERE a.correta)
       AND (v.formato <> 'oficina' OR COUNT(DISTINCT a.texto) = e.total)
)
SELECT usuario_id, 'quiz'::text AS tipo, 'quiz:' || catalogo_id AS chave,
       catalogo_id AS item_id, id AS tentativa_id, titulo, formato,
       acertos, total, round(100.0 * acertos / total, 2) AS pontos,
       criada_em AS realizada_em, disponivel
FROM respostas
UNION ALL
SELECT t.usuario_id, 'simulacao', 'simulacao:' || s.id, s.id, t.id,
       v.conteudo->>'titulo', 'simulacao',
       CASE WHEN v.conteudo->'opcoes'->t.opcao->>'segura' = 'true' THEN 1 ELSE 0 END,
       1, CASE WHEN v.conteudo->'opcoes'->t.opcao->>'segura' = 'true' THEN 100.0 ELSE 0.0 END,
       t.criada_em, s.estado = 'publicada' AND s.removido_em IS NULL
FROM public.tentativas_simulacao t
JOIN public.versoes_simulacao v ON v.id = t.versao_simulacao_id
JOIN public.simulacoes s ON s.id = v.simulacao_id AND s.identificador = t.simulacao
WHERE t.usuario_id IS NOT NULL AND v.conteudo->'opcoes'->t.opcao->>'segura' IN ('true', 'false')
UNION ALL
SELECT usuario_id, 'laboratorio', 'laboratorio:qual-vazou-mais', NULL::integer, id,
       'Qual vazou mais?', 'laboratorio', acertos, total_rodadas,
       round(100.0 * acertos / total_rodadas, 2), concluido_em, TRUE
FROM public.desafios_senha
WHERE total_rodadas = 5 AND acertos BETWEEN 0 AND 5 AND btrim(token_partida) <> '';

-- Retira a exposição imediatamente; a exclusão definitiva também elimina avaliações.
CREATE OR REPLACE FUNCTION public.limpar_participacao_conta() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.excluida_em IS NOT NULL THEN
        DELETE FROM public.avaliacoes_conteudo WHERE usuario_id = NEW.id;
        DELETE FROM public.avaliacoes_quiz WHERE usuario_id = NEW.id;
        DELETE FROM public.preferencias_ranking WHERE usuario_id = NEW.id;
    ELSIF NEW.exclusao_solicitada_em IS NOT NULL THEN
        UPDATE public.avaliacoes_conteudo SET publicar_nota = FALSE, publicar_comentario = FALSE,
            moderacao = 'nao_solicitada', autorizado_em = NULL, revisao = revisao + 1 WHERE usuario_id = NEW.id;
        UPDATE public.avaliacoes_quiz SET publicar_nota = FALSE, publicar_comentario = FALSE,
            moderacao = 'nao_solicitada', autorizado_em = NULL, revisao = revisao + 1 WHERE usuario_id = NEW.id;
        DELETE FROM public.preferencias_ranking WHERE usuario_id = NEW.id;
    END IF;
    IF NEW.perfil <> 'usuario' THEN
        DELETE FROM public.preferencias_ranking WHERE usuario_id = NEW.id;
    END IF;
    RETURN NEW;
END $$;
DROP TRIGGER IF EXISTS participacao_conta_privacidade ON public.usuarios;
CREATE TRIGGER participacao_conta_privacidade
AFTER UPDATE OF exclusao_solicitada_em, excluida_em, perfil ON public.usuarios
FOR EACH ROW EXECUTE FUNCTION public.limpar_participacao_conta();

COMMIT;
