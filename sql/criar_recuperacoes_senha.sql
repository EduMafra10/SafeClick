BEGIN;

CREATE TABLE public.recuperacoes_senha (
    usuario_id INTEGER PRIMARY KEY
        REFERENCES public.usuarios(id) ON DELETE CASCADE,

    token_hash TEXT NOT NULL UNIQUE
        CHECK (token_hash ~ '^[0-9a-f]{64}$'),

    criado_em TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expira_em TIMESTAMPTZ NOT NULL
        DEFAULT (CURRENT_TIMESTAMP + INTERVAL '30 minutes'),

    utilizado_em TIMESTAMPTZ,

    CHECK (expira_em > criado_em)
);

COMMIT;