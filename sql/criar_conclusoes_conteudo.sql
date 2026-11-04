BEGIN;

CREATE TABLE public.conclusoes_conteudo (
    usuario_id INTEGER NOT NULL,
    conteudo_id INTEGER NOT NULL,
    concluido_em TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

  
    CONSTRAINT conclusoes_conteudo_pk
        PRIMARY KEY (usuario_id, conteudo_id),


    CONSTRAINT conclusoes_conteudo_usuario_fk
        FOREIGN KEY (usuario_id)
        REFERENCES public.usuarios (id)
        ON DELETE CASCADE,

 
    CONSTRAINT conclusoes_conteudo_conteudo_fk
        FOREIGN KEY (conteudo_id)
        REFERENCES public.conteudos (id)
        ON DELETE RESTRICT
);


CREATE INDEX conclusoes_conteudo_conteudo_idx
    ON public.conclusoes_conteudo (conteudo_id);

COMMIT;