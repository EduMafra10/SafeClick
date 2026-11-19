(function () {
    const MOSTRAR = "Mostrar o e-mail completo. A visualização fica registrada na auditoria.";
    const OCULTAR = "Ocultar o e-mail";

    function trocar(usuario, email) {
        document.querySelectorAll(`[data-email-usuario="${usuario}"]`).forEach((bloco) => {
            const texto = bloco.querySelector(".admin-email-texto");
            const botao = bloco.querySelector(".admin-email-botao");
            if (email) {
                bloco.dataset.mascara = texto.textContent;
                texto.textContent = email;
                bloco.dataset.revelado = "1";
            } else {
                texto.textContent = bloco.dataset.mascara;
                delete bloco.dataset.revelado;
            }
            botao.setAttribute("aria-label", email ? OCULTAR : MOSTRAR);
            botao.title = email ? OCULTAR : "Mostrar e-mail completo (fica registrado na auditoria)";
            botao.setAttribute("aria-pressed", email ? "true" : "false");
            botao.classList.remove("admin-email-botao--erro");
        });
    }

    document.addEventListener("submit", async (evento) => {
        const formulario = evento.target.closest(".admin-email-form");
        if (!formulario) {
            return;
        }
        evento.preventDefault();

        const bloco = formulario.closest("[data-email-usuario]");
        const usuario = bloco.dataset.emailUsuario;
        // Ocultar não consulta o servidor; mostrar de novo gera outro registro na auditoria.
        if (bloco.dataset.revelado) {
            trocar(usuario, null);
            return;
        }

        const botao = formulario.querySelector("button");
        botao.disabled = true;
        try {
            const resposta = await fetch(formulario.action, {
                method: "POST",
                body: new FormData(formulario),
                headers: { Accept: "application/json" },
                credentials: "same-origin",
            });
            if (!resposta.ok) {
                throw new Error(String(resposta.status));
            }
            const { email } = await resposta.json();
            trocar(usuario, email);
        } catch (erro) {
            botao.title = "Não foi possível mostrar o e-mail. Recarregue a página e tente de novo.";
            botao.classList.add("admin-email-botao--erro");
        } finally {
            botao.disabled = false;
        }
    });
})();
