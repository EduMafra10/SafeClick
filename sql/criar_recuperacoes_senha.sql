BEGIN;

-- guarda a solicitacao mais recente de recuperacao de cada usuario
CREATE TABLE public.recuperacoes_senha (
    usuario_id INTEGER PRIMARY KEY
        REFERENCES public.usuarios(id) ON DELETE CASCADE,

    -- guarda apenas o hash do token enviado no link por e-mail
    token_hash TEXT NOT NULL UNIQUE
        CHECK (token_hash ~ '^[0-9a-f]{64}$'),

    criado_em TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expira_em TIMESTAMPTZ NOT NULL
        DEFAULT (CURRENT_TIMESTAMP + INTERVAL '30 minutes'),

    -- preenchido quando a nova senha for salva com sucesso
    utilizado_em TIMESTAMPTZ,

    CHECK (expira_em > criado_em)
);

COMMIT;