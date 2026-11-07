// Nada do que a pessoa digita sai do navegador: a análise roda em um Web Worker.

(() => {
    // ---------- Abas ----------
    const listaAbas = document.querySelector(".lab-abas");
    if (!listaAbas) return;

    const abas = [...listaAbas.querySelectorAll('[role="tab"]')];
    const paineis = abas.map((aba) => document.getElementById(aba.getAttribute("aria-controls")));

    
    const nomeDaAba = (aba) => aba.id.replace("aba-", "");

    function selecionar(abaEscolhida, focar = false) {
        abas.forEach((aba, indice) => {
            const ativa = aba === abaEscolhida;
            aba.setAttribute("aria-selected", String(ativa));
            aba.tabIndex = ativa ? 0 : -1;
            paineis[indice].hidden = !ativa;
        });

        if (focar) abaEscolhida.focus();
        history.replaceState(null, "", `#${nomeDaAba(abaEscolhida)}`);
    }

    abas.forEach((aba, indice) => {
        aba.addEventListener("click", () => selecionar(aba));

        
        aba.addEventListener("keydown", (evento) => {
            const destino = {
                ArrowRight: abas[(indice + 1) % abas.length],
                ArrowLeft: abas[(indice - 1 + abas.length) % abas.length],
                Home: abas[0],
                End: abas[abas.length - 1],
            }[evento.key];

            if (!destino) return;
            evento.preventDefault();
            selecionar(destino, true);
        });
    });

    const inicial = abas.find((aba) => `#${nomeDaAba(aba)}` === location.hash) ?? abas[0];
    listaAbas.hidden = false;
    document.getElementById("aviso-javascript")?.remove();
    selecionar(inicial);

    // ---------- Analisador ----------
    const area = document.querySelector(".lab-analisador");
    const campo = document.getElementById("senha-analise");
    const mostrar = document.getElementById("mostrar-senha");
    const resultado = document.getElementById("resultado-analise");
    const rotulo = document.getElementById("rotulo-forca");
    const aviso = document.getElementById("aviso-forca");
    const sugestoes = document.getElementById("sugestoes-forca");
    const itemComprimento = document.getElementById("item-comprimento");
    const itemPadroes = document.getElementById("item-padroes");
    const contagem = document.getElementById("contagem-caracteres");

    const NIVEIS = ["Muito fraca", "Fraca", "Moderada", "Boa", "Forte"];
    const MINIMO_RECOMENDADO = 15;

    if (!window.Worker) {
        rotulo.textContent = "Indisponível neste navegador";
        return;
    }

    let worker = null;
    let sequencia = 0;
    let pausa = null;
    let prazo = null;

    function marcar(item, ok) {
        item.dataset.ok = String(ok);
    }

    
    function limpar() {
        resultado.dataset.estado = "vazio";
        delete resultado.dataset.nivel;
        rotulo.textContent = "Aguardando";
        aviso.textContent = contagem.textContent = "";
        aviso.hidden = sugestoes.hidden = true;
        sugestoes.replaceChildren();
        delete itemComprimento.dataset.ok;
        delete itemPadroes.dataset.ok;
    }

    function reiniciarWorker() {
        worker?.terminate();
        worker = null;
    }

    function mostrarAvaliacao(senha, avaliacao) {
        
        const tamanho = [...senha].length;
        contagem.textContent = `(${tamanho} agora)`;
        marcar(itemComprimento, tamanho >= MINIMO_RECOMENDADO);
        resultado.dataset.estado = "resultado";

        if (!avaliacao) {
            rotulo.textContent = "Indisponível";
            aviso.textContent = "Não foi possível estimar a força agora. Tente novamente em instantes.";
            aviso.hidden = false;
            marcar(itemPadroes, false);
            return;
        }

        resultado.dataset.nivel = String(avaliacao.nivel);
        rotulo.textContent = NIVEIS[avaliacao.nivel];
        marcar(itemPadroes, avaliacao.nivel >= 3 && !avaliacao.aviso);

        aviso.textContent = avaliacao.aviso;
        aviso.hidden = !avaliacao.aviso;

        sugestoes.replaceChildren(...avaliacao.orientacoes.map((texto) => {
            const item = document.createElement("li");
            item.textContent = texto; 
            return item;
        }));
        sugestoes.hidden = avaliacao.orientacoes.length === 0;
    }

    
    function avaliacaoValida(a) {
        return a && Number.isInteger(a.nivel) && a.nivel >= 0 && a.nivel <= 4 &&
            typeof a.aviso === "string" && Array.isArray(a.orientacoes) &&
            a.orientacoes.every((item) => typeof item === "string");
    }

    function analisar(senha) {
        const numero = ++sequencia;
        clearTimeout(prazo);

        const concluir = (avaliacao) => {
            if (numero !== sequencia) return; 
            clearTimeout(prazo);
            if (!avaliacao) reiniciarWorker();
            mostrarAvaliacao(senha, avaliacao);
        };

        try {
            worker ??= new Worker(area.dataset.workerUrl);

           
            worker.onmessage = ({ data }) => {
                if (!data || data.id !== numero) return;
                concluir(avaliacaoValida(data.avaliacao) ? data.avaliacao : null);
            };
            worker.onerror = (evento) => {
                evento.preventDefault();
                concluir(null);
            };

            
            prazo = setTimeout(() => concluir(null), 8000);
            worker.postMessage({ id: numero, senha });
        } catch {
            concluir(null);
        }
    }

    campo.addEventListener("input", () => {
        clearTimeout(pausa);
        sequencia += 1; 

        if (!campo.value) {
            limpar();
            return;
        }

        
        rotulo.textContent = "Analisando…";
        resultado.dataset.estado = "analisando";
        delete resultado.dataset.nivel;
        pausa = setTimeout(() => analisar(campo.value), 300);
    });

    mostrar.addEventListener("click", () => {
        const visivel = campo.type === "password";
        campo.type = visivel ? "text" : "password";
        mostrar.textContent = visivel ? "Ocultar" : "Mostrar";
        mostrar.setAttribute("aria-pressed", String(visivel));
    });

    
    window.addEventListener("pagehide", () => {
        campo.value = "";
        limpar();
        reiniciarWorker();
    });

    campo.disabled = mostrar.disabled = false;
})();