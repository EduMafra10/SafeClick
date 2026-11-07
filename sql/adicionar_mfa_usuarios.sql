BEGIN;

-- acrescenta os dados do vinculo com o autenticador
ALTER TABLE public.usuarios
    ADD COLUMN mfa_identidade UUID NOT NULL DEFAULT gen_random_uuid(),
    ADD COLUMN mfa_fator_sid TEXT,
    ADD COLUMN mfa_confirmado_em TIMESTAMPTZ;

ALTER TABLE public.usuarios
    ADD CONSTRAINT usuarios_mfa_identidade_unica
        UNIQUE (mfa_identidade),

    ADD CONSTRAINT usuarios_mfa_fator_unico
        UNIQUE (mfa_fator_sid),

    -- a confirmacao exige um autenticador vinculado
    ADD CONSTRAINT usuarios_mfa_confirmacao_valida
        CHECK (
            mfa_confirmado_em IS NULL
            OR mfa_fator_sid IS NOT NULL
        );

COMMIT;