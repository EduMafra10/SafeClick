BEGIN;

ALTER TABLE public.tentativas_quiz
ADD COLUMN IF NOT EXISTS token_envio TEXT;

CREATE UNIQUE INDEX IF NOT EXISTS tentativas_quiz_token_envio_unico
ON public.tentativas_quiz (token_envio);

COMMIT;