BEGIN;

INSERT INTO public.quizzes (titulo)
SELECT novos.titulo
FROM (
    VALUES
        ('Phishing: aprenda antes de clicar'),
        ('Proteção de senhas e contas')
) AS novos (titulo)
WHERE NOT EXISTS (
    SELECT 1
    FROM public.quizzes AS existentes
    WHERE existentes.titulo = novos.titulo
);

INSERT INTO public.questoes (
    quiz_id,
    enunciado,
    explicacao,
    ordem
)
SELECT
    quiz.id,
    'Você recebe um e-mail dizendo que seu acesso ao portal da faculdade será bloqueado em dez minutos. A mensagem pede que você clique em um link e informe sua senha. Qual é a atitude mais segura?',
    'Golpistas podem usar ameaças de bloqueio para provocar decisões apressadas. Verifique a situação por um canal oficial acessado independentemente da mensagem.',
    1
FROM public.quizzes AS quiz
WHERE quiz.titulo = 'Phishing: aprenda antes de clicar'
ON CONFLICT (quiz_id, ordem) DO NOTHING;

INSERT INTO public.alternativas (
    questao_id,
    texto,
    correta,
    ordem
)
SELECT
    questao.id,
    opcao.texto,
    opcao.correta,
    opcao.ordem
FROM public.questoes AS questao
JOIN public.quizzes AS quiz
    ON quiz.id = questao.quiz_id
CROSS JOIN (
    VALUES
        (
            'Clicar imediatamente para evitar o bloqueio.',
            FALSE,
            1
        ),
        (
            'Responder ao e-mail perguntando se ele é verdadeiro.',
            FALSE,
            2
        ),
        (
            'Acessar o portal pelo endereço conhecido e verificar o aviso.',
            TRUE,
            3
        ),
        (
            'Encaminhar o link aos colegas para que testem primeiro.',
            FALSE,
            4
        )
) AS opcao (texto, correta, ordem)
WHERE quiz.titulo = 'Phishing: aprenda antes de clicar'
  AND questao.ordem = 1
ON CONFLICT (questao_id, ordem) DO NOTHING;

-- Phishing: aprenda antes de clicar: questão 2.
INSERT INTO public.questoes (
    quiz_id,
    enunciado,
    explicacao,
    ordem
)
SELECT
    quiz.id,
    'Uma mensagem apresenta o logotipo da faculdade e menciona seu nome. Isso comprova que ela foi enviada pela instituição?',
    'Informações pessoais e elementos visuais podem tornar uma fraude convincente. Confirme a identidade do remetente por um canal oficial antes de atender a pedidos.',
    2
FROM public.quizzes AS quiz
WHERE quiz.titulo = 'Phishing: aprenda antes de clicar'
ON CONFLICT (quiz_id, ordem) DO NOTHING;

INSERT INTO public.alternativas (
    questao_id,
    texto,
    correta,
    ordem
)
SELECT
    questao.id,
    opcao.texto,
    opcao.correta,
    opcao.ordem
FROM public.questoes AS questao
JOIN public.quizzes AS quiz
    ON quiz.id = questao.quiz_id
CROSS JOIN (
    VALUES
        (
            'Não. A aparência e os dados citados podem ser usados por golpistas.',
            TRUE,
            1
        ),
        (
            'Sim. Somente a faculdade pode colocar seu logotipo em mensagens.',
            FALSE,
            2
        ),
        (
            'Sim. Conhecer o nome do estudante comprova a identidade do remetente.',
            FALSE,
            3
        ),
        (
            'Não, porque toda comunicação verdadeira precisa chegar por carta.',
            FALSE,
            4
        )
) AS opcao (texto, correta, ordem)
WHERE quiz.titulo = 'Phishing: aprenda antes de clicar'
  AND questao.ordem = 2
ON CONFLICT (questao_id, ordem) DO NOTHING;

-- Phishing: aprenda antes de clicar: questão 3.
INSERT INTO public.questoes (
    quiz_id,
    enunciado,
    explicacao,
    ordem
)
SELECT
    quiz.id,
    'Você recebe um anexo chamado “Atualização de matrícula”, mas não esperava esse documento e não reconhece o remetente. O que deve fazer primeiro?',
    'Anexos inesperados podem conter programas maliciosos. Confirmar a origem antes de abrir reduz o risco de comprometer o dispositivo e os dados armazenados.',
    3
FROM public.quizzes AS quiz
WHERE quiz.titulo = 'Phishing: aprenda antes de clicar'
ON CONFLICT (quiz_id, ordem) DO NOTHING;

INSERT INTO public.alternativas (
    questao_id,
    texto,
    correta,
    ordem
)
SELECT
    questao.id,
    opcao.texto,
    opcao.correta,
    opcao.ordem
FROM public.questoes AS questao
JOIN public.quizzes AS quiz
    ON quiz.id = questao.quiz_id
CROSS JOIN (
    VALUES
        (
            'Abrir o arquivo para descobrir quem o enviou.',
            FALSE,
            1
        ),
        (
            'Encaminhar o anexo ao grupo da turma.',
            FALSE,
            2
        ),
        (
            'Desativar a proteção do computador caso ela impeça a abertura.',
            FALSE,
            3
        ),
        (
            'Confirmar o envio com a secretaria pelo contato oficial conhecido.',
            TRUE,
            4
        )
) AS opcao (texto, correta, ordem)
WHERE quiz.titulo = 'Phishing: aprenda antes de clicar'
  AND questao.ordem = 3
ON CONFLICT (questao_id, ordem) DO NOTHING;

-- Phishing: aprenda antes de clicar: questão 4.
INSERT INTO public.questoes (
    quiz_id,
    enunciado,
    explicacao,
    ordem
)
SELECT
    quiz.id,
    'Um colega envia um link de uma suposta bolsa de estudos. A página pede seu login e sua senha institucional. Qual é a melhor decisão?',
    'A conta de um conhecido pode estar comprometida, ou ele pode encaminhar um golpe sem perceber. A origem aparente da mensagem não substitui a verificação do endereço e da instituição.',
    4
FROM public.quizzes AS quiz
WHERE quiz.titulo = 'Phishing: aprenda antes de clicar'
ON CONFLICT (quiz_id, ordem) DO NOTHING;

INSERT INTO public.alternativas (
    questao_id,
    texto,
    correta,
    ordem
)
SELECT
    questao.id,
    opcao.texto,
    opcao.correta,
    opcao.ordem
FROM public.questoes AS questao
JOIN public.quizzes AS quiz
    ON quiz.id = questao.quiz_id
CROSS JOIN (
    VALUES
        (
            'Informar os dados porque a mensagem veio de um conhecido.',
            FALSE,
            1
        ),
        (
            'Verificar a oportunidade no canal oficial da instituição antes de fornecer dados.',
            TRUE,
            2
        ),
        (
            'Confiar na página se ela tiver imagens de estudantes.',
            FALSE,
            3
        ),
        (
            'Compartilhar o link para descobrir se outras pessoas conseguem entrar.',
            FALSE,
            4
        )
) AS opcao (texto, correta, ordem)
WHERE quiz.titulo = 'Phishing: aprenda antes de clicar'
  AND questao.ordem = 4
ON CONFLICT (questao_id, ordem) DO NOTHING;

-- Phishing: aprenda antes de clicar: questão 5.
INSERT INTO public.questoes (
    quiz_id,
    enunciado,
    explicacao,
    ordem
)
SELECT
    quiz.id,
    'Uma mensagem anuncia um sorteio de material escolar. Para participar, um formulário desconhecido exige foto do documento e senha do seu e-mail, sem explicar a necessidade dessas informações. Como agir?',
    'Pedidos excessivos ou sem finalidade clara merecem atenção. A LGPD estabelece que a coleta deve ser limitada ao necessário para sua finalidade. Nunca forneça a senha do seu e-mail em um formulário de sorteio e respeite também os dados de outras pessoas.',
    5
FROM public.quizzes AS quiz
WHERE quiz.titulo = 'Phishing: aprenda antes de clicar'
ON CONFLICT (quiz_id, ordem) DO NOTHING;

INSERT INTO public.alternativas (
    questao_id,
    texto,
    correta,
    ordem
)
SELECT
    questao.id,
    opcao.texto,
    opcao.correta,
    opcao.ordem
FROM public.questoes AS questao
JOIN public.quizzes AS quiz
    ON quiz.id = questao.quiz_id
CROSS JOIN (
    VALUES
        (
            'Preencher tudo porque os campos são obrigatórios.',
            FALSE,
            1
        ),
        (
            'Enviar os dados e pedir a exclusão depois.',
            FALSE,
            2
        ),
        (
            'Não enviar e verificar a legitimidade e a finalidade da coleta.',
            TRUE,
            3
        ),
        (
            'Fornecer os dados de um familiar para proteger os seus.',
            FALSE,
            4
        )
) AS opcao (texto, correta, ordem)
WHERE quiz.titulo = 'Phishing: aprenda antes de clicar'
  AND questao.ordem = 5
ON CONFLICT (questao_id, ordem) DO NOTHING;

-- Proteção de senhas e contas: questão 1.
INSERT INTO public.questoes (
    quiz_id,
    enunciado,
    explicacao,
    ordem
)
SELECT
    quiz.id,
    'Qual estratégia é mais adequada para criar uma senha?',
    'Comprimento e imprevisibilidade ajudam a proteger a senha. Dados pessoais, sequências e exemplos públicos facilitam tentativas de descoberta.',
    1
FROM public.quizzes AS quiz
WHERE quiz.titulo = 'Proteção de senhas e contas'
ON CONFLICT (quiz_id, ordem) DO NOTHING;

INSERT INTO public.alternativas (
    questao_id,
    texto,
    correta,
    ordem
)
SELECT
    questao.id,
    opcao.texto,
    opcao.correta,
    opcao.ordem
FROM public.questoes AS questao
JOIN public.quizzes AS quiz
    ON quiz.id = questao.quiz_id
CROSS JOIN (
    VALUES
        (
            'Usar o próprio nome seguido do ano de nascimento.',
            FALSE,
            1
        ),
        (
            'Criar uma senha longa, exclusiva e difícil de prever, sem dados pessoais.',
            TRUE,
            2
        ),
        (
            'Usar uma sequência do teclado para facilitar a memorização.',
            FALSE,
            3
        ),
        (
            'Copiar uma senha publicada como exemplo em uma aula.',
            FALSE,
            4
        )
) AS opcao (texto, correta, ordem)
WHERE quiz.titulo = 'Proteção de senhas e contas'
  AND questao.ordem = 1
ON CONFLICT (questao_id, ordem) DO NOTHING;

-- Proteção de senhas e contas: questão 2.
INSERT INTO public.questoes (
    quiz_id,
    enunciado,
    explicacao,
    ordem
)
SELECT
    quiz.id,
    'Uma pessoa usa a mesma senha no e-mail, na rede social e em uma loja virtual. Qual é o principal risco dessa prática?',
    'Uma senha descoberta pode ser testada em outras contas. Usar senhas diferentes reduz o impacto de um comprometimento.',
    2
FROM public.quizzes AS quiz
WHERE quiz.titulo = 'Proteção de senhas e contas'
ON CONFLICT (quiz_id, ordem) DO NOTHING;

INSERT INTO public.alternativas (
    questao_id,
    texto,
    correta,
    ordem
)
SELECT
    questao.id,
    opcao.texto,
    opcao.correta,
    opcao.ordem
FROM public.questoes AS questao
JOIN public.quizzes AS quiz
    ON quiz.id = questao.quiz_id
CROSS JOIN (
    VALUES
        (
            'O navegador deixa de aceitar a senha.',
            FALSE,
            1
        ),
        (
            'As contas passam a compartilhar automaticamente seus arquivos.',
            FALSE,
            2
        ),
        (
            'A senha perde caracteres cada vez que é utilizada.',
            FALSE,
            3
        ),
        (
            'A descoberta da senha em um serviço pode comprometer os demais.',
            TRUE,
            4
        )
) AS opcao (texto, correta, ordem)
WHERE quiz.titulo = 'Proteção de senhas e contas'
  AND questao.ordem = 2
ON CONFLICT (questao_id, ordem) DO NOTHING;

-- Proteção de senhas e contas: questão 3.
INSERT INTO public.questoes (
    quiz_id,
    enunciado,
    explicacao,
    ordem
)
SELECT
    quiz.id,
    'Para que serve ativar a verificação em duas etapas em uma conta?',
    'A segunda etapa acrescenta proteção caso a senha seja descoberta. Ela não elimina todos os riscos nem dispensa outros cuidados.',
    3
FROM public.quizzes AS quiz
WHERE quiz.titulo = 'Proteção de senhas e contas'
ON CONFLICT (quiz_id, ordem) DO NOTHING;

INSERT INTO public.alternativas (
    questao_id,
    texto,
    correta,
    ordem
)
SELECT
    questao.id,
    opcao.texto,
    opcao.correta,
    opcao.ordem
FROM public.questoes AS questao
JOIN public.quizzes AS quiz
    ON quiz.id = questao.quiz_id
CROSS JOIN (
    VALUES
        (
            'Acrescentar uma verificação além da senha para dificultar acessos indevidos.',
            TRUE,
            1
        ),
        (
            'Garantir que nenhuma tentativa de golpe terá sucesso.',
            FALSE,
            2
        ),
        (
            'Permitir compartilhar a senha sem qualquer risco.',
            FALSE,
            3
        ),
        (
            'Substituir a necessidade de atualizar o dispositivo.',
            FALSE,
            4
        )
) AS opcao (texto, correta, ordem)
WHERE quiz.titulo = 'Proteção de senhas e contas'
  AND questao.ordem = 3
ON CONFLICT (questao_id, ordem) DO NOTHING;

-- Proteção de senhas e contas: questão 4.
INSERT INTO public.questoes (
    quiz_id,
    enunciado,
    explicacao,
    ordem
)
SELECT
    quiz.id,
    'Alguém se apresenta como suporte de um aplicativo e pede que você envie o código de verificação recebido por SMS. Você não iniciou nenhum atendimento. Como agir?',
    'Códigos de verificação podem permitir acesso à conta. Um golpista pode se passar pelo suporte para obter essa informação e agir em seu nome.',
    4
FROM public.quizzes AS quiz
WHERE quiz.titulo = 'Proteção de senhas e contas'
ON CONFLICT (quiz_id, ordem) DO NOTHING;

INSERT INTO public.alternativas (
    questao_id,
    texto,
    correta,
    ordem
)
SELECT
    questao.id,
    opcao.texto,
    opcao.correta,
    opcao.ordem
FROM public.questoes AS questao
JOIN public.quizzes AS quiz
    ON quiz.id = questao.quiz_id
CROSS JOIN (
    VALUES
        (
            'Enviar o código se a pessoa souber seu nome.',
            FALSE,
            1
        ),
        (
            'Enviar apenas parte do código para testar o atendimento.',
            FALSE,
            2
        ),
        (
            'Não compartilhar o código e procurar o suporte pelo canal oficial.',
            TRUE,
            3
        ),
        (
            'Publicar o código no grupo da turma para pedir orientação.',
            FALSE,
            4
        )
) AS opcao (texto, correta, ordem)
WHERE quiz.titulo = 'Proteção de senhas e contas'
  AND questao.ordem = 4
ON CONFLICT (questao_id, ordem) DO NOTHING;

-- Proteção de senhas e contas: questão 5.
INSERT INTO public.questoes (
    quiz_id,
    enunciado,
    explicacao,
    ordem
)
SELECT
    quiz.id,
    'Você confirma, pelo canal oficial de um serviço, que sua senha foi exposta em um vazamento. O que deve fazer?',
    'Uma senha exposta deve ser substituída rapidamente em todos os lugares onde foi usada. Também é indicado revisar acessos e ativar a verificação em duas etapas.',
    5
FROM public.quizzes AS quiz
WHERE quiz.titulo = 'Proteção de senhas e contas'
ON CONFLICT (quiz_id, ordem) DO NOTHING;

INSERT INTO public.alternativas (
    questao_id,
    texto,
    correta,
    ordem
)
SELECT
    questao.id,
    opcao.texto,
    opcao.correta,
    opcao.ordem
FROM public.questoes AS questao
JOIN public.quizzes AS quiz
    ON quiz.id = questao.quiz_id
CROSS JOIN (
    VALUES
        (
            'Aguardar um acesso indevido antes de tomar providências.',
            FALSE,
            1
        ),
        (
            'Trocar a senha no serviço e onde ela foi repetida, usando senhas diferentes.',
            TRUE,
            2
        ),
        (
            'Trocar apenas a foto e o nome do perfil.',
            FALSE,
            3
        ),
        (
            'Enviar a senha antiga aos amigos para que verifiquem o vazamento.',
            FALSE,
            4
        )
) AS opcao (texto, correta, ordem)
WHERE quiz.titulo = 'Proteção de senhas e contas'
  AND questao.ordem = 5
ON CONFLICT (questao_id, ordem) DO NOTHING;

-- Confere a carga antes de confirmar a transação.
-- Não altera perguntas ou alternativas já existentes.
DO $$
BEGIN
    IF EXISTS (
        SELECT esperado.titulo
        FROM (VALUES
            ('Phishing: aprenda antes de clicar'),
            ('Proteção de senhas e contas')
        ) AS esperado(titulo)
        LEFT JOIN public.quizzes AS quiz ON quiz.titulo = esperado.titulo
        GROUP BY esperado.titulo
        HAVING count(quiz.id) <> 1
    ) THEN
        RAISE EXCEPTION 'A carga precisa de exatamente um quiz para cada título.';
    END IF;

    IF EXISTS (
        SELECT quiz.id
        FROM public.quizzes AS quiz
        LEFT JOIN public.questoes AS questao ON questao.quiz_id = quiz.id
        WHERE quiz.titulo IN (
            'Phishing: aprenda antes de clicar',
            'Proteção de senhas e contas'
        )
        GROUP BY quiz.id
        HAVING count(questao.id) <> 5
            OR min(questao.ordem) <> 1 OR max(questao.ordem) <> 5
    ) THEN
        RAISE EXCEPTION 'Cada quiz precisa de cinco questões, numeradas de 1 a 5.';
    END IF;

    IF EXISTS (
        SELECT questao.id
        FROM public.questoes AS questao
        JOIN public.quizzes AS quiz ON quiz.id = questao.quiz_id
        LEFT JOIN public.alternativas AS alternativa
            ON alternativa.questao_id = questao.id
        WHERE quiz.titulo IN (
            'Phishing: aprenda antes de clicar',
            'Proteção de senhas e contas'
        )
        GROUP BY questao.id
        HAVING count(alternativa.id) <> 4
            OR min(alternativa.ordem) <> 1 OR max(alternativa.ordem) <> 4
            OR count(alternativa.id) FILTER (WHERE alternativa.correta) <> 1
    ) THEN
        RAISE EXCEPTION 'Cada questão precisa de quatro alternativas, de 1 a 4, e uma correta.';
    END IF;
END;
$$;

COMMIT;
