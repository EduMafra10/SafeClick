
(() => {
    const painel = document.getElementById("painel-desafio");
    if (!painel || !window.fetch) return;

    const token = document.getElementById("csrf-desafio").value;
    const iniciar = document.getElementById("iniciar-desafio");
    const inicio = document.getElementById("desafio-inicio");
    const rodada = document.getElementById("desafio-rodada");
    const progresso = document.getElementById("desafio-progresso");
    const numeroRodada = document.getElementById("numero-rodada");
    const totalRodadas = document.getElementById("total-rodadas");
    const placar = document.getElementById("placar-desafio");
    const opcoes = [...painel.querySelectorAll(".lab-desafio-opcao")];
    const resultado = document.getElementById("desafio-resultado");
    const veredito = document.getElementById("veredito-desafio");
    const comparacao = document.getElementById("comparacao-desafio");
    const proxima = document.getElementById("proxima-rodada");
    const final = document.getElementById("desafio-final");
    const acertosFinal = document.getElementById("acertos-final");
    const totalFinal = document.getElementById("total-final");
    const mensagemFinal = document.getElementById("mensagem-final");
    const jogarNovamente = document.getElementById("jogar-novamente");
    const erro = document.getElementById("erro-desafio");
    const historico = document.getElementById("historico-desafio");

    const numero = new Intl.NumberFormat("pt-BR");
    let rodadaAtual = null;
    let ultimaResposta = null;

    function mostrarEtapa(etapa) {
        for (const elemento of [inicio, rodada, resultado, final]) {
            elemento.hidden = elemento !== etapa;
        }
        progresso.hidden = etapa !== rodada && etapa !== resultado;
    }

    function linhaDaRodada(numeroDaRodada) {
        return historico?.children[numeroDaRodada - 1] ?? null;
    }

    function prepararHistorico(total) {
        if (!historico) return;
        historico.replaceChildren(...Array.from({ length: total }, (_, indice) => {
            const linha = document.createElement("li");
            const marcador = document.createElement("span");
            marcador.className = "lab-rodada-numero";
            marcador.textContent = indice + 1;
            const texto = document.createElement("span");
            texto.className = "lab-rodada-texto";
            texto.textContent = "Aguardando";
            linha.append(marcador, texto);
            return linha;
        }));
    }

    function marcarRodada(numeroDaRodada, dados) {
        const linha = linhaDaRodada(numeroDaRodada);
        if (!linha) return;
        const texto = linha.querySelector(".lab-rodada-texto");
        if (!dados) {
            linha.dataset.estado = "atual";
            texto.textContent = "Em andamento";
            return;
        }
        const vencedora = dados.resultado.reduce((maior, item) => (item.vazamentos > maior.vazamentos ? item : maior));
        linha.dataset.estado = dados.correta ? "acerto" : "erro";
        const par = document.createElement("span");
        par.className = "lab-rodada-par";
        dados.resultado.forEach((item, indice) => {
            if (indice) par.append(" × ");
            const senha = document.createElement("code");
            senha.textContent = item.senha;
            par.append(senha);
        });
        const detalhe = document.createElement("small");
        detalhe.textContent = `${vencedora.senha} vazou mais`;
        const situacao = document.createElement("strong");
        situacao.className = "lab-rodada-situacao";
        situacao.textContent = dados.correta ? "Acertou" : "Errou";
        texto.replaceChildren(par, detalhe);
        linha.append(situacao);
    }

    function mostrarErro(mensagem) {
        erro.textContent = mensagem;
        erro.hidden = !mensagem;
    }

    
    async function enviar(url, campos) {
        const resposta = await fetch(url, {
            method: "POST",
            body: new URLSearchParams({ ...campos, csrf_token: token }),
            headers: { Accept: "application/json" },
            credentials: "same-origin",
        });

        let dados = {};
        try {
            dados = await resposta.json();
        } catch {
            
        }

        if (!resposta.ok || resposta.redirected) {
            const falha = new Error(dados.erro || "Não foi possível continuar. Recarregue a página.");
            falha.status = resposta.status;
            throw falha;
        }
        return dados;
    }

    function exibirRodada(dados) {
        rodadaAtual = dados;
        numeroRodada.textContent = dados.rodada;
        totalRodadas.textContent = dados.total;
        marcarRodada(dados.rodada, null);
        dados.opcoes.forEach((senha, indice) => {
            opcoes[indice].textContent = senha;
            opcoes[indice].disabled = false;
        });
        mostrarEtapa(rodada);
        opcoes[0].focus();
    }

    function atualizarPlacar(acertos) {
        placar.textContent = `${acertos} ${acertos === 1 ? "acerto" : "acertos"}`;
    }

    function exibirResultado(dados) {
        ultimaResposta = dados;
        atualizarPlacar(dados.acertos);
        marcarRodada(rodadaAtual.rodada, dados);

        veredito.dataset.correta = String(dados.correta);
        veredito.textContent = dados.correta
            ? "Acertou! Essa senha apareceu mais nos vazamentos."
            : "Não foi dessa vez. A outra senha apareceu mais.";

        const maior = Math.max(...dados.resultado.map((item) => item.vazamentos), 1);

        comparacao.replaceChildren(...dados.resultado.map((item, indice) => {
            const linha = document.createElement("li");
            linha.dataset.maior = String(item.vazamentos === maior);

            const topo = document.createElement("div");
            topo.className = "lab-comparacao-topo";
            const nome = document.createElement("span");
            nome.className = "lab-comparacao-nome";
            const senha = document.createElement("code");
            senha.textContent = item.senha;
            nome.append(senha);
            if (indice === dados.escolha) {
                const marca = document.createElement("span");
                marca.className = "lab-marca";
                marca.textContent = "Sua escolha";
                nome.append(marca);
            }
            const vezes = document.createElement("strong");
            vezes.textContent = `${numero.format(item.vazamentos)} ${item.vazamentos === 1 ? "vez" : "vezes"}`;
            topo.append(nome, vezes);

            const barra = document.createElement("div");
            barra.className = "lab-comparacao-barra";
            barra.setAttribute("aria-hidden", "true");
            const preenchimento = document.createElement("span");
            preenchimento.style.width = `${(item.vazamentos / maior) * 100}%`;
            barra.append(preenchimento);

            const licao = document.createElement("p");
            licao.textContent = item.licao;

            linha.append(topo, barra, licao);
            return linha;
        }));

        proxima.textContent = dados.final ? "Ver resultado" : "Próxima rodada";
        mostrarEtapa(resultado);
        proxima.focus();
    }

    function exibirFinal({ acertos, total }) {
        acertosFinal.textContent = acertos;
        totalFinal.textContent = total;

        const proporcao = acertos / total;
        mensagemFinal.textContent = proporcao >= 0.8
            ? "Excelente! Você reconhece bem as senhas que os criminosos testam primeiro."
            : proporcao >= 0.5
                ? "Bom resultado! Repare nas lições: senhas populares são as primeiras a cair."
                : "Senhas que parecem diferentes podem ser igualmente previsíveis. Jogue de novo e compare.";

        mostrarEtapa(final);
        jogarNovamente.focus();
    }

    async function comecar() {
        mostrarErro("");
        iniciar.disabled = jogarNovamente.disabled = true;
        try {
            const dados = await enviar(painel.dataset.iniciarUrl, {});
            atualizarPlacar(0);
            prepararHistorico(dados.total);
            exibirRodada(dados);
        } catch (falha) {
            mostrarErro(falha.message);
            mostrarEtapa(final.hidden ? inicio : final);
        } finally {
            iniciar.disabled = jogarNovamente.disabled = false;
        }
    }

    async function responder(escolha) {
        mostrarErro("");
        opcoes.forEach((opcao) => { opcao.disabled = true; });
        try {
            const dados = await enviar(painel.dataset.responderUrl, {
                escolha: String(escolha),
                rodada: String(rodadaAtual.rodada),
            });
            exibirResultado(dados);
        } catch (falha) {
            mostrarErro(falha.message);
            if (falha.status === 409) {
                
                mostrarEtapa(inicio);
            } else {
                
                opcoes.forEach((opcao) => { opcao.disabled = false; });
            }
        }
    }

    iniciar.addEventListener("click", comecar);
    jogarNovamente.addEventListener("click", comecar);
    opcoes.forEach((opcao) => {
        opcao.addEventListener("click", () => responder(Number(opcao.dataset.escolha)));
    });
    proxima.addEventListener("click", () => {
        if (ultimaResposta.final) {
            exibirFinal(ultimaResposta.final);
        } else {
            exibirRodada(ultimaResposta.proxima);
        }
    });

    iniciar.disabled = false;
})();