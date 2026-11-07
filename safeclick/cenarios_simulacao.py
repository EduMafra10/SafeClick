# Conteúdo fictício usado nas atividades educativas do SafeClick
# As chaves dos cenários e das opções identificam as respostas no banco
# Os endereços e as chamadas são textos da simulação, sem links externos

CENARIOS = {
    "conta_bloqueada": {
        "slug": "conta-bloqueada",
        "titulo": "Aviso de conta bloqueada",
        "resumo": "Um e-mail ameaça bloquear sua conta e pede seus dados.",
        "canal": "E-mail fictício",
        "origem": "Equipe de segurança · suporte@verificacao-conta.example",
        "assunto": "Sua conta será bloqueada em 30 minutos!",
        "mensagem": [
            "Identificamos uma atividade suspeita na sua conta.",
            "Para evitar o bloqueio da sua conta, confirme imediatamente seus dados pelo link enviado abaixo.",
            "Caso a confirmação não seja realizada em até 30 minutos, seu acesso será bloqueado.",
        ],
        "chamada": "CONFIRMAR MEUS DADOS",
        "sinais": [
            "Pressão para responder imediatamente.",
            "Ameaça de bloqueio com prazo curto.",
            "Pedido de dados pessoais por uma mensagem não verificada.",
            "Convite para acessar um endereço fornecido pelo próprio remetente.",
        ],
        "opcoes": {
            "clicar_link": {
                "texto": "Clicar no link e informar meus dados",
                "consequencia": "Nessa situação simulada, seus dados seriam entregues para uma página fraudulenta.",
                "explicacao": "A urgência que o e-mail propõe e a ameaça de bloqueio tentam te induzir a uma ação sem verificação.",
                "segura": False,
            },
            "responder_email": {
                "texto": "Responder ao e-mail enviando meus dados para confirmar minha identidade.",
                "consequencia": "Nessa situação simulada, seus dados seriam enviados ao remetente que está tentando aplicar a fraude.",
                "explicacao": "Responder à mensagem não confirma a identidade do remetente, nem torna seguro compartilhar informações pessoais.",
                "segura": False,
            },
            "acessar_canal_oficial": {
                "texto": "Abrir o aplicativo ou acessar o site oficial que já tenho conhecimento para verificar se está tudo certo com a conta.",
                "consequencia": "Dessa forma, você evita fornecer seus dados por essa mensagem suspeita e verifica a situação por um canal válido.",
                "explicacao": "A conferência acontece sem depender dos links suspeitos ou dos contatos fornecidos pelo próprio e-mail.",
                "segura": True,
            },
        },
    },
    "entrega_sms": {
        "slug": "entrega-sms",
        "titulo": "Taxa para liberar uma entrega",
        "resumo": "Um SMS cobra uma taxa urgente para liberar uma encomenda.",
        "canal": "SMS fictício",
        "origem": "Remetente desconhecido",
        "assunto": "Sua encomenda está retida",
        "mensagem": [
            "Não conseguimos concluir sua entrega por uma pendência no endereço.",
            "Pague uma taxa de R$ 4,90 nos próximos 20 minutos para evitar a devolução.",
            "Atualize seus dados e efetue o pagamento em entrega-pendente.example.",
        ],
        "chamada": "REGULARIZAR ENTREGA",
        "sinais": [
            "Cobrança inesperada sem identificar claramente o pedido.",
            "Prazo curto acompanhado de ameaça de devolução.",
            "Pedido de dados e pagamento por um endereço recebido no SMS.",
            "Valor pequeno usado para incentivar uma decisão rápida.",
        ],
        "opcoes": {
            "consultar_pedido": {
                "texto": "Abrir o aplicativo ou site oficial da compra e consultar o pedido por lá.",
                "consequencia": "Você verifica a entrega sem informar dados ou pagar pelo endereço da mensagem suspeita.",
                "explicacao": "Consulte o pedido e o rastreamento pelo canal oficial que você já utiliza. Se precisar de atendimento, procure o contato nesse canal.",
                "segura": True,
            },
            "pagar_taxa": {
                "texto": "Pagar a taxa pelo link, pois o valor é pequeno.",
                "consequencia": "Nesta simulação, o pagamento seria direcionado ao fraudador e seus dados poderiam ser coletados.",
                "explicacao": "Um valor baixo não comprova a legitimidade da cobrança. A urgência tenta impedir que você confira a origem do pedido.",
                "segura": False,
            },
            "informar_dados": {
                "texto": "Abrir o link e informar meu CPF e endereço, sem fazer o pagamento.",
                "consequencia": "Mesmo sem pagar, você entregaria dados pessoais ao responsável pela página falsa.",
                "explicacao": "A fraude também pode buscar informações pessoais. Evite preencher formulários recebidos por mensagens cuja origem você não confirmou.",
                "segura": False,
            },
        },
    },
    "falso_conhecido": {
        "slug": "falso-conhecido",
        "titulo": "Pedido de Pix de um conhecido",
        "resumo": "Um novo número usa nome e foto conhecidos para pedir dinheiro.",
        "canal": "Conversa fictícia",
        "origem": "Número novo com nome e foto de um conhecido",
        "assunto": "Troquei de número e preciso de uma ajuda",
        "mensagem": [
            "Oi! Salva meu número novo. O antigo parou de funcionar.",
            "Preciso pagar uma conta agora, mas meu aplicativo do banco está bloqueado. Faz um Pix de R$ 480 para mim? Depois te devolvo.",
            "A conta está no nome de outra pessoa. Não consigo atender ligação agora, estou com muita pressa.",
        ],
        "chamada": "FAZER O PIX AGORA",
        "sinais": [
            "Contato por um número novo alegando ser alguém conhecido.",
            "Pedido urgente de dinheiro.",
            "Transferência para uma conta de outra pessoa.",
            "Recusa de uma ligação para confirmar a identidade.",
        ],
        "opcoes": {
            "transferir_pela_foto": {
                "texto": "Fazer o Pix porque reconheci o nome e a foto do contato.",
                "consequencia": "Nesta simulação, o dinheiro seria enviado para a conta indicada pelo fraudador.",
                "explicacao": "Nome e foto podem ser copiados. Esses elementos não comprovam que você está conversando com a pessoa conhecida.",
                "segura": False,
            },
            "confirmar_contato": {
                "texto": "Confirmar o pedido com a pessoa pelo número que eu já tinha ou pessoalmente, antes de transferir.",
                "consequencia": "Você interrompe a pressão por uma transferência imediata e verifica se o pedido é verdadeiro.",
                "explicacao": "Use um contato que você já conhecia, sem depender das informações fornecidas na conversa suspeita. Se não conseguir confirmar, não faça a transferência.",
                "segura": True,
            },
            "pedir_dados_pessoais": {
                "texto": "Perguntar o nome completo e a data de nascimento e transferir se responder corretamente.",
                "consequencia": "Você ainda poderia transferir dinheiro ao fraudador, mesmo recebendo respostas corretas.",
                "explicacao": "Informações pessoais podem estar disponíveis publicamente ou ter sido expostas. Saber esses dados não comprova a identidade de quem envia a mensagem.",
                "segura": False,
            },
        },
    },
    "loja_falsa": {
        "slug": "loja-falsa",
        "titulo": "Promoção em uma loja desconhecida",
        "resumo": "Um anúncio oferece um produto muito barato e exige pagamento por Pix.",
        "canal": "Loja virtual fictícia",
        "origem": "Loja Oferta Expressa · oferta-expressa.example",
        "assunto": "Celular de R$ 2.499 por apenas R$ 299!",
        "produto": {
            "nome": "Celular",
            "preco_anterior": "R$ 2.499",
            "preco_atual": "R$ 299",
        },
        "mensagem": [
            "Oferta exclusiva para quem chegou pelo anúncio. Frete grátis para todo o Brasil!",
            "Restam apenas 5 minutos. O desconto é válido somente para pagamento por Pix.",
            "Site com HTTPS e depoimentos de clientes satisfeitos. Pague agora para garantir o preço!",
        ],
        "chamada": "COMPRAR COM DESCONTO",
        "sinais": [
            "Preço muito abaixo do habitual combinado com pressão para pagar.",
            "Loja desconhecida encontrada por um anúncio.",
            "Desconto condicionado ao pagamento imediato por Pix.",
            "Depoimentos e alegações de segurança apresentados apenas pela própria loja.",
        ],
        "opcoes": {
            "comprar_por_https": {
                "texto": "Comprar porque o endereço usa HTTPS e isso garante que a loja é confiável.",
                "consequencia": "Nesta simulação, você faria um pagamento a uma loja falsa, apesar de a conexão usar HTTPS.",
                "explicacao": "HTTPS protege a conexão, mas não comprova que o vendedor é legítimo. Páginas fraudulentas também podem usar HTTPS.",
                "segura": False,
            },
            "confiar_depoimentos": {
                "texto": "Confiar nos depoimentos do próprio site e pagar antes que a promoção termine.",
                "consequencia": "Você poderia pagar sem receber o produto, confiando em avaliações criadas pela própria página fraudulenta.",
                "explicacao": "Depoimentos dentro da loja podem ser fabricados. O contador de tempo tenta reduzir a chance de você pesquisar antes da compra.",
                "segura": False,
            },
            "verificar_loja": {
                "texto": "Pesquisar o vendedor, conferir o endereço e buscar avaliações independentes antes de comprar.",
                "consequencia": "Você evita pagar sob pressão e reúne informações para avaliar a autenticidade da loja.",
                "explicacao": "Compare preços, confira os dados do vendedor em fontes independentes e procure seu canal oficial. Nenhum sinal isolado garante confiança; se não conseguir verificar a loja, não prossiga com a compra.",
                "segura": True,
            },
        },
    },
}