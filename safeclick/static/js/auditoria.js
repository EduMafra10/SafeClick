(() => {
    const formulario = document.querySelector(".auditoria-filtros");
    if (!formulario) return;

    formulario.addEventListener("submit", () => {
        for (const campo of formulario.querySelectorAll("input, select")) {
            if (!campo.value || (campo.type === "checkbox" && !campo.checked)) campo.disabled = true;
        }
    });

    window.addEventListener("pageshow", () => {
        formulario.querySelectorAll("[disabled]").forEach((campo) => { campo.disabled = false; });
    });
})();