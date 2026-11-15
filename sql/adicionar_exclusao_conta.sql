BEGIN;

ALTER TABLE public.usuarios
    ADD COLUMN IF NOT EXISTS exclusao_solicitada_em TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS excluida_em TIMESTAMPTZ,
    ALTER COLUMN nome DROP NOT NULL,
    ALTER COLUMN email DROP NOT NULL,
    ALTER COLUMN senha_hash DROP NOT NULL;

ALTER TABLE public.usuarios
    DROP CONSTRAINT IF EXISTS usuarios_exclusao_sem_dados_pessoais;

ALTER TABLE public.usuarios
    ADD CONSTRAINT usuarios_exclusao_sem_dados_pessoais
        CHECK (
            (excluida_em IS NULL
                AND nome IS NOT NULL
                AND email IS NOT NULL
                AND senha_hash IS NOT NULL)
            OR
            (excluida_em IS NOT NULL
                AND nome IS NULL
                AND email IS NULL
                AND senha_hash IS NULL
                AND mfa_fator_sid IS NULL
                AND mfa_confirmado_em IS NULL)
        );

CREATE INDEX IF NOT EXISTS usuarios_exclusao_pendente
    ON public.usuarios (exclusao_solicitada_em)
    WHERE exclusao_solicitada_em IS NOT NULL AND excluida_em IS NULL;

CREATE TABLE IF NOT EXISTS public.reativacoes_conta (
    usuario_id INTEGER PRIMARY KEY
        REFERENCES public.usuarios (id) ON DELETE CASCADE,
    token_hash TEXT NOT NULL UNIQUE
        CHECK (token_hash ~ '^[0-9a-f]{64}$'),
    criado_em TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expira_em TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS public.contas_excluidas (
    usuario_id INTEGER PRIMARY KEY
        REFERENCES public.usuarios (id) ON DELETE CASCADE,
    email_guardado TEXT NOT NULL
        CHECK (btrim(email_guardado) <> ''),
    descartar_em TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS contas_excluidas_descartar_em
    ON public.contas_excluidas (descartar_em);

COMMIT;