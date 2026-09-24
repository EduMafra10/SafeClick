BEGIN;

-- guarda os dados usados no cadastro e na autenticacao do usuario
CREATE TABLE public.usuarios (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    nome TEXT NOT NULL CHECK (btrim(nome) <> ''),
    email TEXT NOT NULL CHECK (btrim(email) <> ''),

    -- o python irá gravar aqui o hash gerado pelo scrypt
    senha_hash TEXT NOT NULL CHECK (btrim(senha_hash) <> ''),

    -- cadastro publico irá criar contas com o perfil do usuario
    perfil TEXT NOT NULL DEFAULT 'usuario'
        CHECK (perfil IN ('usuario', 'administrador')),

    criado_em TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- impede email repetidos inclusive com diferenca de maiusculas 
CREATE UNIQUE INDEX usuarios_email_unico
    ON public.usuarios (lower(email));

COMMIT;