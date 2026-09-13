BEGIN;

CREATE TABLE public.quizzes (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    titulo TEXT NOT NULL,
    CONSTRAINT quizzes_titulo_preenchido
        CHECK (btrim(titulo) <> '')
);
CREATE TABLE public.questoes (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    quiz_id INTEGER NOT NULL,
    enunciado TEXT NOT NULL,
    explicacao TEXT NOT NULL,
    ordem SMALLINT NOT NULL,

    CONSTRAINT questoes_quiz_fk
        FOREIGN KEY (quiz_id)
        REFERENCES public.quizzes (id)
        ON DELETE RESTRICT,

    CONSTRAINT questoes_enunciado_preenchido
        CHECK (btrim(enunciado) <> ''),

    CONSTRAINT questoes_explicacao_preenchida
        CHECK (btrim(explicacao) <> ''),

    CONSTRAINT questoes_ordem_positiva
        CHECK (ordem > 0),

    CONSTRAINT questoes_quiz_ordem_unica
        UNIQUE (quiz_id, ordem)
);

CREATE TABLE public.alternativas (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    questao_id INTEGER NOT NULL,
    texto TEXT NOT NULL,
    correta BOOLEAN NOT NULL DEFAULT FALSE,
    ordem SMALLINT NOT NULL,

    CONSTRAINT alternativas_questao_fk
        FOREIGN KEY (questao_id)
        REFERENCES public.questoes (id)
        ON DELETE RESTRICT,

    CONSTRAINT alternativas_texto_preenchido
        CHECK (btrim(texto) <> ''),

    CONSTRAINT alternativas_ordem_positiva
        CHECK (ordem > 0),

    CONSTRAINT alternativas_questao_ordem_unica
        UNIQUE (questao_id, ordem),

    CONSTRAINT alternativas_questao_id_unico
        UNIQUE (questao_id, id)
);

CREATE UNIQUE INDEX alternativas_uma_correta_por_questao
    ON public.alternativas (questao_id)
    WHERE correta;

CREATE TABLE public.tentativas_quiz (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    quiz_id INTEGER NOT NULL,
    pontuacao SMALLINT NOT NULL,
    total_questoes SMALLINT NOT NULL,
    criada_em TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT tentativas_quiz_quiz_fk
        FOREIGN KEY (quiz_id)
        REFERENCES public.quizzes (id)
        ON DELETE RESTRICT,

    CONSTRAINT tentativas_quiz_total_positivo
        CHECK (total_questoes > 0),

    CONSTRAINT tentativas_quiz_pontuacao_valida
        CHECK (pontuacao >= 0 AND pontuacao <= total_questoes)
);

CREATE INDEX tentativas_quiz_quiz_idx
    ON public.tentativas_quiz (quiz_id);

CREATE TABLE public.respostas_tentativa_quiz (
    tentativa_id INTEGER NOT NULL,
    questao_id INTEGER NOT NULL,
    alternativa_id INTEGER NOT NULL,

    CONSTRAINT respostas_tentativa_quiz_pk
        PRIMARY KEY (tentativa_id, questao_id),

    CONSTRAINT respostas_tentativa_quiz_tentativa_fk
        FOREIGN KEY (tentativa_id)
        REFERENCES public.tentativas_quiz (id)
        ON DELETE CASCADE,

    CONSTRAINT respostas_tentativa_quiz_questao_fk
        FOREIGN KEY (questao_id)
        REFERENCES public.questoes (id)
        ON DELETE RESTRICT,

    CONSTRAINT respostas_tentativa_quiz_alternativa_fk
        FOREIGN KEY (questao_id, alternativa_id)
        REFERENCES public.alternativas (questao_id, id)
        ON DELETE RESTRICT
);

CREATE INDEX respostas_tentativa_quiz_alternativa_idx
    ON public.respostas_tentativa_quiz (questao_id, alternativa_id);

COMMIT;