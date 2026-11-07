BEGIN;

-- versoes publicadas da politica de privacidade (mesmo formato de versoes_termos)
CREATE TABLE public.versoes_politica (
    versao TEXT PRIMARY KEY
        CHECK (versao = btrim(versao) AND versao <> ''),
    vigente_desde DATE NOT NULL,
    conteudo_html TEXT NOT NULL CHECK (btrim(conteudo_html) <> ''),
    registrado_em TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);


-- leis, resolucoes e artigos citados nos documentos
CREATE TABLE public.referencias_legais (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    norma TEXT NOT NULL CHECK (btrim(norma) <> ''),
    -- artigo ou inciso; fica vazio quando o documento cita a norma inteira
    dispositivo TEXT CHECK (dispositivo IS NULL OR btrim(dispositivo) <> ''),
    assunto TEXT NOT NULL CHECK (btrim(assunto) <> ''),
    url TEXT CHECK (url IS NULL OR url LIKE 'https://%'),
    CONSTRAINT referencias_legais_unica UNIQUE NULLS NOT DISTINCT (norma, dispositivo)
);


-- quais leis cada versao dos termos cita
CREATE TABLE public.termos_referencias (
    versao_termos TEXT NOT NULL
        REFERENCES public.versoes_termos (versao) ON DELETE CASCADE,
    referencia_id INTEGER NOT NULL
        REFERENCES public.referencias_legais (id) ON DELETE RESTRICT,
    ordem SMALLINT NOT NULL CHECK (ordem > 0),
    PRIMARY KEY (versao_termos, referencia_id),
    CONSTRAINT termos_referencias_ordem_unica UNIQUE (versao_termos, ordem)
);


-- quais leis cada versao da politica cita
CREATE TABLE public.politica_referencias (
    versao_politica TEXT NOT NULL
        REFERENCES public.versoes_politica (versao) ON DELETE CASCADE,
    referencia_id INTEGER NOT NULL
        REFERENCES public.referencias_legais (id) ON DELETE RESTRICT,
    ordem SMALLINT NOT NULL CHECK (ordem > 0),
    PRIMARY KEY (versao_politica, referencia_id),
    CONSTRAINT politica_referencias_ordem_unica UNIQUE (versao_politica, ordem)
);

COMMIT;
