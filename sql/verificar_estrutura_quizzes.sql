SELECT current_database() AS banco, current_schema() AS esquema;

SELECT table_schema, table_name, table_type
FROM information_schema.tables
WHERE table_name IN (
    'quizzes', 'questoes', 'alternativas',
    'tentativas_quiz', 'respostas_tentativa_quiz'
)
ORDER BY table_schema, table_name;

SELECT table_name, column_name, data_type, is_nullable, is_identity,
       column_default
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name IN (
      'quizzes', 'questoes', 'alternativas',
      'tentativas_quiz', 'respostas_tentativa_quiz'
  )
ORDER BY table_name, ordinal_position;

SELECT tabela.relname AS tabela, regra.conname AS restricao,
       pg_catalog.pg_get_constraintdef(regra.oid) AS definicao
FROM pg_catalog.pg_constraint AS regra
JOIN pg_catalog.pg_class AS tabela ON tabela.oid = regra.conrelid
JOIN pg_catalog.pg_namespace AS esquema ON esquema.oid = tabela.relnamespace
WHERE esquema.nspname = 'public'
  AND tabela.relname IN (
      'quizzes', 'questoes', 'alternativas',
      'tentativas_quiz', 'respostas_tentativa_quiz'
  )
ORDER BY tabela.relname, regra.conname;

SELECT indexname, indexdef
FROM pg_catalog.pg_indexes
WHERE schemaname = 'public'
  AND indexname = 'alternativas_uma_correta_por_questao';
