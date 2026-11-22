const editor = document.querySelector("form[data-editor]");

if (editor) {
    const aviso = editor.querySelector("[data-editor-mensagem]");
    const campo = (item, chave) => item.querySelector('[data-campo="' + chave + '"]');
    const itens = lista => [...lista.children].filter(item => item.matches("[data-item]"));

    function listaPara(botao) {
        const tipo = botao.dataset.tipo;
        const grupo = tipo === "alternativa" ? botao.closest("[data-item=questao]") : editor;
        return grupo.querySelector('[data-lista="' + tipo + '"]');
    }

    function atualizar() {
        for (const lista of editor.querySelectorAll("[data-lista]")) {
            const todos = itens(lista);
            todos.forEach((item, indice) => {
                item.querySelector(":scope > legend [data-numero]").textContent = indice + 1;
                item.querySelector(':scope > .admin-acoes [data-editor-acao="subir"]').disabled = indice === 0;
                item.querySelector(':scope > .admin-acoes [data-editor-acao="descer"]').disabled = indice === todos.length - 1;
            });
        }
        for (const botao of editor.querySelectorAll('[data-editor-acao="adicionar"]')) {
            const lista = listaPara(botao);
            botao.disabled = itens(lista).length >= Number(lista.dataset.limite);
        }
    }

    function estruturaAlterada() {
        atualizar();
        editor.dispatchEvent(new Event("input", { bubbles: true }));
    }

    editor.querySelector("[data-repetir-cartoes]")?.addEventListener("click", () => {
        const perguntas = itens(editor.querySelector('[data-lista="questao"]'));
        const listaDe = pergunta => pergunta.querySelector('[data-lista="alternativa"]');
        const textoDe = alternativa => campo(alternativa, "texto").value.trim();
        const banco = perguntas.length ? itens(listaDe(perguntas[0])).map(textoDe) : [];
        if (perguntas.length < 2 || banco.length < 2 || banco.includes("") || new Set(banco).size !== banco.length) {
            aviso.textContent = "Crie pelo menos dois trechos e preencha cartões diferentes no primeiro.";
            window.alert(aviso.textContent);
            return;
        }
        if (!window.confirm("Repetir os cartões do primeiro trecho? Cartões substituídos perderão o comentário e a marcação.")) return;
        const modelo = editor.querySelector('[data-modelo="alternativa"]');
        for (const pergunta of perguntas.slice(1)) {
            const lista = listaDe(pergunta);
            const existentes = new Map(itens(lista).map(a => [textoDe(a), a]));
            const ordenadas = banco.map(texto => {
                const alternativa = existentes.get(texto) || modelo.content.firstElementChild.cloneNode(true);
                campo(alternativa, "texto").value = texto;
                return alternativa;
            });
            lista.replaceChildren(...ordenadas);
        }
        estruturaAlterada();
        aviso.textContent = "Cartões repetidos. Confira o gabarito de cada trecho.";
    });

    editor.addEventListener("click", evento => {
        const botao = evento.target.closest("[data-editor-acao]");
        if (!botao || botao.disabled) return;
        const acao = botao.dataset.editorAcao;
        if (acao === "adicionar") {
            const lista = listaPara(botao);
            if (itens(lista).length >= Number(lista.dataset.limite)) return;
            const modelo = editor.querySelector('[data-modelo="' + botao.dataset.tipo + '"]');
            lista.append(modelo.content.cloneNode(true));
            estruturaAlterada();
            lista.lastElementChild.querySelector("[data-campo]").focus();
            aviso.textContent = "Item adicionado.";
            return;
        }

        const item = botao.closest("[data-item]");
        const lista = item.parentElement;
        if (acao === "remover") {
            const preenchido = [...item.querySelectorAll("input, textarea")].some(
                entrada => entrada.type === "checkbox" ? entrada.checked : entrada.value.trim(),
            );
            if (preenchido && !window.confirm("Remover este item do rascunho?")) return;
            const vizinho = item.nextElementSibling || item.previousElementSibling;
            item.remove();
            estruturaAlterada();
            const adicionar = [...editor.querySelectorAll('[data-editor-acao="adicionar"]')]
                .find(controle => listaPara(controle) === lista);
            (vizinho?.querySelector("[data-campo]") || adicionar)?.focus();
            aviso.textContent = "Item removido.";
        } else {
            if (acao === "subir" && item.previousElementSibling) {
                lista.insertBefore(item, item.previousElementSibling);
            } else if (acao === "descer" && item.nextElementSibling) {
                lista.insertBefore(item.nextElementSibling, item);
            }
            estruturaAlterada();
            (botao.disabled ? item.querySelector("[data-campo]") : botao).focus();
            aviso.textContent = "Ordem atualizada.";
        }
    });

    function atualizarProduto() {
        const produto = editor.querySelector("[data-produto]");
        if (produto) produto.hidden = editor.elements.tipo.value !== "loja";
    }

    editor.addEventListener("change", evento => {
        if (evento.target.name === "tipo") atualizarProduto();
        if (evento.target.matches('[data-campo="correta"]:checked')) {
            const pergunta = evento.target.closest("[data-item=questao]");
            for (const caixa of pergunta.querySelectorAll('[data-campo="correta"]')) {
                if (caixa !== evento.target) caixa.checked = false;
            }
        }
    });

    editor.addEventListener("submit", () => {
        let estrutura;
        if (editor.dataset.editor === "quizzes") {
            estrutura = itens(editor.querySelector("[data-lista=questao]")).map(pergunta => ({
                enunciado: campo(pergunta, "enunciado").value,
                explicacao: campo(pergunta, "explicacao").value,
                alternativas: itens(pergunta.querySelector("[data-lista=alternativa]")).map(opcao => ({
                    texto: campo(opcao, "texto").value,
                    correta: campo(opcao, "correta").checked,
                    explicacao: campo(opcao, "explicacao").value,
                })),
            }));
        } else {
            estrutura = itens(editor.querySelector("[data-lista=opcao]")).map(opcao => ({
                texto: campo(opcao, "texto").value,
                consequencia: campo(opcao, "consequencia").value,
                explicacao: campo(opcao, "explicacao").value,
                segura: campo(opcao, "segura").checked,
            }));
        }
        editor.elements.estrutura.value = JSON.stringify(estrutura);
    });

    atualizar();
    atualizarProduto();
    document.querySelector('[data-salvar-estrutura]').disabled = false;
}
