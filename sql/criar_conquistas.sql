BEGIN;

CREATE TABLE public.conquistas (
    id SMALLINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    codigo TEXT NOT NULL,
    nome TEXT NOT NULL,
    descricao TEXT NOT NULL,
    criterio TEXT NOT NULL,
    meta SMALLINT NOT NULL,
    ordem SMALLINT NOT NULL,

    CONSTRAINT conquistas_codigo_unico UNIQUE (codigo),
    CONSTRAINT conquistas_ordem_unica UNIQUE (ordem),

    CONSTRAINT conquistas_codigo_valido
        CHECK (codigo ~ '^[a-z0-9-]{3,40}$'),

    CONSTRAINT conquistas_nome_valido
        CHECK (char_length(nome) BETWEEN 3 AND 60),

    CONSTRAINT conquistas_descricao_valida
        CHECK (char_length(descricao) BETWEEN 3 AND 200),

    CONSTRAINT conquistas_criterio_valido
        CHECK (criterio IN (
            'conteudos_concluidos',
            'quizzes_respondidos',
            'acertos_em_um_quiz',
            'quizzes_perfeitos',
            'simulacoes_realizadas',
            'escolhas_seguras',
            'desafios_senha'
        )),

    CONSTRAINT conquistas_meta_valida
        CHECK (meta > 0)
);

CREATE TABLE public.conquistas_usuario (
    usuario_id INTEGER NOT NULL,
    conquista_id SMALLINT NOT NULL,
    desbloqueada_em TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT conquistas_usuario_pk
        PRIMARY KEY (usuario_id, conquista_id),

    -- ao excluir a conta, as conquistas dela também são apagadas
    CONSTRAINT conquistas_usuario_usuario_fk
        FOREIGN KEY (usuario_id)
        REFERENCES public.usuarios (id)
        ON DELETE CASCADE,

    CONSTRAINT conquistas_usuario_conquista_fk
        FOREIGN KEY (conquista_id)
        REFERENCES public.conquistas (id)
        ON DELETE CASCADE
);

INSERT INTO public.conquistas (codigo, nome, descricao, criterio, meta, ordem) VALUES
    ('primeiro-conteudo', 'Primeiro conteúdo', 'Concluiu o primeiro conteúdo educativo.', 'conteudos_concluidos', 1, 1),
    ('leitor-dedicado', 'Leitor dedicado', 'Concluiu cinco conteúdos educativos.', 'conteudos_concluidos', 5, 2),
    ('primeiro-quiz', 'Primeiro quiz', 'Respondeu um quiz até o fim.', 'quizzes_respondidos', 1, 3),
    ('cinco-acertos', 'Cinco acertos', 'Acertou cinco perguntas em um mesmo quiz.', 'acertos_em_um_quiz', 5, 4),
    ('nota-maxima', 'Nota máxima', 'Acertou todas as perguntas de um quiz.', 'quizzes_perfeitos', 1, 5),
    ('primeira-simulacao', 'Primeira simulação', 'Concluiu a primeira simulação de golpe.', 'simulacoes_realizadas', 1, 6),
    ('escolha-segura', 'Escolha segura', 'Fez três escolhas seguras nas simulações.', 'escolhas_seguras', 3, 7),
    ('detetive-de-senhas', 'Detetive de senhas', 'Terminou uma partida do desafio “Qual vazou mais?” no Laboratório.', 'desafios_senha', 1, 8);

COMMIT;