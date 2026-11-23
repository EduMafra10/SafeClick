BEGIN;

CREATE TABLE public.logins_pendentes (
    usuario_id INTEGER PRIMARY KEY
        REFERENCES public.usuarios(id) ON DELETE CASCADE,


    token_hash TEXT NOT NULL UNIQUE
        CHECK (length(token_hash) = 64),

    tentativas SMALLINT NOT NULL DEFAULT 0
        CHECK (tentativas BETWEEN 0 AND 5),

    criado_em TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expira_em TIMESTAMPTZ NOT NULL
        DEFAULT (CURRENT_TIMESTAMP + INTERVAL '5 minutes'),

    concluido_em TIMESTAMPTZ,

    CHECK (expira_em > criado_em)
);

COMMIT;
