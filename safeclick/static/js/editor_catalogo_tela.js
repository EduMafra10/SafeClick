(() => {
    const formulario = document.getElementById("editor-catalogo");
    if (!formulario) return;
    const secao = formulario.dataset.secao;
    const preenchido = elemento => Boolean(elemento && elemento.value.trim());

    const texto = formulario.querySelector("[data-formatavel]");
    const barra = formulario.querySelector(".admin-formatacao");

    function linhasSelecionadas(prefixo) {
        const inicio = texto.value.lastIndexOf("\n", texto.selectionStart - 1) + 1;
        let fim = texto.value.indexOf("\n", texto.selectionEnd);
        if (fim === -1) fim = texto.value.length;
        const linhas = texto.value.slice(inicio, fim).split("\n");
        const todas = linhas.every(linha => !linha.trim() || linha.startsWith(prefixo));
        const novas = linhas.map(linha => {
            if (!linha.trim()) return linha;
            if (todas) return linha.slice(prefixo.length);
            return prefixo + linha.replace(/^(## |- |> )/, "");
        });
        texto.setRangeText(novas.join("\n"), inicio, fim, "select");
    }

    function envolver(antes, depois, exemplo, selecionarDepois) {
        const { selectionStart: inicio, selectionEnd: fim } = texto;
        const escolhido = texto.value.slice(inicio, fim) || exemplo;
        texto.setRangeText(antes + escolhido + depois, inicio, fim, "end");
        if (selecionarDepois) {
            const fimDepois = inicio + antes.length + escolhido.length + depois.length - 1;
            texto.setSelectionRange(fimDepois - selecionarDepois.length, fimDepois);
        } else {
            texto.setSelectionRange(inicio + antes.length, inicio + antes.length + escolhido.length);
        }
    }

    barra?.addEventListener("click", evento => {
        const botao = evento.target.closest("[data-formato]");
        if (!botao || !texto) return;
        texto.focus();
        const acoes = {
            subtitulo: () => linhasSelecionadas("## "),
            lista: () => linhasSelecionadas("- "),
            destaque: () => linhasSelecionadas("> "),
            negrito: () => envolver("**", "**", "texto em negrito"),
            link: () => envolver("[", "](/endereco)", "texto do link", "/endereco"),
        };
        acoes[botao.dataset.formato]?.();
        texto.dispatchEvent(new Event("input", { bubbles: true }));
    });

    const titulo = formulario.elements.titulo;
    const endereco = formulario.querySelector("[data-endereco]");
    let enderecoManual = preenchido(endereco);

    function paraEndereco(valor) {
        return valor.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase()
            .replace(/[^a-z0-9]+/g, "-").replace(/^[^a-z]+/, "").replace(/-+$/, "")
            .slice(0, Number(endereco.maxLength) || 50).replace(/-+$/, "");
    }

    titulo?.addEventListener("input", () => {
        if (endereco && !enderecoManual) endereco.value = paraEndereco(titulo.value);
    });
    endereco?.addEventListener("input", () => {
        enderecoManual = preenchido(endereco);
    });

    const itens = (raiz, tipo) => [...raiz.querySelectorAll('[data-item="' + tipo + '"]')];
    const campo = (item, nome) => item.querySelector('[data-campo="' + nome + '"]');

    const cartoes = pergunta => itens(pergunta, "alternativa").map(a => campo(a, "texto").value.trim());

    function oficinaValida(perguntas) {
        if (perguntas.length < 2) return false;
        const banco = cartoes(perguntas[0]);
        if (new Set(banco).size !== banco.length || banco.length < perguntas.length || banco.includes("")) return false;
        const corretas = new Set();
        for (const pergunta of perguntas) {
            const atuais = cartoes(pergunta);
            if (atuais.length !== banco.length || !banco.every(cartao => atuais.includes(cartao))) return false;
            const marcada = itens(pergunta, "alternativa").find(a => campo(a, "correta").checked);
            if (!marcada || corretas.has(campo(marcada, "texto").value.trim())) return false;
            corretas.add(campo(marcada, "texto").value.trim());
        }
        return true;
    }

    function regras() {
        const r = { titulo: preenchido(titulo) };
        if (secao === "conteudos" || secao === "paginas") {
            r.texto = preenchido(texto);
        } else if (secao === "quizzes") {
            const perguntas = itens(formulario, "questao");
            r.perguntas = perguntas.length > 0 && perguntas.every(
                p => preenchido(campo(p, "enunciado")) && preenchido(campo(p, "explicacao")));
            r.alternativas = perguntas.length > 0 && perguntas.every(p => {
                const textos = cartoes(p);
                return textos.length >= 2 && !textos.includes("") && new Set(textos).size === textos.length;
            });
            r.corretas = perguntas.length > 0 && perguntas.every(
                p => itens(p, "alternativa").filter(a => campo(a, "correta").checked).length === 1);
            r.comentarios = perguntas.length > 0 && perguntas.every(p => {
                const alternativas = itens(p, "alternativa");
                const comentadas = alternativas.filter(a => preenchido(campo(a, "explicacao"))).length;
                return comentadas === 0 || comentadas === alternativas.length;
            });
            r.oficina = oficinaValida(perguntas);
        } else if (secao === "simulacoes") {
            const opcoes = itens(formulario, "opcao");
            const el = formulario.elements;
            r.resumo = preenchido(el.resumo);
            r.formato = Boolean(el.tipo.value);
            r.mensagem = preenchido(el.assunto) && preenchido(el.origem) && preenchido(el.mensagem);
            r.opcoes = opcoes.length >= 2 && opcoes.every(
                o => ["texto", "consequencia", "explicacao"].every(nome => preenchido(campo(o, nome))));
            const seguras = opcoes.filter(o => campo(o, "segura").checked).length;
            r.escolhas = seguras > 0 && seguras < opcoes.length;
            r.sinais = preenchido(el.sinais);
        }
        return r;
    }

    function atualizarLista() {
        const situacao = regras();
        const regraOficina = document.querySelector('[data-regra="oficina"]');
        if (regraOficina) regraOficina.hidden = formulario.elements.formato?.value !== "oficina";
        for (const item of document.querySelectorAll("[data-checklist] [data-regra]")) {
            item.classList.toggle("ok", Boolean(situacao[item.dataset.regra]));
        }
    }

    const alterado = document.querySelector("[data-alterado]");
    let mudou = false;

    function marcarAlteracao() {
        mudou = true;
        if (alterado) alterado.hidden = false;
        atualizarLista();
    }

    formulario.addEventListener("input", marcarAlteracao);
    formulario.addEventListener("change", marcarAlteracao);
    formulario.addEventListener("submit", () => {
        mudou = false;
    });

    document.querySelector("[data-publicar]")?.addEventListener("click", evento => {
        if (mudou && !window.confirm("Há alterações não salvas. A publicação usa a última versão salva. Continuar mesmo assim?")) {
            evento.preventDefault();
        } else {
            mudou = false;
        }
    });
    window.addEventListener("beforeunload", evento => {
        if (mudou) evento.preventDefault();
    });

    atualizarLista();
})();
