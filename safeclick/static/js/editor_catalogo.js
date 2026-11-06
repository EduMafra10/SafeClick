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

    editor.addEventListener("click", evento => {
        const botao = evento.target.closest("[data-editor-acao]");
        if (!botao || botao.disabled) return;
        const acao = botao.dataset.editorAcao;
        if (acao === "adicionar") {
            const lista = listaPara(botao);
            if (itens(lista).length >= Number(lista.dataset.limite)) return;
            const modelo = editor.querySelector('[data-modelo="' + botao.dataset.tipo + '"]');
            lista.append(modelo.content.cloneNode(true));
            atualizar();
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
            atualizar();
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
            atualizar();
            (botao.disabled ? item.querySelector("[data-campo]") : botao).focus();
            aviso.textContent = "Ordem atualizada.";
        }
    });

    const tipo = editor.querySelector('[name="tipo"]');
    function atualizarProduto() {
        if (tipo) editor.querySelector("[data-produto]").hidden = tipo.value !== "loja";
    }

    editor.addEventListener("change", evento => {
        if (evento.target === tipo) atualizarProduto();
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
}
