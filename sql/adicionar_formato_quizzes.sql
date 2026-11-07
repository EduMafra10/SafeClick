BEGIN;

SET LOCAL lock_timeout = '5s';

ALTER TABLE public.quizzes
    ADD COLUMN IF NOT EXISTS formato TEXT NOT NULL DEFAULT 'perguntas'
        CHECK (formato IN ('perguntas', 'oficina'));

ALTER TABLE public.alternativas
    ADD COLUMN IF NOT EXISTS explicacao TEXT NOT NULL DEFAULT ''
        CHECK (char_length(explicacao) <= 800);

COMMIT;
