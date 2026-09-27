BEGIN;

ALTER TABLE public.tentativas_simulacao
ADD COLUMN usuario_id INTEGER
    CONSTRAINT tentativas_simulacao_usuario_fk
    REFERENCES public.usuarios (id);

ALTER TABLE public.tentativas_quiz
ADD COLUMN usuario_id INTEGER
    CONSTRAINT tentativas_quiz_usuario_fk
    REFERENCES public.usuarios (id);

CREATE INDEX tentativas_simulacao_usuario_idx
    ON public.tentativas_simulacao (usuario_id);

CREATE INDEX tentativas_quiz_usuario_idx
    ON public.tentativas_quiz (usuario_id);

COMMIT;