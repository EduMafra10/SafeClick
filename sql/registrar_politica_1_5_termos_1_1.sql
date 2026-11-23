BEGIN;

INSERT INTO public.referencias_legais (norma, dispositivo, assunto, url)
VALUES ('Lei nº 13.709/2018 (LGPD)', 'art. 7º, I, e art. 8º',
        'Base legal: consentimento, prova do consentimento e revogação',
        'https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm')
ON CONFLICT ON CONSTRAINT referencias_legais_unica DO NOTHING;

DO $registrar_politica_1_5$
DECLARE
    texto_politica CONSTANT TEXT := $conteudo_politica_1_5$<h1>Política de Privacidade</h1>
        <p class="privacidade-meta">Versão 1.5 · vigente desde 16/11/2026</p>
        <nav class="privacidade-sumario" aria-label="Seções">
            <p>Nesta página</p>
            <ol>
                <li><a href="#1-quem-somos-e-quem-cuida-dos-seus-dados">1. Quem somos e quem cuida dos seus dados</a></li>
                <li><a href="#2-quais-dados-tratamos">2. Quais dados tratamos</a></li>
                <li><a href="#3-para-que-usamos-os-dados-e-com-qual-base-legal">3. Para que usamos os dados e com qual base legal</a></li>
                <li><a href="#4-adolescentes">4. Adolescentes</a></li>
                <li><a href="#5-cookies">5. Cookies</a></li>
                <li><a href="#6-com-quem-compartilhamos">6. Com quem compartilhamos</a></li>
                <li><a href="#7-transferencia-internacional">7. Transferência internacional</a></li>
                <li><a href="#8-por-quanto-tempo-guardamos">8. Por quanto tempo guardamos</a></li>
                <li><a href="#9-seus-direitos">9. Seus direitos</a></li>
                <li><a href="#10-seguranca">10. Segurança</a></li>
                <li><a href="#11-alteracoes-nesta-politica">11. Alterações nesta política</a></li>
                <li><a href="#12-avaliacoes">12. Avaliações de conteúdos e quizzes</a></li>
            </ol>
        </nav>
        <section class="privacidade-resumo" aria-labelledby="resumo">
            <h2 id="resumo">Resumo em linguagem simples</h2>
            <ul>
                <li>Para usar o SafeClick é preciso criar uma conta e ter <strong>16 anos ou mais</strong>.</li>
                <li>Guardamos só o necessário: como você quer ser chamado, seu e-mail, sua senha e o que você faz na plataforma (conteúdos concluídos, quizzes, simulações, desafio de senhas e conquistas). A senha é guardada embaralhada (hash): nem a equipe consegue lê-la.</li>
                <li>O login tem uma segunda etapa com um aplicativo autenticador no celular. A empresa que confere esses códigos (Twilio) recebe só um identificador aleatório, nunca seu nome, e-mail ou senha.</li>
                <li>Não vendemos seus dados, não mostramos anúncios e não usamos cookies de rastreamento. Seu progresso e seus resultados são privados. Se quiser, você pode avaliar conteúdos e quizzes: a avaliação fica privada, a menos que você autorize publicá-la, sem o seu nome (seção 12).</li>
                <li>Em <strong>Minha conta</strong> você corrige seu nome, troca a senha e exclui a conta. Depois de excluir, você tem <strong>30 dias</strong> para voltar atrás pelo link enviado ao seu e-mail; passado esse prazo, nome e senha são apagados de vez, e o e-mail fica guardado por mais 6 meses, visível só para a administração.</li>
                <li>Para ver ou receber uma cópia dos seus dados, ou para qualquer outro pedido, escreva para <a href="mailto:safeclick.privacidade@gmail.com">safeclick.privacidade@gmail.com</a>.</li>
                <li>O SafeClick é um projeto acadêmico: as contas criadas durante testes e validação serão apagadas até 31/12/2026.</li>
            </ul>
        </section>

        <h2 id="1-quem-somos-e-quem-cuida-dos-seus-dados">1. Quem somos e quem cuida dos seus dados</h2>
        <p>O SafeClick é uma plataforma educativa de segurança digital desenvolvida como Projeto Final de Curso (PFC) do Bacharelado em Sistemas de Informação da Universidade de Mogi das Cruzes (UMC), pelos estudantes Eduardo Mafra dos Santos, Humberto Ribeiro Bezerra e João Henrique Alves de Souza.</p>
        <p><strong>Controlador.</strong> Durante o PFC, a equipe desenvolvedora decide como os dados são tratados e atua como controladora (art. 5º, VI, da Lei nº 13.709/2018 – LGPD). Em uma implantação real, por exemplo se uma escola ou universidade adotasse o SafeClick para seus estudantes, a instituição passaria a ser a controladora e deveria validar esta política com sua assessoria jurídica.</p>
        <p><strong>Operadores.</strong> Empresas que tratam dados em nosso nome, apenas para fazer a plataforma funcionar, estão listadas na seção 6.</p>
        <p><strong>Canal de privacidade.</strong> João Souza responde pelo canal <a href="mailto:safeclick.privacidade@gmail.com">safeclick.privacidade@gmail.com</a>, que recebe dúvidas, pedidos e reclamações sobre dados pessoais (art. 41 da LGPD).</p>

        <h2 id="2-quais-dados-tratamos">2. Quais dados tratamos</h2>
        <div class="privacidade-tabela" role="region" aria-label="Tabela" tabindex="0">
            <table>
                <thead><tr><th scope="col">Dado</th><th scope="col">Quando é coletado</th><th scope="col">Obrigatório?</th><th scope="col">Situação</th></tr></thead>
                <tbody>
                    <tr><td data-rotulo="Dado">Nome ou apelido (como você quer ser chamado)</td><td data-rotulo="Quando é coletado">Cadastro e Minha conta</td><td data-rotulo="Obrigatório?">Sim</td><td data-rotulo="Situação">Em funcionamento</td></tr>
                    <tr><td data-rotulo="Dado">Ícone de perfil, escolhido entre os personagens desenhados pelo SafeClick (não é foto)</td><td data-rotulo="Quando é coletado">Minha conta</td><td data-rotulo="Obrigatório?">Opcional</td><td data-rotulo="Situação">Em funcionamento</td></tr>
                    <tr><td data-rotulo="Dado">E-mail</td><td data-rotulo="Quando é coletado">Cadastro e login</td><td data-rotulo="Obrigatório?">Sim</td><td data-rotulo="Situação">Em funcionamento</td></tr>
                    <tr><td data-rotulo="Dado">Senha, guardada somente como hash scrypt</td><td data-rotulo="Quando é coletado">Cadastro e login</td><td data-rotulo="Obrigatório?">Sim</td><td data-rotulo="Situação">Em funcionamento</td></tr>
                    <tr><td data-rotulo="Dado">Perfil de acesso (usuário ou administrador), data de criação da conta e, quando houver, datas do pedido de exclusão e da exclusão</td><td data-rotulo="Quando é coletado">Definidos pelo sistema</td><td data-rotulo="Obrigatório?">Automático</td><td data-rotulo="Situação">Em funcionamento</td></tr>
                    <tr><td data-rotulo="Dado">Vínculo com o aplicativo autenticador: identificador aleatório, código do fator na Twilio e data de confirmação</td><td data-rotulo="Quando é coletado">Configuração do segundo fator</td><td data-rotulo="Obrigatório?">Sim</td><td data-rotulo="Situação">Em funcionamento</td></tr>
                    <tr><td data-rotulo="Dado">Sessão de acesso: identificador guardado só como hash, datas de início, última atividade e expiração</td><td data-rotulo="Quando é coletado">Login</td><td data-rotulo="Obrigatório?">Automático</td><td data-rotulo="Situação">Em funcionamento</td></tr>
                    <tr><td data-rotulo="Dado">Etapa de login em andamento: identificador temporário (hash) e número de tentativas do código</td><td data-rotulo="Quando é coletado">Entre a senha e o código do autenticador</td><td data-rotulo="Obrigatório?">Automático</td><td data-rotulo="Situação">Em funcionamento</td></tr>
                    <tr><td data-rotulo="Dado">Controle de tentativas: e-mail digitado, número da conta ou endereço IP, sempre transformados em código irreversível (HMAC), e contador</td><td data-rotulo="Quando é coletado">Login, configuração do autenticador, recuperação e troca de senha, exclusão e reativação da conta e desafio de senhas</td><td data-rotulo="Obrigatório?">Automático</td><td data-rotulo="Situação">Em funcionamento</td></tr>
                    <tr><td data-rotulo="Dado">Conteúdos concluídos: conteúdo e data</td><td data-rotulo="Quando é coletado">Ao marcar um conteúdo como concluído</td><td data-rotulo="Obrigatório?">Automático</td><td data-rotulo="Situação">Em funcionamento</td></tr>
                    <tr><td data-rotulo="Dado">Tentativas de quizzes: quiz, alternativas escolhidas, pontuação e data</td><td data-rotulo="Quando é coletado">Envio de um quiz</td><td data-rotulo="Obrigatório?">Automático</td><td data-rotulo="Situação">Em funcionamento</td></tr>
                    <tr><td data-rotulo="Dado">Escolhas nas simulações: simulação, opção escolhida e data</td><td data-rotulo="Quando é coletado">Uso de uma simulação</td><td data-rotulo="Obrigatório?">Automático</td><td data-rotulo="Situação">Em funcionamento</td></tr>
                    <tr><td data-rotulo="Dado">Cookie de sessão</td><td data-rotulo="Quando é coletado">Navegação e login</td><td data-rotulo="Obrigatório?">Necessário</td><td data-rotulo="Situação">Em funcionamento</td></tr>
                    <tr><td data-rotulo="Dado">Versão e data do aceite dos Termos, com declaração de idade</td><td data-rotulo="Quando é coletado">Cadastro</td><td data-rotulo="Obrigatório?">Sim</td><td data-rotulo="Situação">Em funcionamento</td></tr>
                    <tr><td data-rotulo="Dado">Registros de auditoria: identificador da conta, tipo de evento, resultado, data/hora e, nas ações da administração, o item afetado; quando um administrador exclui a conta de outro, também o motivo informado</td><td data-rotulo="Quando é coletado">Ações de acesso (cadastro, login, logout, troca de senha, exclusão e reativação da conta), de aprendizagem (conteúdos, quizzes, simulações, desafio de senhas e avaliações) e da administração, incluindo a moderação de comentários</td><td data-rotulo="Obrigatório?">Automático</td><td data-rotulo="Situação">Em funcionamento</td></tr>
                    <tr><td data-rotulo="Dado">Senha digitada no analisador de força do laboratório: avaliada só no seu navegador, não é enviada ao servidor nem armazenada</td><td data-rotulo="Quando é coletado">Ao usar o analisador</td><td data-rotulo="Obrigatório?">Opcional</td><td data-rotulo="Situação">Em funcionamento</td></tr>
                    <tr><td data-rotulo="Dado">Resultado do desafio "Qual vazou mais?": acertos, total de rodadas e data</td><td data-rotulo="Quando é coletado">Ao terminar uma partida</td><td data-rotulo="Obrigatório?">Automático</td><td data-rotulo="Situação">Em funcionamento</td></tr>
                    <tr><td data-rotulo="Dado">Token de recuperação de senha, guardado como hash e válido por 30 minutos</td><td data-rotulo="Quando é coletado">Pedido de recuperação de senha</td><td data-rotulo="Obrigatório?">Automático</td><td data-rotulo="Situação">Em funcionamento</td></tr>
                    <tr><td data-rotulo="Dado">Conquistas: conquista liberada e data</td><td data-rotulo="Quando é coletado">Uso da conta</td><td data-rotulo="Obrigatório?">Automático</td><td data-rotulo="Situação">Em funcionamento</td></tr>
                    <tr><td data-rotulo="Dado">Link de reativação da conta, guardado como hash e válido até o fim do prazo de 30 dias</td><td data-rotulo="Quando é coletado">Pedido de exclusão da conta ou tentativa de login nesse prazo</td><td data-rotulo="Obrigatório?">Automático</td><td data-rotulo="Situação">Em funcionamento</td></tr>
                    <tr><td data-rotulo="Dado">E-mail da conta excluída, guardado à parte e visível só para a administração</td><td data-rotulo="Quando é coletado">Exclusão definitiva da conta</td><td data-rotulo="Obrigatório?">Automático</td><td data-rotulo="Situação">Em funcionamento</td></tr>
                    <tr><td data-rotulo="Dado">Avaliações de conteúdos e quizzes: nota de 1 a 5, comentário opcional de até 500 caracteres e situação da moderação; se você autorizar a publicação, também a sua escolha, a declaração de ter 18 anos ou mais, a versão do aviso de publicação e a data da autorização</td><td data-rotulo="Quando é coletado">Depois de concluir um conteúdo ou quiz</td><td data-rotulo="Obrigatório?">Opcional</td><td data-rotulo="Situação">Em funcionamento</td></tr>
                </tbody>
            </table>
        </div>
        <p>O código de 6 dígitos do aplicativo autenticador é enviado para conferência e não é guardado. O QR Code usado para configurar o autenticador é gerado no nosso próprio servidor.</p>
        <p><strong>Não coletamos</strong> CPF, data de nascimento, endereço, telefone, fotografia, localização nem dados pessoais sensíveis (art. 5º, II, da LGPD). Nosso banco de dados não grava endereço IP em texto: ele só entra no controle de tentativas, transformado em código irreversível. A empresa de hospedagem (seção 6) pode registrar dados técnicos das requisições, como o IP, em seus registros de funcionamento.</p>

        <h2 id="3-para-que-usamos-os-dados-e-com-qual-base-legal">3. Para que usamos os dados e com qual base legal</h2>
        <div class="privacidade-tabela" role="region" aria-label="Tabela" tabindex="0">
            <table>
                <thead><tr><th scope="col">Finalidade</th><th scope="col">Dados usados</th><th scope="col">Base legal (LGPD)</th></tr></thead>
                <tbody>
                    <tr><td data-rotulo="Finalidade">Criar e manter sua conta, confirmar sua identidade no login (senha e segundo fator), proteger sua sessão e permitir que você gerencie a conta em Minha conta</td><td data-rotulo="Dados usados">Nome ou apelido, ícone, e-mail, hash da senha, perfil, vínculo com o autenticador, sessão, etapa de login e cookie de sessão</td><td data-rotulo="Base legal (LGPD)">Execução de contrato: os Termos de Uso aceitos no cadastro (art. 7º, V)</td></tr>
                    <tr><td data-rotulo="Finalidade">Registrar suas atividades, liberar conquistas, mostrar o seu progresso no painel e avaliar, de forma agregada e sem identificar pessoas, se os conteúdos ensinam bem</td><td data-rotulo="Dados usados">Conteúdos concluídos, tentativas de quizzes, escolhas nas simulações, resultados do desafio de senhas e conquistas</td><td data-rotulo="Base legal (LGPD)">Execução de contrato (art. 7º, V)</td></tr>
                    <tr><td data-rotulo="Finalidade">Limitar tentativas em ações sensíveis, para impedir ataques de adivinhação de senha e abuso dos links enviados por e-mail</td><td data-rotulo="Dados usados">Código HMAC do e-mail digitado, do número da conta ou do endereço IP, e contador</td><td data-rotulo="Base legal (LGPD)">Legítimo interesse em segurança (art. 7º, IX), com avaliação documentada pela equipe</td></tr>
                    <tr><td data-rotulo="Finalidade">Registrar o aceite dos Termos e a declaração de idade</td><td data-rotulo="Dados usados">Versão e data do aceite</td><td data-rotulo="Base legal (LGPD)">Execução de contrato (art. 7º, V), para demonstrar o cumprimento do art. 14 da LGPD e da Lei nº 15.211/2025</td></tr>
                    <tr><td data-rotulo="Finalidade">Registrar acessos e ações para proteger as contas e investigar falhas</td><td data-rotulo="Dados usados">Identificador da conta, ação, data e hora</td><td data-rotulo="Base legal (LGPD)">Legítimo interesse (art. 7º, IX), com avaliação documentada pela equipe</td></tr>
                    <tr><td data-rotulo="Finalidade">Enviar os e-mails da conta: recuperação de senha, aviso de senha alterada, link de reativação e avisos de exclusão e de reativação</td><td data-rotulo="Dados usados">E-mail e link temporário</td><td data-rotulo="Base legal (LGPD)">Execução de contrato (art. 7º, V)</td></tr>
                    <tr><td data-rotulo="Finalidade">Atender o seu pedido de exclusão da conta, com 30 dias para reativá-la</td><td data-rotulo="Dados usados">Dados da conta, data do pedido e link de reativação</td><td data-rotulo="Base legal (LGPD)">Execução de contrato (art. 7º, V) e direito de eliminação (art. 18, VI)</td></tr>
                    <tr><td data-rotulo="Finalidade">Guardar por 6 meses o e-mail de uma conta excluída, para comprovar a exclusão, responder a pedidos do titular e apurar incidentes de segurança</td><td data-rotulo="Dados usados">E-mail e datas da exclusão</td><td data-rotulo="Base legal (LGPD)">Exercício regular de direitos (art. 7º, VI) e legítimo interesse em segurança (art. 7º, IX), com acesso restrito à administração</td></tr>
                    <tr><td data-rotulo="Finalidade">Excluir a conta de um administrador que deixou a equipe</td><td data-rotulo="Dados usados">Dados da conta e motivo informado</td><td data-rotulo="Base legal (LGPD)">Legítimo interesse em segurança (art. 7º, IX), para que só a equipe atual administre a plataforma (art. 46)</td></tr>
                                                            <tr><td data-rotulo="Finalidade">Guardar a sua avaliação para você poder editá-la ou excluí-la e para evitar avaliações repetidas</td><td data-rotulo="Dados usados">Número da conta, atividade, nota e comentário</td><td data-rotulo="Base legal (LGPD)">Execução de contrato (art. 7º, V)</td></tr>
                    <tr><td data-rotulo="Finalidade">Permitir que a equipe leia as avaliações para melhorar os conteúdos e quizzes, vendo só o número da conta, sem nome nem e-mail</td><td data-rotulo="Dados usados">Número da conta, atividade, nota e comentário</td><td data-rotulo="Base legal (LGPD)">Legítimo interesse (art. 7º, IX), informado no próprio formulário, com avaliação documentada pela equipe</td></tr>
                    <tr><td data-rotulo="Finalidade">Publicar a sua nota na média pública e, depois da moderação, o seu comentário, sem nome, e-mail nem número da conta</td><td data-rotulo="Dados usados">Nota, comentário, data e a autorização registrada</td><td data-rotulo="Base legal (LGPD)">Consentimento (art. 7º, I, e art. 8º), dado ao marcar as opções de publicação e revogável a qualquer momento</td></tr>
                    <tr><td data-rotulo="Finalidade">Moderar os comentários enviados para publicação, para barrar dados pessoais, contatos, ofensas ou textos fora do tema</td><td data-rotulo="Dados usados">Comentário, número da conta e decisão da moderação</td><td data-rotulo="Base legal (LGPD)">Legítimo interesse (art. 7º, IX) em proteger os usuários e outras pessoas, com avaliação documentada pela equipe</td></tr>
                    <tr><td data-rotulo="Finalidade">Atender pedidos de privacidade</td><td data-rotulo="Dados usados">E-mail e conteúdo do pedido</td><td data-rotulo="Base legal (LGPD)">Cumprimento de obrigação legal (art. 7º, II, e art. 18)</td></tr>
                </tbody>
            </table>
        </div>
        <p>Usamos o consentimento (art. 7º, I) somente para publicar avaliações. Ele é dado quando você marca as opções de publicação no formulário da avaliação, separadas de qualquer outra escolha, e pode ser revogado a qualquer momento (art. 8º, § 5º, e art. 18, IX): basta desmarcar as opções e salvar, ou usar “Retirar divulgação e manter privada” em Minhas avaliações. A revogação tira a nota e o comentário da consulta pública dali em diante, e o uso privado da plataforma continua igual. As demais operações desta tabela não dependem de consentimento; para elas, você pode excluir a sua conta a qualquer momento em Minha conta, como explicado na seção 8.</p>

        <h2 id="4-adolescentes">4. Adolescentes</h2>
        <p>O SafeClick é voltado a estudantes a partir de 16 anos, do ensino médio e universitários, e parte desse público tem 16 ou 17 anos. Tratamos os dados de adolescentes em seu melhor interesse (art. 14 da LGPD) e seguimos o Estatuto Digital da Criança e do Adolescente (Lei nº 15.211/2025):</p>
        <ul>
            <li>As atividades do SafeClick exigem conta, e a conta só pode ser criada a partir de <strong>16 anos</strong>. Menores de 16 anos não podem usar a plataforma nesta fase do projeto.</li>
            <li>Entre 16 e 17 anos, o cadastro exige declarar que o responsável legal está ciente e de acordo com o uso da plataforma.</li>
            <li>Se identificarmos uma conta de menor de 16 anos, ela será excluída; o responsável pode pedir informações pelo canal <a href="mailto:safeclick.privacidade@gmail.com">safeclick.privacidade@gmail.com</a>.</li>
            <li>Todos os usuários recebem configurações privadas por padrão: não há perfil público, chat, publicidade ou cookies de rastreamento. Adolescentes de 16 e 17 anos podem avaliar conteúdos e quizzes de forma privada; publicar uma avaliação exige declarar ter 18 anos ou mais, e essa declaração não é uma verificação documental de idade.</li>
            <li>As conquistas não usam sequências diárias obrigatórias nem notificações que incentivem o uso compulsivo.</li>
        </ul>

        <h2 id="5-cookies">5. Cookies</h2>
        <p>Usamos apenas um <strong>cookie de sessão, estritamente necessário</strong>: ele mantém você conectado, protege formulários contra envios forjados (CSRF) e evita que um quiz seja enviado duas vezes. O cookie é assinado, inacessível a scripts da página (HttpOnly), restrito ao próprio site (SameSite=Lax), enviado somente por HTTPS em produção e apagado quando você fecha o navegador. Do lado do servidor, a sessão expira após 30 minutos sem atividade ou em até 8 horas, e é encerrada imediatamente quando você sai da conta. As páginas de conta e de login não são guardadas em cache pelo navegador.</p>
        <p>Não usamos cookies de análise, publicidade ou rastreamento. Por isso, não exibimos banner de cookies.</p>

        <h2 id="6-com-quem-compartilhamos">6. Com quem compartilhamos</h2>
        <p>Não vendemos dados nem os compartilhamos para marketing. Os serviços abaixo recebem apenas o necessário para a plataforma funcionar:</p>
        <div class="privacidade-tabela" role="region" aria-label="Tabela" tabindex="0">
            <table>
                <thead><tr><th scope="col">Serviço</th><th scope="col">Para quê</th><th scope="col">O que recebe</th><th scope="col">Onde</th></tr></thead>
                <tbody>
                    <tr><td data-rotulo="Serviço">Neon (PostgreSQL)</td><td data-rotulo="Para quê">Armazenar o banco de dados</td><td data-rotulo="O que recebe">Os dados guardados listados na seção 2</td><td data-rotulo="Onde">Brasil (AWS São Paulo), com conexão criptografada</td></tr>
                    <tr><td data-rotulo="Serviço">Vercel</td><td data-rotulo="Para quê">Hospedar a aplicação</td><td data-rotulo="O que recebe">As requisições enquanto são processadas (formulários e cookie de sessão) e dados técnicos de acesso</td><td data-rotulo="Onde">Execução configurada em São Paulo (gru1); empresa sediada nos EUA</td></tr>
                    <tr><td data-rotulo="Serviço">Twilio (Verify)</td><td data-rotulo="Para quê">Conferir os códigos do aplicativo autenticador (segundo fator); quando a conta é excluída, o vínculo é removido</td><td data-rotulo="O que recebe">Um identificador aleatório que não revela quem você é, o código de 6 dígitos digitado e a chave secreta do autenticador, criada e guardada pela própria Twilio. Não recebe nome, e-mail nem senha</td><td data-rotulo="Onde">EUA</td></tr>
                    <tr><td data-rotulo="Serviço">Gmail (Google), por SMTP</td><td data-rotulo="Para quê">Enviar o link de recuperação de senha, o aviso de senha alterada, o link de reativação da conta e os avisos de exclusão e de reativação</td><td data-rotulo="O que recebe">Seu e-mail, o link temporário e o texto do aviso; a senha nunca é enviada</td><td data-rotulo="Onde">Fora do Brasil (Google, EUA)</td></tr>
                    <tr><td data-rotulo="Serviço">Have I Been Pwned – Pwned Passwords</td><td data-rotulo="Para quê">Mostrar, no desafio "Qual vazou mais?" do laboratório, quantas vezes senhas públicas de exemplo apareceram em vazamentos</td><td data-rotulo="O que recebe">Somente os 5 primeiros caracteres do hash SHA-1 das senhas de exemplo do desafio; nada da sua conta e nenhuma senha digitada por você</td><td data-rotulo="Onde">Fora do Brasil</td></tr>
                </tbody>
            </table>
        </div>
        <p>O código-fonte fica no GitHub, que não recebe dados de usuários: senhas de acesso e chaves ficam em variáveis de ambiente, fora do repositório.</p>
        <p><strong>Avaliações publicadas</strong> por sua escolha aparecem na página de avaliações públicas do SafeClick, que pode ser aberta sem login. Ela mostra a nota, o comentário aprovado e a data, sem nome, e-mail nem número da conta, e pede aos buscadores que não a indexem.</p>

        <h2 id="7-transferencia-internacional">7. Transferência internacional</h2>
        <p>O banco de dados fica no Brasil. A Twilio, a Vercel e o Google (Gmail, usado no envio de e-mails) são empresas estrangeiras e podem processar dados fora do país, o que caracteriza transferência internacional (art. 33 da LGPD). Para reduzir esse risco, a Twilio recebe apenas um identificador aleatório, sem dados que identifiquem você diretamente. Em uma implantação real, o controlador deverá formalizar essas transferências por um dos mecanismos do art. 33, como as cláusulas-padrão contratuais da ANPD (Resolução CD/ANPD nº 19/2024).</p>

        <h2 id="8-por-quanto-tempo-guardamos">8. Por quanto tempo guardamos</h2>
        <ul>
            <li><strong>Conta, atividades (conteúdos concluídos, quizzes, simulações, desafio de senhas e conquistas) e vínculo com o autenticador:</strong> até a exclusão da conta. As contas criadas em testes e na validação do PFC serão excluídas até 31/12/2026.</li>
            <li><strong>Exclusão pedida por você:</strong> o acesso é encerrado na hora, em todos os dispositivos, e o vínculo com o aplicativo autenticador é apagado. Durante 30 dias a conta fica desativada e pode ser reativada pelo link enviado ao seu e-mail, que pede a sua senha. Passado esse prazo, nome, e-mail e senha são apagados de vez e a conta não pode mais ser recuperada; para voltar, é preciso criar uma conta nova, que começa do zero.</li>
            <li><strong>Exclusão de administrador:</strong> quando um administrador deixa a equipe, outro administrador pode excluir a conta dele. Nesse caso, os dados pessoais são apagados na hora, sem o prazo de 30 dias; a pessoa recebe um aviso por e-mail e a exclusão fica registrada na auditoria, com quem excluiu e o motivo.</li>
            <li><strong>E-mail da conta excluída:</strong> guardado à parte por 6 meses a partir da exclusão definitiva, visível só para a administração. Depois disso, é apagado pelo próprio sistema.</li>
            <li><strong>Atividades de uma conta excluída:</strong> ficam ligadas a um número de conta sem nome, e-mail nem senha, só para estatísticas. Depois que o e-mail guardado é apagado, não há mais como associá-las a você, e elas passam a ser dados anonimizados (arts. 12 e 16, IV, da LGPD).</li>
            <li><strong>Avaliações:</strong> até você excluí-las em Minhas avaliações ou até a exclusão definitiva da conta, quando são apagadas. Ao pedir a exclusão da conta, a publicação é retirada na hora e não volta sozinha se você reativar a conta.</li>
            <li><strong>Link de reativação da conta:</strong> vale até o fim do prazo de 30 dias e só pode ser usado uma vez; um novo envio substitui o anterior.</li>
            <li><strong>Sessão de acesso:</strong> até 30 minutos sem atividade, no máximo 8 horas, ou até você sair da conta. Registros vencidos são apagados automaticamente.</li>
            <li><strong>Etapa de login em andamento:</strong> 5 minutos; o registro é substituído no próximo login e apagado quando a conta é excluída.</li>
            <li><strong>Controle de tentativas:</strong> janela de 5 minutos; o registro é apagado automaticamente um dia depois de vencer.</li>
            <li><strong>Registros de auditoria:</strong> até 6 meses, para investigar falhas e acessos indevidos. Quando a conta é excluída de vez, eles passam a apontar para um número de conta sem dados pessoais.</li>
            <li><strong>Token de recuperação de senha:</strong> válido por 30 minutos e de uso único; o registro é substituído no pedido seguinte e apagado quando a conta é excluída.</li>
            <li><strong>Senha digitada no analisador de força:</strong> não sai do seu navegador e não é armazenada.</li>
            <li><strong>Cópias de segurança do banco:</strong> até 6 horas, janela de restauração do plano utilizado no Neon.</li>
        </ul>
        <p>O plano completo de retenção e descarte faz parte da documentação do projeto.</p>

        <h2 id="9-seus-direitos">9. Seus direitos</h2>
        <p>Pelo art. 18 da LGPD, você pode pedir a qualquer momento:</p>
        <ul>
            <li>confirmação de que tratamos seus dados e acesso a eles;</li>
            <li>correção de dados incompletos, inexatos ou desatualizados;</li>
            <li>anonimização, bloqueio ou eliminação de dados desnecessários ou tratados em desconformidade com a lei;</li>
            <li>portabilidade, recebendo os dados da sua conta e os seus resultados em formato legível;</li>
            <li>informação sobre com quem compartilhamos dados (seção 6);</li>
            <li>eliminação dos seus dados, com a exclusão da conta.</li>
        </ul>
        <p><strong>Na própria plataforma</strong>, em Minha conta, você corrige seu nome, troca a senha, encerra as sessões abertas em outros aparelhos e exclui a conta. A exclusão pede a sua senha atual e a confirmação de que você entendeu as consequências; o que acontece depois está na seção 8.</p>
        <p><strong>Para os outros pedidos</strong>, como acesso e cópia dos dados: envie um e-mail para <a href="mailto:safeclick.privacidade@gmail.com">safeclick.privacidade@gmail.com</a> a partir do e-mail cadastrado na sua conta, para que possamos confirmar que o pedido é seu. Respondemos de forma simplificada imediatamente ou com uma declaração completa em até 15 dias (art. 19).</p>
        <p>Você também pode apresentar reclamação à Autoridade Nacional de Proteção de Dados (ANPD), em www.gov.br/anpd.</p>

        <h2 id="10-seguranca">10. Segurança</h2>
        <p>Adotamos medidas técnicas para proteger os dados (art. 46 da LGPD): senhas guardadas apenas como hash scrypt com salt; login em duas etapas com aplicativo autenticador; limite de 5 tentativas a cada 5 minutos no login, na troca de senha, na exclusão e na reativação da conta; confirmação da senha atual antes de trocar a senha, excluir a conta ou excluir a conta de um administrador; links enviados por e-mail guardados apenas como hash, com prazo e uso único; sessões registradas no servidor, com identificadores guardados apenas como hash, expiração após 30 minutos sem atividade ou em 8 horas e encerramento no logout; registros de auditoria sem senhas, códigos, tokens, IP ou dados digitados nos formulários, consultados somente pelo administrador; exigência de login e verificação do perfil no servidor em todas as páginas de conteúdo; proteção de formulários contra CSRF; comunicação por HTTPS; consultas parametrizadas ao banco; e credenciais fora do código-fonte.</p>
        <p>Se ocorrer um incidente de segurança que possa causar risco ou dano relevante, comunicaremos a ANPD e as pessoas afetadas no prazo de três dias úteis, conforme a Resolução CD/ANPD nº 15/2024 (art. 48 da LGPD).</p>

        <h2 id="11-alteracoes-nesta-politica">11. Alterações nesta política</h2>
        <p>A versão e a data de vigência aparecem no topo desta página. Mudanças importantes serão avisadas em destaque na plataforma e, quando alterarem o que foi aceito no cadastro, pediremos um novo aceite dos Termos de Uso.</p>
        <h2 id="12-avaliacoes">12. Avaliações de conteúdos e quizzes</h2>
        <p>Depois de concluir um conteúdo ou quiz, você pode avaliá-lo com uma nota de 1 a 5 e um comentário opcional de até 500 caracteres. Avaliar é opcional e não muda o seu progresso.</p>
        <ul>
            <li><strong>Privada por padrão.</strong> Sem marcar as opções de publicação, a avaliação fica ligada à sua conta só para você poder editá-la ou excluí-la. A equipe pode lê-la para melhorar as atividades, vendo apenas o número da conta, sem nome nem e-mail, e acompanha as médias gerais sem identificar quem avaliou.</li>
            <li><strong>Publicação só com a sua autorização.</strong> São duas escolhas separadas: incluir a nota na média pública e enviar o comentário para publicação. O comentário só aparece depois de aprovado por um administrador, e qualquer alteração no texto passa por nova moderação. A moderação pode recusar ou retirar comentários com dados pessoais, contatos, senhas, ofensas ou texto fora do tema.</li>
            <li><strong>Sem identificação na página pública.</strong> A consulta pública mostra a nota, o comentário aprovado e a data, sem nome, e-mail ou número da conta (seção 6).</li>
            <li><strong>18 anos ou mais para publicar.</strong> Publicar exige declarar ter 18 anos ou mais. A declaração não é uma verificação documental de idade; quem tem 16 ou 17 anos pode avaliar normalmente, de forma privada.</li>
            <li><strong>O que fica registrado.</strong> Guardamos a sua escolha, a declaração de idade, a versão do aviso de publicação e a data da autorização, para demonstrar que o consentimento foi dado (art. 8º, § 2º).</li>
            <li><strong>Você pode voltar atrás.</strong> Desmarque as opções e salve, ou use “Retirar divulgação e manter privada” em <a href="/avaliacoes/minhas">Minhas avaliações</a>; ali também é possível excluir a avaliação. A retirada vale para as próximas consultas; não controlamos cópias que outras pessoas tenham feito enquanto o comentário estava público.</li>
            <li><strong>Exclusão da conta.</strong> Ao pedir a exclusão, a publicação é retirada na hora; quando a exclusão é concluída, as avaliações são apagadas (seção 8).</li>
        </ul>
        <p>O <a href="/avaliacoes/privacidade">aviso de publicação de avaliações</a> resume essas regras dentro da plataforma.</p>
    $conteudo_politica_1_5$;
BEGIN
    IF NOT EXISTS (SELECT 1 FROM public.versoes_politica WHERE versao = '1.4') THEN
        RAISE EXCEPTION 'Publique a Política 1.4 antes da 1.5.';
    END IF;

    INSERT INTO public.versoes_politica (versao, vigente_desde, conteudo_html)
    VALUES ('1.5', DATE '2026-11-16', texto_politica)
    ON CONFLICT (versao) DO NOTHING;

    IF NOT EXISTS (
        SELECT 1 FROM public.versoes_politica
        WHERE versao = '1.5' AND vigente_desde = DATE '2026-11-16' AND conteudo_html = texto_politica
    ) THEN
        RAISE EXCEPTION 'A Política 1.5 já existe com outro texto ou vigência. Nada foi substituído.';
    END IF;
END;
$registrar_politica_1_5$;

INSERT INTO public.politica_referencias (versao_politica, referencia_id, ordem)
SELECT '1.5', referencia_id, CASE WHEN ordem >= 3 THEN ordem + 1 ELSE ordem END
FROM public.politica_referencias WHERE versao_politica = '1.4'
ON CONFLICT DO NOTHING;

INSERT INTO public.politica_referencias (versao_politica, referencia_id, ordem)
SELECT '1.5', id, 3 FROM public.referencias_legais
WHERE norma = 'Lei nº 13.709/2018 (LGPD)' AND dispositivo = 'art. 7º, I, e art. 8º'
ON CONFLICT DO NOTHING;

DO $registrar_termos_1_1$
DECLARE
    texto_termos CONSTANT TEXT := $conteudo_termos_1_1$<h1>Termos de Uso</h1>
        <p class="privacidade-meta">Versão 1.1 · vigente desde 16/11/2026</p>
        <nav class="privacidade-sumario" aria-label="Seções">
            <p>Nesta página</p>
            <ol>
                <li><a href="#1-aceitacao">1. Aceitação</a></li>
                <li><a href="#2-o-servico-e-suas-limitacoes">2. O serviço e suas limitações</a></li>
                <li><a href="#3-quem-pode-usar">3. Quem pode usar</a></li>
                <li><a href="#4-sua-conta">4. Sua conta</a></li>
                <li><a href="#5-condutas-proibidas">5. Condutas proibidas</a></li>
                <li><a href="#6-conteudo-enviado-por-voce">6. Conteúdo enviado por você</a></li>
                <li><a href="#7-propriedade-intelectual">7. Propriedade intelectual</a></li>
                <li><a href="#8-disponibilidade-e-suporte">8. Disponibilidade e suporte</a></li>
                <li><a href="#9-encerramento-da-conta">9. Encerramento da conta</a></li>
                <li><a href="#10-responsabilidades">10. Responsabilidades</a></li>
                <li><a href="#11-legislacao-aplicavel">11. Legislação aplicável</a></li>
                <li><a href="#12-versao-e-alteracoes">12. Versão e alterações</a></li>
            </ol>
        </nav>
        <section class="privacidade-resumo" aria-labelledby="resumo">
            <h2 id="resumo">Resumo em linguagem simples</h2>
            <ul>
                <li>O SafeClick ensina segurança digital. Ele não é um antivírus e não garante que você nunca cairá em um golpe.</li>
                <li>Para usar é preciso criar uma conta e ter 16 anos ou mais; entre 16 e 17, com ciência do responsável.</li>
                <li>O login pede sua senha e um código de um aplicativo autenticador no celular.</li>
                <li>Cuide da sua senha, não tente acessar contas de outras pessoas e não use as simulações para aplicar golpes de verdade.</li>
                <li>Suas avaliações de conteúdos e quizzes são privadas, a menos que você autorize publicá-las, sem o seu nome. Para publicar é preciso ter 18 anos ou mais.</li>
                <li>Você pode excluir a sua conta quando quiser, em Minha conta, e tem 30 dias para voltar atrás. Seus direitos sobre os dados estão na Política de Privacidade.</li>
            </ul>
        </section>

        <h2 id="1-aceitacao">1. Aceitação</h2>
        <p>Estes Termos regulam o uso do SafeClick. Ao criar uma conta, você declara que leu e aceita estes Termos. O tratamento de dados pessoais é explicado separadamente na Política de Privacidade, que não é substituída por estes Termos.</p>

        <h2 id="2-o-servico-e-suas-limitacoes">2. O serviço e suas limitações</h2>
        <p>O SafeClick é uma plataforma educativa, gratuita e sem fins comerciais, desenvolvida como Projeto Final de Curso da UMC. Oferece, para usuários com conta, conteúdos educativos, quizzes e oficinas, simulações de golpes digitais, um laboratório de senhas, painel de progresso, conquistas e avaliações das atividades.</p>
        <ul>
            <li>O SafeClick tem finalidade educativa. Ele não detecta ameaças em tempo real e não substitui antivírus, atualizações ou os canais oficiais de bancos e serviços.</li>
            <li>As simulações são <strong>inteiramente fictícias</strong>: nomes, mensagens e endereços são inventados para fins didáticos e não representam nenhuma empresa ou instituição real.</li>
            <li>No laboratório de senhas, o analisador de força funciona só no seu navegador, e o desafio “Qual vazou mais?” usa senhas públicas de exemplo. Os resultados servem para aprender e não garantem que uma senha seja segura.</li>
        </ul>

        <h2 id="3-quem-pode-usar">3. Quem pode usar</h2>
        <ul>
            <li>O acesso aos conteúdos, quizzes e simulações exige uma conta.</li>
            <li>A criação de conta é permitida a partir de <strong>16 anos</strong>. Menores de 16 anos não podem usar a plataforma nesta fase do projeto.</li>
            <li>Se você tem entre 16 e 17 anos, só pode criar conta com a ciência e a concordância do seu responsável legal, e declara isso no cadastro.</li>
            <li>Contas de menores de 16 anos serão excluídas quando identificadas.</li>
            <li>Publicar avaliações exige declarar ter 18 anos ou mais; quem tem 16 ou 17 anos pode avaliar de forma privada.</li>
        </ul>

        <h2 id="4-sua-conta">4. Sua conta</h2>
        <ul>
            <li>Informe um e-mail que seja seu. No campo de nome, você pode usar um apelido.</li>
            <li>A senha deve ter pelo menos 15 caracteres. Use uma senha exclusiva e não a compartilhe.</li>
            <li>Para entrar, é preciso configurar um aplicativo autenticador no celular (segundo fator) e informar o código gerado por ele a cada login. Se perder o acesso ao aplicativo, fale conosco pelo canal <a href="mailto:safeclick.privacidade@gmail.com">safeclick.privacidade@gmail.com</a>.</li>
            <li>Depois de 5 tentativas de login sem sucesso em 5 minutos, novas tentativas ficam bloqueadas temporariamente. A sessão expira após 30 minutos sem atividade ou em até 8 horas; saia da conta ao usar um computador compartilhado.</li>
            <li>Se suspeitar de acesso indevido, troque a senha e avise pelo canal <a href="mailto:safeclick.privacidade@gmail.com">safeclick.privacidade@gmail.com</a>.</li>
            <li>Existem dois perfis: <strong>usuário</strong>, criado pelo cadastro público, e <strong>administrador</strong>, criado apenas pela equipe e restrito à manutenção de conteúdos e à segurança da plataforma.</li>
        </ul>

        <h2 id="5-condutas-proibidas">5. Condutas proibidas</h2>
        <p>Ao usar o SafeClick, você não pode:</p>
        <ul>
            <li>tentar acessar contas ou dados de outras pessoas;</li>
            <li>testar vulnerabilidades, sobrecarregar ou atacar a plataforma sem autorização da equipe;</li>
            <li>automatizar cadastros, logins ou envios de quizzes;</li>
            <li>digitar no laboratório a senha de outra pessoa;</li>
            <li>usar as simulações ou os conteúdos como modelo para aplicar golpes reais;</li>
            <li>incluir em avaliações dados pessoais, contatos ou senhas, seus ou de outras pessoas, ofensas, propaganda ou textos fora do tema.</li>
        </ul>
        <p>O descumprimento pode levar à suspensão ou à exclusão da conta, com aviso sempre que possível.</p>

        <h2 id="6-conteudo-enviado-por-voce">6. Conteúdo enviado por você</h2>
        <p>Você pode avaliar os conteúdos e quizzes que concluir, com uma nota de 1 a 5 e um comentário opcional. A avaliação fica ligada à sua conta para que você possa editá-la ou excluí-la, e a equipe pode lê-la para melhorar a plataforma, vendo apenas o número da conta, sem nome nem e-mail.</p>
        <ul>
            <li>A avaliação só aparece para outras pessoas se você autorizar, marcando as opções de publicação: a nota entra na média pública e o comentário é publicado depois de aprovado pela moderação, sem o seu nome, e-mail ou número da conta.</li>
            <li>Ao autorizar a publicação, você permite que o SafeClick exiba o comentário na plataforma enquanto a autorização valer. Você continua sendo o autor e pode retirar a publicação ou excluir a avaliação a qualquer momento em Minhas avaliações.</li>
            <li>A moderação pode recusar ou retirar comentários que descumpram a seção 5.</li>
            <li>O uso desses dados está explicado na seção 12 da Política de Privacidade.</li>
        </ul>

        <h2 id="7-propriedade-intelectual">7. Propriedade intelectual</h2>
        <p>Os textos, as simulações e o código-fonte do SafeClick são de autoria da equipe e foram produzidos para fins acadêmicos. As fontes consultadas nos conteúdos educativos estão indicadas na monografia do projeto.</p>

        <h2 id="8-disponibilidade-e-suporte">8. Disponibilidade e suporte</h2>
        <p>Por ser um projeto acadêmico hospedado em planos gratuitos, o SafeClick pode ficar indisponível para manutenção ou por limites dos provedores. Se o serviço que confere os códigos do autenticador ficar fora do ar, o login pode ficar temporariamente indisponível. Dúvidas e suporte: <a href="mailto:safeclick.privacidade@gmail.com">safeclick.privacidade@gmail.com</a>.</p>

        <h2 id="9-encerramento-da-conta">9. Encerramento da conta</h2>
        <p>Você pode excluir a sua conta a qualquer momento em Minha conta, confirmando a sua senha. O acesso é encerrado na hora e você tem 30 dias para voltar atrás pelo link enviado ao seu e-mail; depois disso, a exclusão é definitiva. Se preferir, peça a exclusão pelo canal <a href="mailto:safeclick.privacidade@gmail.com">safeclick.privacidade@gmail.com</a>. A conta de um administrador que deixar a equipe pode ser excluída por outro administrador. As contas criadas em testes e na validação do PFC serão excluídas até 31/12/2026. Se a plataforma continuar em operação depois disso, estes Termos e a Política de Privacidade serão atualizados.</p>

        <h2 id="10-responsabilidades">10. Responsabilidades</h2>
        <p>A equipe adota as medidas de segurança descritas na Política de Privacidade e responde por falhas nos termos da lei. Você é responsável pelo sigilo da sua senha, pela guarda do aplicativo autenticador e pelas condutas realizadas com a sua conta. Nada nestes Termos afasta direitos garantidos pela LGPD, pelo Código de Defesa do Consumidor ou pelo Estatuto da Criança e do Adolescente.</p>

        <h2 id="11-legislacao-aplicavel">11. Legislação aplicável</h2>
        <p>Estes Termos seguem as leis brasileiras, em especial a Lei Geral de Proteção de Dados Pessoais (Lei nº 13.709/2018), o Marco Civil da Internet (Lei nº 12.965/2014), o Estatuto da Criança e do Adolescente (Lei nº 8.069/1990) e o Estatuto Digital da Criança e do Adolescente (Lei nº 15.211/2025).</p>

        <h2 id="12-versao-e-alteracoes">12. Versão e alterações</h2>
        <p>A versão e a data de vigência aparecem no topo desta página. Quando uma alteração mudar o que foi aceito no cadastro, pediremos um novo aceite. A versão 1.1 atualizou as funcionalidades disponíveis (seção 2), as regras das avaliações (seções 3, 5 e 6) e a exclusão da conta (seção 9).</p>$conteudo_termos_1_1$;
BEGIN
    INSERT INTO public.versoes_termos (versao, vigente_desde, conteudo_html)
    VALUES ('1.1', DATE '2026-11-16', texto_termos)
    ON CONFLICT (versao) DO NOTHING;

    IF NOT EXISTS (
        SELECT 1 FROM public.versoes_termos
        WHERE versao = '1.1' AND vigente_desde = DATE '2026-11-16' AND conteudo_html = texto_termos
    ) THEN
        RAISE EXCEPTION 'Os Termos 1.1 já existem com outro texto ou vigência. Nada foi substituído.';
    END IF;
END;
$registrar_termos_1_1$;

INSERT INTO public.termos_referencias (versao_termos, referencia_id, ordem)
SELECT '1.1', referencia_id, ordem FROM public.termos_referencias WHERE versao_termos = '1.0'
ON CONFLICT DO NOTHING;

COMMIT;