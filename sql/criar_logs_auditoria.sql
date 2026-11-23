BEGIN;

CREATE TABLE public.logs_auditoria (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    criado_em TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    usuario_id INTEGER,

    evento TEXT NOT NULL,

    resultado TEXT NOT NULL,

    recurso_tipo TEXT,

    recurso_id TEXT,

    detalhes JSONB NOT NULL DEFAULT '{}'::jsonb,

    CONSTRAINT logs_auditoria_usuario_fk
        FOREIGN KEY (usuario_id)
        REFERENCES public.usuarios (id)
        ON DELETE SET NULL,

    CONSTRAINT logs_auditoria_evento_preenchido
        CHECK (btrim(evento) <> ''),

    CONSTRAINT logs_auditoria_resultado_valido
        CHECK (resultado IN ('sucesso', 'falha', 'negado')),

    CONSTRAINT logs_auditoria_recurso_tipo_preenchido
        CHECK (
            recurso_tipo IS NULL
            OR btrim(recurso_tipo) <> ''
        ),

    CONSTRAINT logs_auditoria_recurso_id_preenchido
        CHECK (
            recurso_id IS NULL
            OR btrim(recurso_id) <> ''
        ),

    CONSTRAINT logs_auditoria_detalhes_objeto
        CHECK (jsonb_typeof(detalhes) = 'object')
);

CREATE INDEX logs_auditoria_data_idx
    ON public.logs_auditoria (criado_em DESC, id DESC);

CREATE INDEX logs_auditoria_usuario_data_idx
    ON public.logs_auditoria (usuario_id, criado_em DESC);

CREATE INDEX logs_auditoria_evento_data_idx
    ON public.logs_auditoria (evento, criado_em DESC);

COMMIT;