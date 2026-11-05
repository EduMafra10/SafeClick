// Envia só os filtros preenchidos, para a URL ficar limpa.
(() => {
    const formulario = document.querySelector(".auditoria-filtros");
    if (!formulario) return;

    formulario.addEventListener("submit", () => {
        for (const campo of formulario.querySelectorAll("input, select")) {
            if (!campo.value || (campo.type === "checkbox" && !campo.checked)) campo.disabled = true;
        }
    });

    // Ao voltar pela seta do navegador, os campos precisam estar ativos de novo.
    window.addEventListener("pageshow", () => {
        formulario.querySelectorAll("[disabled]").forEach((campo) => { campo.disabled = false; });
    });
})();