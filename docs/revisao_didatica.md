# Revisão dos conteúdos, quizzes e Oficina SafeClick

Revisão de 15/11/2026 sobre a cópia de trabalho da branch `entrega0911` e o catálogo do Neon configurado no projeto.

## Material analisado e estrutura

Foram lidos integralmente os nove textos educativos completos publicados, os cinco quizzes de perguntas e respostas, as seis oficinas, as mensagens, escolhas e explicações das quatro simulações publicadas e as instruções do Laboratório de Senhas. Também foram conferidos o cadastro dos materiais, os rascunhos existentes, as cargas SQL, os modelos de páginas, a correção, a persistência das respostas e a apresentação dos resultados.

O catálogo tem um décimo texto publicado, no endereço `golpes-por-mensagem1`, cujo corpo inteiro é “Apenas um teste”. Esse item não oferece material de ensino suficiente. O cenário `falso-suporte-tecnico` está em rascunho, sem uma versão publicada. Nenhum deles foi usado como pré-requisito de avaliação. A equipe deve decidir se completa ou despublica o texto de teste e se conclui o cenário.

Não foram encontrados módulos de aulas independentes nesse catálogo. A organização atual é por conteúdos, quizzes, oficinas, simulações e laboratório. Materiais de Teams, aulas externas e documentos não presentes nesta cópia de trabalho não fazem parte desta revisão.

A aplicação usa Flask, templates Jinja, CSS e JavaScript próprios e PostgreSQL no Neon. Os textos são armazenados em `conteudos`. Quizzes usam `catalogo_quizzes` como identidade pública, `quizzes` como edição publicada e `questoes` e `alternativas` como itens dessa edição. Simulações também têm versões. Os arquivos de carga inicial não são a fonte definitiva do material atualmente publicado.

Os principais pontos da implementação conferidos foram:

- `safeclick/conteudos.py` e `conteudos_db.py` para listar, exibir e concluir leituras.
- `safeclick/catalogo_admin.py`, `catalogo_admin_db.py` e `catalogo_validacao.py` para gestão, validação e publicação.
- `safeclick/quizzes.py` para formulários, correção, tentativas, resultados e guia de revisão.
- `templates/quizzes/` e `static/js/oficina_quiz.js` para perguntas verticais e associação de cartões.
- `templates/laboratorio_senhas.html`, `desafio_senhas.py` e JavaScript do laboratório para o material complementar.
- `painel_db.py`, avaliações e auditoria para conferir a continuidade do histórico e das referências.

## Problemas identificados e correções

| Encontrado | Tratamento realizado |
| --- | --- |
| Os dois quizzes originais tinham somente explicação geral por pergunta. | Explicações para todas as alternativas, inclusive as incorretas. Alguns distratores absurdos foram substituídos por erros de compreensão plausíveis. |
| Leitura de senhas orientava 12 caracteres e mistura obrigatória de tipos, enquanto laboratório e cadastro atuais usam 15. | Texto e gabarito passam a priorizar comprimento, imprevisibilidade e exclusividade. A referência educativa é 15 caracteres, sem apresentar tamanho ou símbolos como garantia isolada. |
| Texto de mensagens chamava todo phishing por celular de smishing. | Smishing fica delimitado ao SMS; phishing por aplicativos continua explicado como outro canal. |
| Texto de falso conhecido sugeria pergunta pessoal como confirmação suficiente, em divergência com a simulação. | Confirmar por contato independente conhecido; dados pessoais e palavra-chave não substituem essa verificação. |
| Orientações de MED e cartão poderiam gerar expectativa excessiva de recuperação. | Solicitá-los não é apresentado como garantia de devolução ou de reembolso automático. |
| HTTPS era explicado na simulação, mas não na leitura de compras. | Pequeno complemento na leitura distingue proteção da conexão de legitimidade do vendedor. |
| Limites de eliminação e portabilidade estavam pouco claros. | Texto de privacidade distingue solicitação de resultado irrestrito e considera conservação e limites legais. Não constitui parecer jurídico. |
| Material usava a denominação anterior da ANPD. | Atualização para Agência Nacional de Proteção de Dados, conforme sua base jurídica atual. |
| A descrição do backup podia ser entendida como prevenção de infecção. | Esclarece recuperação, proteção das cópias e complementaridade com atualizações e outros cuidados. |
| Não havia avaliação sobre o uso educativo do laboratório. | Novo quiz e nova oficina sobre ideias fictícias, estimativa, geração local e comparação de exemplos públicos. |
| Oficinas tinham três trechos e exatamente três cartões; o último encaixe podia ser deduzido sem compreensão. | Cinco trechos e seis cartões por oficina, com um excedente, sem repetir cartões usados e com posições de gabarito variadas. Os excedentes descrevem conceitos válidos de outro contexto, para exigir distinguir sua finalidade. |
| Poucos itens sobre permissões, dados sensíveis, canais de direitos e diferenças entre malware. | Novo quiz específico de privacidade e ampliação das atividades existentes. |

Os seis textos que receberam ajustes pontuais são Proteção de Senhas, Golpes por SMS e mensagens, Golpe do falso conhecido e Pix, Compras online seguras, Privacidade e seus dados pessoais e Códigos maliciosos e atualizações. Seus slugs e a organização em títulos, listas e destaques foram preservados.

## Cobertura e organização das avaliações

| Material | Cobertura de perguntas e trechos na revisão | Atividades diferentes |
| --- | ---: | ---: |
| Phishing | 8 | 3 |
| Proteção de Senhas | 7 | 3 |
| Golpes por SMS e mensagens | 6 | 2 |
| Golpe do falso conhecido e Pix | 8 | 2 |
| Compras online seguras | 7 | 2 |
| Verificação em duas etapas | 7 | 3 |
| Vazamento de dados | 5 | 3 |
| Privacidade e seus dados pessoais | 12 | 4 |
| Códigos maliciosos e atualizações | 10 | 3 |
| Laboratório de Senhas | 12 | 3 |

Há 47 perguntas de múltipla escolha e 35 trechos de oficina, totalizando 82 itens. Antes havia 25 perguntas e 18 trechos, totalizando 43. Foram acrescentados 39 itens educativos e revisadas as 11 atividades anteriores.

Os cinco quizzes anteriores passam de cinco para sete perguntas. As seis oficinas anteriores passam de três para cinco trechos. As novas atividades são:

1. **Privacidade na prática: dados, permissões e direitos** — seis perguntas.
2. **Laboratório de senhas: interpretar, gerar e revisar** — seis perguntas.
3. **Laboratório: ideia de senha, estimativa e exemplos públicos** — oficina com cinco trechos.

Os exercícios combinam definição, distinção de conceitos, leitura de sinais, aplicação de cuidados e interpretação de resultados. Cada pergunta tradicional tem uma correta e três incorretas. As oficinas mantêm o mesmo banco de cartões em todos os trechos e um cartão correto distinto por trecho. As 398 alternativas/cartões das atividades têm explicação específica para a escolha e o contexto da questão. A tabela de cobertura considera o objetivo principal de cada pergunta ou trecho; a matriz também identifica a fonte do cartão excedente de cada oficina.

Os níveis registrados são **compreensão** e **aplicação**. Essa classificação é uma análise editorial, não uma medição empírica de dificuldade. Não há nota de corte nova, classificação pública de participantes ou comprovação automática de aprendizagem. A adequação da dificuldade deve ser confirmada com o público do projeto.

As questões sobre direitos se limitam aos exemplos e orientações estudados. Não exigem decorar artigos, prazos de procedimentos administrativos ou detalhes técnicos que não tenham sido ensinados. O prazo de sete dias da oficina de compras é explicitamente aplicado ao exemplo do produto recebido, sem generalização a todos os contratos.

A correspondência de **cada questão** com material, seção, objetivo e nível está em [matriz.json](../dados/revisao_didatica/matriz.json). Os gabaritos e feedbacks completos ficam em [01_quizzes.json](../dados/revisao_didatica/01_quizzes.json) e [02_oficinas.json](../dados/revisao_didatica/02_oficinas.json). Os textos corrigidos, no formato aceito pelo editor, estão em [conteudos_revisados.json](../dados/revisao_didatica/conteudos_revisados.json).

## Publicação e manutenção

A revisão usa o serviço existente de gestão do catálogo. Cada edição de quiz salva um rascunho e publica uma nova versão, sem alterar diretamente questões antigas. Nos textos, a publicação atualiza o corpo e o número da versão, mantendo o identificador e as conclusões vinculadas. A autoria é registrada na auditoria, com `catalogo.editado`, `catalogo.criado` e `catalogo.publicado`. A aplicação desta revisão foi feita com a conta administrativa de ID 15, indicada pelo responsável.

O script de manutenção [aplicar_revisao_didatica.py](../scripts/aplicar_revisao_didatica.py) usa os mesmos validadores e operações da gestão. Não requer migração de esquema adicional no ambiente já preparado para catálogo e oficinas.

Para conferir outro ambiente, execute na raiz do projeto, com as variáveis de ambiente e a conexão autorizada configuradas:

```powershell
.\.venv\Scripts\python.exe scripts/aplicar_revisao_didatica.py
```

O comando acima só apresenta o plano. Para aplicar uma revisão aprovada, informe a conta administrativa responsável:

```powershell
.\.venv\Scripts\python.exe scripts/aplicar_revisao_didatica.py --aplicar --administrador-id 15
```

O número é o ID da conta administradora **desse banco**. A permissão é conferida no servidor. O script verifica se o conteúdo continua igual ao analisado, bloqueia rascunhos diferentes e itens retirados pela equipe e usa o controle de revisão do catálogo. Reexecutar sobre a mesma revisão publicada não cria cópias nem novas versões. Um rascunho idêntico deixado por interrupção pode ser retomado. As transações são as das operações existentes, por item; uma interrupção não reverte itens já publicados. Confira a gestão e execute a conferência novamente antes de retomar.

Se o comando detectar alteração posterior da equipe, revise o material pelo editor administrativo e atualize os dados e a matriz após a revisão. Não substitua os hashes para forçar uma publicação sem conferir a diferença.

Os dois arquivos de quizzes também são aceitos em **Gestão de conteúdo → Quizzes → Importar rascunhos**. O importador preserva títulos existentes; ele não atualiza os quizzes já cadastrados. Para esses casos, use o editor ou a manutenção descrita acima. Não reaplique as cargas SQL iniciais sobre o catálogo em uso.

## Verificação

Os testes em `tests/test_revisao_didatica.py` verificam validade dos lotes, cobertura e referências, gabarito único, feedback de todas as opções, cartões excedentes, publicação com autoria, bloqueio de conflitos e falta de permissão. Também passam todas as atividades pelos formulários reais do Flask, pela correção, pelo contrato de gravação e pela tela de resultado, tanto com tudo certo quanto com tudo errado. Nesses testes, o acesso a banco real é bloqueado.

```powershell
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
```

A suíte completa passou com **436 testes e 1.234 subtestes**. Os 27 avisos são de depreciação de campos de escolha do WTForms usados nas avaliações.

Além dos testes isolados, a validação do Neon confere a igualdade dos 20 itens com a revisão, a correção dos 14 quizzes/oficinas usando seus gabaritos publicados e a preservação das questões das versões anteriores. A gravação de tentativas, respostas, evento de conclusão e reenvio idempotente é exercitada em transações revertidas, sem acrescentar tentativas de demonstração ao histórico do usuário.

Essa conferência foi concluída com 28 correções reais, uma com tudo certo e outra com tudo errado por atividade. Foram confirmados 3 eventos de criação, 25 de edição e 28 de publicação da revisão, incluindo a correção final da denominação da ANPD no texto de privacidade e o refinamento dos cartões excedentes. Permaneceram as 20 tentativas e 90 respostas anteriores. A consulta de conferência passou a indicar os 20 itens como inalterados, confirmando que uma repetição não exige nova publicação.

Para conferir no navegador, entre em `/quizzes/`, abra uma atividade de cada formato, responda e revise as explicações. A oficina permite deixar o cartão excedente sem uso. Confira “Meu guia de revisão”, “Tentar novamente”, os links para a próxima atividade e o painel de progresso. Na administração, os itens e suas versões estão em `/administracao/catalogo/quizzes`, e as publicações podem ser consultadas nos logs de auditoria.

O teste automatizado e a verificação de banco não substituem uma rodada de avaliação com estudantes nem a validação do orientador. Não foi realizada uma nova sessão de login com autenticador ou uma avaliação humana de usabilidade neste trabalho.

## Fontes oficiais conferidas

- [CERT.br — Autenticação](https://cartilha.cert.br/fasciculos/autenticacao/), para os cuidados com credenciais e segundo fator.
- [NIST SP 800-63B-4, seção 3.1.1](https://pages.nist.gov/800-63-4/sp800-63b.html), para contextualizar comprimento e regras de composição. O documento distingue senha como fator único e uso com múltiplos fatores; a referência educativa do projeto não deve ser apresentada como regra universal.
- [GSI — OSIC 01/2023](https://www.gov.br/gsi/pt-br/seguranca-da-informacao-e-cibernetica/osic/copy_of_osic-01-2023), para a delimitação de smishing.
- [Banco Central — Mecanismo Especial de Devolução](https://www.bcb.gov.br/meubc/faqs/p/o-que-e-e-como-funciona-o-mecanismo-especial-de-devolucao-med), para a orientação de acionar a instituição diante de golpe com Pix.
- [ANPD — Direitos dos titulares](https://www.gov.br/anpd/pt-br/assuntos/titular-de-dados/direito-dos-titulares), para os direitos e os limites de eliminação.
- [ANPD — Base jurídica](https://www.gov.br/anpd/pt-br/acesso-a-informacao/institucional/base-juridica), para a denominação atual de Agência Nacional de Proteção de Dados.
- [Código de Defesa do Consumidor, artigo 49](https://www.planalto.gov.br/ccivil_03/leis/l8078compilado.htm), para o exemplo de arrependimento.
- [CERT.br — Ransomware](https://cartilha.cert.br/ransomware/), para distinguir prevenção e recuperação por backup.

As referências complementam os materiais do projeto. Os textos revisados permanecem educativos; não prometem segurança absoluta, recuperação garantida de valores ou conformidade jurídica automática.
