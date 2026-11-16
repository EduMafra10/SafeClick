BEGIN;

CREATE TABLE public.avaliacoes_conteudo (
    usuario_id INTEGER NOT NULL,
    conteudo_id INTEGER NOT NULL,
    nota SMALLINT NOT NULL CHECK (nota BETWEEN 1 AND 5),
    comentario TEXT CHECK (char_length(comentario) <= 500),

    PRIMARY KEY (usuario_id, conteudo_id),
    FOREIGN KEY (usuario_id, conteudo_id)
        REFERENCES public.conclusoes_conteudo (usuario_id, conteudo_id) ON DELETE CASCADE
);

CREATE INDEX avaliacoes_conteudo_item_idx ON public.avaliacoes_conteudo (conteudo_id);

CREATE TABLE public.avaliacoes_quiz (
    usuario_id INTEGER NOT NULL REFERENCES public.usuarios (id) ON DELETE CASCADE,
    catalogo_id INTEGER NOT NULL REFERENCES public.catalogo_quizzes (id) ON DELETE RESTRICT,
    nota SMALLINT NOT NULL CHECK (nota BETWEEN 1 AND 5),
    comentario TEXT CHECK (char_length(comentario) <= 500),

    PRIMARY KEY (usuario_id, catalogo_id)
);

CREATE INDEX avaliacoes_quiz_item_idx ON public.avaliacoes_quiz (catalogo_id);

COMMIT;
