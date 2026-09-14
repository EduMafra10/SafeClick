insert into public.conteudos (slug, titulo, texto) values
('phishing', 'Phishing', '<h3>O que é Phishing? <h3>
<p>Phishing é uma técnica de golpe digital em que criminosos se passam por empresas, bancos, órgãos públicos ou até conhecidos para enganar a vítima e obter senhas, dados de cartão ou documentos.</p>
<p>O golpe costuma chegar por e-mail, SMS, WhatsApp ou redes sociais, imitando a comunicação de uma marca conhecida, levando a vítima a clicar num link ou preencher um formulário falso.</p>
<h3>Como identificar</h3>
<ul>
<li><strong>Urgência exagerada:</strong> "sua conta será bloqueada em 24h".</li>
<li><strong>Erros de escrita</strong> ou tradução estranha.</li>
<li><strong>Remetente ou domínio suspeito</strong>, diferente do oficial.</li>
<li><strong>Link diferente do texto</strong> ao passar o mouse sobre ele.</li>
<li><strong>Pedido de dados sensíveis</strong> por e-mail ou mensagem, algo que empresas sérias raramente fazem.</li>
</ul>
<p>Na dúvida, não clique: acesse o site oficial digitando o endereço direto no navegador.</p>'),
('protecao-de-senhas', 'Proteção de Senhas', '<h3>Por que senhas fracas são perigosas</h3>
<p>Senhas simples, como sequências óbvias ou datas de nascimento, podem ser descobertas em segundos por programas automatizados. Reutilizar a mesma senha em vários sites também é arriscado: se um deles vaza dados, criminosos testam a mesma combinação em outras plataformas (credential stuffing).</p>
<h3>Como se proteger</h3>
<ul>
<li><strong>Use senhas longas</strong>, com 12 caracteres ou mais.</li>
<li><strong>Misture</strong> letras, números e símbolos.</li>
<li><strong>Nunca repita</strong> a mesma senha entre serviços importantes.</li>
<li><strong>Evite dados pessoais óbvios</strong> na senha.</li>
<li><strong>Ative a verificação em duas etapas (2FA)</strong> sempre que possível.</li>
<li><strong>Considere um gerenciador de senhas</strong> pra não precisar memorizar tudo.</li>
</ul>')
on conflict(slug) do nothing;