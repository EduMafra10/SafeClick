-- armazena as decisoes dos visitantes sem vinculo com algum usuario nesta etapa
CREATE TABLE public.tentativas_simulacao (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    simulacao TEXT NOT NULL,
    opcao TEXT NOT NULL,

    -- o banco preenche a data e a hora de quando alguma tentiva é feita
    criada_em TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);