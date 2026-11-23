BEGIN;

CREATE TABLE public.usuarios (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    nome TEXT NOT NULL CHECK (btrim(nome) <> ''),
    email TEXT NOT NULL CHECK (btrim(email) <> ''),

    senha_hash TEXT NOT NULL CHECK (btrim(senha_hash) <> ''),

    perfil TEXT NOT NULL DEFAULT 'usuario'
        CHECK (perfil IN ('usuario', 'administrador')),

    criado_em TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX usuarios_email_unico
    ON public.usuarios (lower(email));

COMMIT;