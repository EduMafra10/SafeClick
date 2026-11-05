# Estimativa local de força — SafeClick

Esta pasta contém a fonte legível e as dependências usadas para gerar o estimador. A aplicação Flask usa o JavaScript já compilado em `safeclick/static/js/vendor/forca-senha.js`; não precisa de Node.js para executar a funcionalidade.

## Responsabilidades

- `estimador.mjs`: configura zxcvbn-ts com padrões de teclado e dicionários comum, inglês e português do Brasil. `avaliar(senha)` retorna somente nível de 0 a 4, rótulo e orientações fixas. Não retorna senha, hash, trechos reconhecidos ou tempos de quebra.
- `compilar.mjs`: gera um arquivo local para o navegador, licenças e manifesto SHA-256. Não consulta a API Pwned Passwords.
- `teste-estimador.mjs`: testa padrões comuns, entradas, separação de vazamentos e o contrato do arquivo compilado.
- `package-lock.json`: fixa as versões e a integridade das dependências.
- `../../safeclick/static/js/forca_senha_worker.js`: executa a análise em um Web Worker, em segundo plano no navegador. Recebe `{id, senha}` e devolve `{id, avaliacao}` ou um erro genérico. Não envia requisições de consulta.

## Significado do resultado

0 = Muito fraca; 1 = Fraca; 2 = Moderada; 3 = Boa; 4 = Forte.

São estimativas de dificuldade de adivinhação, não garantias de segurança. O estimador não sabe onde a senha é usada, se foi reutilizada nem se apareceu em um vazamento. A consulta existente ao Pwned Passwords continua separada, apenas no envio explícito do formulário.

O campo mantém o limite já existente de 128 caracteres JavaScript. Não há remoção de espaços nem normalização de acentos. As regras de criação de senha da conta não são alteradas.

## Recompilar (somente para desenvolvimento)

Com Node.js e npm instalados, execute nesta pasta:

```powershell
npm ci --ignore-scripts --no-audit --no-fund
npm run build
npm test
```

O primeiro comando baixa as dependências públicas. Os outros comandos trabalham localmente. `node_modules` é ignorada pelo Git; os arquivos compilados, as licenças, o manifesto, a fonte e o lockfile devem acompanhar o projeto.

## Integração da interface

Esta primeira etapa fornece a base. O JavaScript da tela ainda precisa iniciar o worker, aguardar uma pausa na digitação, ignorar respostas de consultas antigas, limpar o estado ao sair e apresentar a nota como estimativa. As orientações após a consulta devem dar prioridade ao resultado “encontrada” mesmo quando a estimativa de força for alta.

Não carregar este estimador por CDN, não salvar senhas/resultados em armazenamento local e não adicionar informações da análise ao POST da rota de vazamentos. O POST continua recebendo somente prefixo e CSRF.

Fonte da biblioteca: https://github.com/zxcvbn-ts/zxcvbn

Documentação: https://zxcvbn-ts.github.io/zxcvbn/guide/getting-started/

Licenças dos componentes incluídos: `safeclick/static/js/vendor/forca-senha.LICENSE.txt`.
