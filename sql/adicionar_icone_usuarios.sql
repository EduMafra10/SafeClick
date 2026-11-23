BEGIN;

ALTER TABLE public.usuarios
    ADD COLUMN IF NOT EXISTS icone TEXT;

ALTER TABLE public.usuarios
    DROP CONSTRAINT IF EXISTS usuarios_icone_valido;

ALTER TABLE public.usuarios
    ADD CONSTRAINT usuarios_icone_valido CHECK (
        icone IS NULL OR icone IN (
            'robo', 'astronauta', 'raposa', 'gato', 'coruja', 'panda', 'pinguim', 'urso', 'coelho', 'sapo', 'alien', 'fantasma'
        )
    );

COMMIT;
