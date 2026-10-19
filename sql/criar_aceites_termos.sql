BEGIN;


CREATE TABLE public.versoes_termos (
    versao TEXT PRIMARY KEY
        CHECK (versao = btrim(versao) AND versao <> ''),
    vigente_desde DATE NOT NULL,
    conteudo_html TEXT NOT NULL CHECK (btrim(conteudo_html) <> ''),
    registrado_em TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);


CREATE TABLE public.aceites_termos (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    usuario_id INTEGER NOT NULL
        REFERENCES public.usuarios (id) ON DELETE CASCADE,
    versao_termos TEXT NOT NULL
        REFERENCES public.versoes_termos (versao),
    aceito_em TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT aceites_termos_usuario_versao_unico
        UNIQUE (usuario_id, versao_termos)
);

COMMIT;
