BEGIN;

CREATE TABLE public.limites_autenticacao (
    chave_hash TEXT PRIMARY KEY
        CHECK (length(chave_hash) = 64),

    tentativas SMALLINT NOT NULL
        CHECK (tentativas BETWEEN 1 AND 5),

    expira_em TIMESTAMPTZ NOT NULL
);

CREATE INDEX limites_autenticacao_expiracao_idx
    ON public.limites_autenticacao (expira_em);

CREATE TABLE public.sessoes_autenticadas (
    token_hash TEXT PRIMARY KEY
        CHECK (length(token_hash) = 64),

    usuario_id INTEGER NOT NULL
        REFERENCES public.usuarios(id) ON DELETE CASCADE,

    criada_em TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    ultima_atividade TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    expira_em TIMESTAMPTZ NOT NULL
        DEFAULT (CURRENT_TIMESTAMP + INTERVAL '8 hours'),

    CHECK (expira_em > criada_em)
);

CREATE INDEX sessoes_autenticadas_usuario_idx
    ON public.sessoes_autenticadas (usuario_id);

CREATE INDEX sessoes_autenticadas_expiracao_idx
    ON public.sessoes_autenticadas (expira_em);

COMMIT;