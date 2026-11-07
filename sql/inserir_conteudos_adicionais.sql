BEGIN;

UPDATE public.conteudos
SET texto = replace(texto, '<h3>O que é Phishing? <h3>', '<h3>O que é Phishing?</h3>')
WHERE slug = 'phishing';

INSERT INTO public.conteudos (slug, titulo, texto) VALUES
('golpes-por-mensagem', 'Golpes por SMS e mensagens', '<h3>O que é</h3>
<p>É o phishing que chega pelo celular: SMS, WhatsApp, Telegram ou mensagens diretas em redes sociais. Por isso também é chamado de <strong>smishing</strong> (SMS + phishing). A mensagem curta e o costume de responder rápido no celular facilitam o golpe.</p>
<h3>Exemplos comuns</h3>
<ul>
<li><strong>Encomenda retida:</strong> uma "taxa" pequena para liberar a entrega.</li>
<li><strong>Pontos ou benefícios expirando:</strong> do cartão, do programa de fidelidade ou de um aplicativo.</li>
<li><strong>Débito ou multa pendente:</strong> com ameaça de protesto, bloqueio ou perda do nome limpo.</li>
<li><strong>Prêmio ou sorteio:</strong> que você não lembra de ter participado.</li>
<li><strong>Falsa central do banco:</strong> pede para ligar para um número ou confirmar uma compra que você não fez.</li>
</ul>
<h3>Sinais de alerta</h3>
<ul>
<li><strong>Remetente desconhecido</strong> ou número de celular comum se passando por empresa.</li>
<li><strong>Link encurtado ou com endereço estranho</strong>, diferente do site oficial.</li>
<li><strong>Prazo curto</strong> ("pague em 20 minutos") para você não ter tempo de pensar.</li>
<li><strong>Pedido de dados ou pagamento</strong> pela própria mensagem.</li>
</ul>
<h3>O que fazer</h3>
<ul>
<li><strong>Não clique no link</strong> e não responda.</li>
<li><strong>Confira pelo canal oficial:</strong> abra o aplicativo ou digite o endereço da empresa no navegador.</li>
<li><strong>Bloqueie e denuncie</strong> o número como spam no próprio aplicativo.</li>
<li><strong>Se já informou dados:</strong> troque as senhas envolvidas e avise o seu banco pelos canais oficiais.</li>
</ul>
<p class="conteudos-pratique"><strong>Pratique:</strong> <a href="/simulacoes/entrega-sms">simulação “Taxa para liberar uma entrega”</a></p>
<p class="conteudos-fonte">Fontes: Cartilha de Segurança para Internet, fascículos Golpes: Não se Deixe Enganar e Golpes: Evite Fraudes (CERT.br).</p>'),

('falso-conhecido-e-pix', 'Golpe do falso conhecido e Pix', '<h3>Como funciona</h3>
<p>O golpista se passa por alguém que você conhece, como um parente, amigo ou colega. Ele usa a foto e o nome da pessoa em um número novo ("troquei de número") ou invade a conta de WhatsApp dela. Depois de uma conversa curta, vem o pedido: um Pix urgente para pagar uma conta, quase sempre para a conta de outra pessoa.</p>
<h3>Como a conta de WhatsApp é roubada</h3>
<p>O criminoso pede o <strong>código de 6 dígitos</strong> que o WhatsApp envia por SMS, fingindo ser uma loja, uma pesquisa ou uma confirmação de cadastro. Com esse código, ele ativa a sua conta em outro celular e passa a conversar com os seus contatos. <strong>Nunca repasse esse código para ninguém.</strong></p>
<h3>Sinais de alerta</h3>
<ul>
<li><strong>Número novo</strong> com foto de alguém conhecido.</li>
<li><strong>Urgência e pedido de sigilo</strong> ("não conta pra ninguém").</li>
<li><strong>Pix para conta de terceiros</strong>, com uma desculpa para não ser no nome da própria pessoa.</li>
<li><strong>Recusa em atender ligação</strong> ou em fazer chamada de vídeo.</li>
</ul>
<h3>Como se proteger</h3>
<ul>
<li><strong>Confirme por outro caminho:</strong> ligue para o número antigo da pessoa ou faça uma pergunta que só ela saberia responder.</li>
<li><strong>Ative a confirmação em duas etapas do WhatsApp</strong> (um PIN pedido ao registrar o número em outro aparelho).</li>
<li><strong>Combine com a família</strong> uma palavra-chave para pedidos de dinheiro.</li>
</ul>
<h3>Se você já fez o Pix</h3>
<ul>
<li><strong>Avise o seu banco imediatamente</strong> e peça a abertura do <strong>MED</strong> (Mecanismo Especial de Devolução), criado pelo Banco Central para casos de golpe com Pix.</li>
<li><strong>Registre um boletim de ocorrência</strong>, que em muitos estados pode ser feito pela internet.</li>
<li><strong>Avise a pessoa verdadeira</strong> para alertar os contatos dela.</li>
</ul>
<p class="conteudos-pratique"><strong>Pratique:</strong> <a href="/simulacoes/falso-conhecido">simulação “Pedido de Pix de um conhecido”</a></p>
<p class="conteudos-fonte">Fontes: Cartilha de Segurança para Internet, fascículos Golpes: Evite Fraudes e Golpes: Caiu? Veja o que Fazer (CERT.br); Banco Central do Brasil, regulamento do Pix (MED).</p>'),

('compras-online-seguras', 'Compras online seguras', '<h3>Lojas falsas</h3>
<p>Golpistas criam lojas virtuais com aparência profissional, anunciam em redes sociais e buscadores e oferecem preços muito abaixo do mercado. Depois do pagamento, o produto nunca chega ou chega diferente do anunciado.</p>
<h3>Sinais de uma loja suspeita</h3>
<ul>
<li><strong>Preço bom demais</strong> e contagem regressiva para "acabar a promoção".</li>
<li><strong>Pagamento só por Pix ou boleto</strong>, às vezes em nome de uma pessoa física.</li>
<li><strong>Sem CNPJ, endereço ou canal de atendimento</strong>, ou com dados que não batem com o nome da loja.</li>
<li><strong>Endereço do site estranho</strong>, parecido com o de uma marca conhecida, com letras trocadas.</li>
</ul>
<h3>Antes de comprar</h3>
<ul>
<li><strong>Pesquise a reputação</strong> da loja em sites de reclamação e em avaliações de outros compradores.</li>
<li><strong>Confira o CNPJ</strong> informado no rodapé do site.</li>
<li><strong>Digite o endereço da loja</strong> em vez de clicar em anúncios.</li>
<li><strong>Prefira cartão de crédito</strong>, de preferência virtual: ele permite contestar a compra. O Pix cai na hora e é difícil de reverter.</li>
<li><strong>Em boletos, confira o beneficiário</strong> antes de pagar: boletos adulterados mudam o destinatário do dinheiro.</li>
</ul>
<h3>Seus direitos</h3>
<p>Nas compras feitas pela internet, o Código de Defesa do Consumidor garante o <strong>direito de arrependimento</strong>: você pode desistir em até 7 dias a partir do recebimento do produto (art. 49).</p>
<p class="conteudos-pratique"><strong>Pratique:</strong> <a href="/simulacoes/loja-falsa">simulação “Promoção em uma loja desconhecida”</a></p>
<p class="conteudos-fonte">Fontes: Cartilha de Segurança para Internet, fascículo Comércio via Internet (CERT.br); Lei nº 8.078/1990 (Código de Defesa do Consumidor).</p>'),

('verificacao-em-duas-etapas', 'Verificação em duas etapas', '<h3>O que é</h3>
<p>A verificação em duas etapas (também chamada de 2FA ou autenticação multifator) pede, além da senha, uma segunda prova de que é você. Assim, mesmo que alguém descubra a sua senha, não consegue entrar só com ela.</p>
<h3>Os tipos mais comuns</h3>
<ul>
<li><strong>Código por SMS:</strong> melhor do que nada, mas o código pode ser interceptado ou desviado com a troca do chip.</li>
<li><strong>Aplicativo autenticador:</strong> gera no celular um código de 6 dígitos que muda a cada 30 segundos, mesmo sem internet.</li>
<li><strong>Confirmação no aplicativo:</strong> o serviço envia uma notificação para você aprovar o acesso.</li>
<li><strong>Chave de segurança física:</strong> um pequeno dispositivo conectado ao computador ou aproximado do celular.</li>
</ul>
<h3>No SafeClick</h3>
<p>O login do SafeClick usa um <strong>aplicativo autenticador</strong>: depois da senha, você informa o código gerado no celular, conferido pela Twilio Verify. Sem esse código, a sessão não é criada.</p>
<h3>Cuidados</h3>
<ul>
<li><strong>Nunca informe o código</strong> a ninguém, nem a quem diz ser do suporte.</li>
<li><strong>Guarde os códigos de recuperação</strong> que alguns serviços oferecem, em um lugar seguro.</li>
<li><strong>Ative primeiro nas contas mais importantes:</strong> e-mail principal, banco, redes sociais e WhatsApp.</li>
<li><strong>Desconfie de pedidos de aprovação</strong> que você não fez: recuse e troque a senha.</li>
</ul>
<p class="conteudos-fonte">Fontes: Cartilha de Segurança para Internet, fascículo Autenticação (CERT.br); OWASP Multifactor Authentication Cheat Sheet.</p>'),

('vazamento-de-dados', 'Vazamento de dados: o que fazer', '<h3>O que é um vazamento</h3>
<p>Acontece quando dados guardados por uma empresa ou serviço são expostos, seja por uma invasão, seja por um erro de configuração. Podem vazar e-mails, senhas, telefones, endereços e números de documentos.</p>
<h3>Por que isso importa para você</h3>
<ul>
<li><strong>Senhas repetidas:</strong> criminosos testam a senha vazada em outros sites, o chamado <em>credential stuffing</em>.</li>
<li><strong>Golpes personalizados:</strong> com seu nome, CPF ou compras recentes, a mensagem falsa parece muito mais real.</li>
<li><strong>Fraudes no seu nome:</strong> abertura de contas ou pedidos de crédito com os seus documentos.</li>
</ul>
<h3>Como saber se seus dados vazaram</h3>
<ul>
<li><strong>Aviso da empresa:</strong> pela LGPD, a empresa deve comunicar os titulares quando um incidente puder causar risco ou dano relevante.</li>
<li><strong>Consultas públicas</strong>, como o site Have I Been Pwned, que mostra em quais vazamentos conhecidos um e-mail aparece.</li>
<li><strong>Laboratório do SafeClick:</strong> veja como senhas comuns aparecem em vazamentos.</li>
</ul>
<h3>O que fazer</h3>
<ul>
<li><strong>Troque a senha</strong> do serviço afetado e de todos os lugares onde você usava a mesma.</li>
<li><strong>Ative a verificação em duas etapas.</strong></li>
<li><strong>Desconfie de contatos</strong> que citam seus dados para pedir pagamento ou confirmação.</li>
<li><strong>Acompanhe extratos e faturas</strong> e consulte, no Registrato do Banco Central, as contas e empréstimos em seu nome.</li>
</ul>
<p class="conteudos-pratique"><strong>Pratique:</strong> <a href="/laboratorio-senhas/">Laboratório de senhas</a></p>
<p class="conteudos-fonte">Fontes: Cartilha de Segurança para Internet, fascículo Vazamento de Dados (CERT.br); Lei nº 13.709/2018 (LGPD), art. 48.</p>'),

('privacidade-e-dados-pessoais', 'Privacidade e seus dados pessoais', '<h3>O que são dados pessoais</h3>
<p>Dado pessoal é qualquer informação que identifique você ou permita identificar você: nome, e-mail, CPF, telefone, fotos e até a sua localização. Alguns são <strong>dados sensíveis</strong>, como saúde, religião, opinião política e biometria, e por isso recebem proteção maior.</p>
<h3>Seus direitos pela LGPD</h3>
<p>A Lei Geral de Proteção de Dados (Lei nº 13.709/2018) garante que você pode pedir a quem trata os seus dados:</p>
<ul>
<li><strong>Confirmação e acesso:</strong> saber se a empresa tem dados seus e quais são.</li>
<li><strong>Correção</strong> de dados incompletos ou errados.</li>
<li><strong>Eliminação</strong> de dados desnecessários ou tratados sem base legal.</li>
<li><strong>Portabilidade:</strong> levar seus dados para outro serviço.</li>
<li><strong>Informação</strong> sobre com quem os dados foram compartilhados.</li>
</ul>
<p>O pedido é feito pelo canal de privacidade indicado na política da empresa. Se não houver resposta, você pode reclamar na Autoridade Nacional de Proteção de Dados (ANPD).</p>
<h3>Cuidados no dia a dia</h3>
<ul>
<li><strong>Publique menos:</strong> data de nascimento, endereço, rotina e fotos de documentos ajudam golpistas.</li>
<li><strong>Revise as permissões dos aplicativos</strong>, como câmera, contatos e localização.</li>
<li><strong>Desconfie de cadastros em troca de brindes</strong> e de pedidos de CPF sem motivo claro.</li>
<li><strong>Leia o resumo da política de privacidade</strong> antes de criar uma conta.</li>
</ul>
<p class="conteudos-pratique"><strong>Pratique:</strong> <a href="/politica-de-privacidade">veja como o SafeClick trata os seus dados na Política de Privacidade</a></p>
<p class="conteudos-fonte">Fontes: Lei nº 13.709/2018 (LGPD), arts. 5º e 18; Cartilha de Segurança para Internet, fascículo Privacidade (CERT.br).</p>'),

('codigos-maliciosos-e-atualizacoes', 'Códigos maliciosos e atualizações', '<h3>O que são códigos maliciosos</h3>
<p>São programas feitos para causar dano ou roubar informações. Também são chamados de <strong>malware</strong>. Os mais conhecidos são:</p>
<ul>
<li><strong>Vírus:</strong> se espalha infectando arquivos e outros programas.</li>
<li><strong>Cavalo de troia:</strong> parece um programa útil, mas executa ações escondidas.</li>
<li><strong>Spyware:</strong> espiona o que você digita e acessa.</li>
<li><strong>Ransomware:</strong> bloqueia ou embaralha seus arquivos e cobra um "resgate" para liberá-los.</li>
</ul>
<h3>Como eles chegam</h3>
<ul>
<li><strong>Anexos e links</strong> em e-mails e mensagens.</li>
<li><strong>Aplicativos fora das lojas oficiais</strong> e programas piratas.</li>
<li><strong>Pendrives e arquivos</strong> compartilhados.</li>
<li><strong>Sistemas desatualizados</strong>, com falhas já conhecidas pelos criminosos.</li>
</ul>
<h3>Como se proteger</h3>
<ul>
<li><strong>Mantenha tudo atualizado:</strong> sistema, navegador e aplicativos, de preferência com atualização automática.</li>
<li><strong>Instale apps só das lojas oficiais</strong> e confira as permissões pedidas.</li>
<li><strong>Use um antivírus</strong> e mantenha-o ativo.</li>
<li><strong>Faça cópias de segurança (backup)</strong> regulares em um local separado, como um disco externo ou a nuvem. É a melhor defesa contra o ransomware.</li>
<li><strong>Não abra anexos inesperados</strong>, mesmo de conhecidos: confirme antes com a pessoa.</li>
</ul>
<h3>Sinais de infecção</h3>
<p>Lentidão sem motivo, propagandas aparecendo do nada, aplicativos que você não instalou e consumo alto de bateria ou de internet merecem atenção. Nesses casos, rode o antivírus e troque as senhas usando outro aparelho.</p>
<p class="conteudos-fonte">Fontes: Cartilha de Segurança para Internet, fascículos Códigos Maliciosos e Backup (CERT.br).</p>')
ON CONFLICT (slug) DO NOTHING;

COMMIT;