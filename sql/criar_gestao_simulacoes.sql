BEGIN;

CREATE TABLE public.simulacoes (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    identificador VARCHAR(80) NOT NULL UNIQUE
        CHECK (identificador ~ '^[a-z][a-z0-9_]*$'),

    slug VARCHAR(80) NOT NULL UNIQUE
        CHECK (slug ~ '^[a-z0-9]+(-[a-z0-9]+)*$'),

    estado TEXT NOT NULL DEFAULT 'rascunho'
        CHECK (estado IN ('rascunho', 'publicada', 'arquivada')),

    rascunho JSONB NOT NULL DEFAULT '{}'::jsonb
        CHECK (jsonb_typeof(rascunho) = 'object'),

    versao_publicada_id BIGINT,

    criado_por INTEGER
        REFERENCES public.usuarios (id)
        ON DELETE SET NULL,

    criado_em TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT simulacoes_publicacao_obrigatoria
        CHECK (
            estado <> 'publicada'
            OR versao_publicada_id IS NOT NULL
        )
);


CREATE TABLE public.versoes_simulacao (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    simulacao_id INTEGER NOT NULL
        REFERENCES public.simulacoes (id)
        ON DELETE RESTRICT,

    numero INTEGER NOT NULL
        CHECK (numero > 0),

    conteudo JSONB NOT NULL
        CHECK (jsonb_typeof(conteudo) = 'object'),

    publicado_por INTEGER
        REFERENCES public.usuarios (id)
        ON DELETE SET NULL,

    publicado_em TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT versoes_simulacao_numero_unico
        UNIQUE (simulacao_id, numero),

    CONSTRAINT versoes_simulacao_identidade_unica
        UNIQUE (simulacao_id, id)
);


ALTER TABLE public.simulacoes
ADD CONSTRAINT simulacoes_versao_publicada_fk
    FOREIGN KEY (id, versao_publicada_id)
    REFERENCES public.versoes_simulacao (simulacao_id, id)
    ON DELETE RESTRICT;


ALTER TABLE public.tentativas_simulacao
ADD COLUMN versao_simulacao_id BIGINT
    REFERENCES public.versoes_simulacao (id)
    ON DELETE RESTRICT;

CREATE INDEX tentativas_simulacao_versao_idx
    ON public.tentativas_simulacao (versao_simulacao_id);

COMMIT;