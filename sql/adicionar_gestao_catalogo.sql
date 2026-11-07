BEGIN;

-- O ID público do quiz permanece estável; cada edição publicada ganha seus próprios dados.
CREATE TABLE public.catalogo_quizzes (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    estado TEXT NOT NULL DEFAULT 'rascunho'
        CHECK (estado IN ('rascunho', 'publicada', 'arquivada')),
    rascunho JSONB CHECK (jsonb_typeof(rascunho) = 'object'),
    versao_publicada_id INTEGER,
    revisao INTEGER NOT NULL DEFAULT 1 CHECK (revisao > 0),
    removido_em TIMESTAMPTZ,
    CHECK (estado <> 'publicada' OR versao_publicada_id IS NOT NULL),
    CHECK (removido_em IS NULL OR estado = 'arquivada')
);

ALTER TABLE public.quizzes
    ADD COLUMN catalogo_id INTEGER,
    ADD COLUMN versao INTEGER NOT NULL DEFAULT 1 CHECK (versao > 0);

INSERT INTO public.catalogo_quizzes (id) OVERRIDING SYSTEM VALUE
SELECT id FROM public.quizzes ORDER BY id;

UPDATE public.quizzes SET catalogo_id = id;

ALTER TABLE public.quizzes
    ALTER COLUMN catalogo_id SET NOT NULL,
    ADD CONSTRAINT quizzes_catalogo_fk FOREIGN KEY (catalogo_id)
        REFERENCES public.catalogo_quizzes (id) ON DELETE RESTRICT,
    ADD CONSTRAINT quizzes_catalogo_versao_unica UNIQUE (catalogo_id, versao),
    ADD CONSTRAINT quizzes_catalogo_identidade_unica UNIQUE (catalogo_id, id);

ALTER TABLE public.catalogo_quizzes
    ADD CONSTRAINT catalogo_quizzes_versao_fk FOREIGN KEY (id, versao_publicada_id)
        REFERENCES public.quizzes (catalogo_id, id) ON DELETE RESTRICT;

UPDATE public.catalogo_quizzes
SET estado = 'publicada', versao_publicada_id = id;

SELECT setval(
    pg_get_serial_sequence('public.catalogo_quizzes', 'id'),
    COALESCE((SELECT MAX(id) FROM public.catalogo_quizzes), 1),
    EXISTS (SELECT 1 FROM public.catalogo_quizzes)
);

-- O HTML e as conclusões existentes continuam nos mesmos registros.
ALTER TABLE public.conteudos
    ADD COLUMN secao TEXT NOT NULL DEFAULT 'conteudos'
        CHECK (secao IN ('conteudos', 'paginas')),
    ADD COLUMN estado TEXT NOT NULL DEFAULT 'publicada'
        CHECK (estado IN ('rascunho', 'publicada', 'arquivada')),
    ADD COLUMN rascunho JSONB CHECK (jsonb_typeof(rascunho) = 'object'),
    ADD COLUMN versao INTEGER NOT NULL DEFAULT 1 CHECK (versao >= 0),
    ADD COLUMN revisao INTEGER NOT NULL DEFAULT 1 CHECK (revisao > 0),
    ADD COLUMN removido_em TIMESTAMPTZ,
    ADD CONSTRAINT conteudos_estado_publicacao CHECK (estado <> 'publicada' OR versao > 0),
    ADD CONSTRAINT conteudos_remocao CHECK (removido_em IS NULL OR estado = 'arquivada');

CREATE INDEX conteudos_secao_estado_idx ON public.conteudos (secao, estado, id);

ALTER TABLE public.simulacoes
    ADD COLUMN revisao INTEGER NOT NULL DEFAULT 1 CHECK (revisao > 0),
    ADD COLUMN removido_em TIMESTAMPTZ,
    ADD CONSTRAINT simulacoes_remocao CHECK (removido_em IS NULL OR estado = 'arquivada');

COMMIT;
