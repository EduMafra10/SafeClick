BEGIN;

CREATE TABLE public.desafios_senha (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    usuario_id INTEGER NOT NULL,
    acertos SMALLINT NOT NULL,
    total_rodadas SMALLINT NOT NULL,

   
    token_partida TEXT NOT NULL,

    concluido_em TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT desafios_senha_token_unico
        UNIQUE (token_partida),

    CONSTRAINT desafios_senha_rodadas_validas
        CHECK (total_rodadas > 0),

    CONSTRAINT desafios_senha_acertos_validos
        CHECK (acertos BETWEEN 0 AND total_rodadas),

    
    CONSTRAINT desafios_senha_usuario_fk
        FOREIGN KEY (usuario_id)
        REFERENCES public.usuarios (id)
        ON DELETE CASCADE
);


CREATE INDEX desafios_senha_usuario_idx
    ON public.desafios_senha (usuario_id, concluido_em DESC);

COMMIT;