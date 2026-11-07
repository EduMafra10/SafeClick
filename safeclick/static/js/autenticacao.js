document.querySelectorAll("[data-alternar-senha]").forEach((botao) => {
    const campo = document.getElementById(botao.getAttribute("aria-controls"));

    if (!campo) {
        return;
    }

    botao.addEventListener("click", () => {
        const mostrar = campo.type === "password";

        campo.type = mostrar ? "text" : "password";
        botao.textContent = mostrar ? "Ocultar" : "Mostrar";
        botao.setAttribute("aria-label", mostrar ? "Ocultar senha" : "Mostrar senha");
    });

    botao.hidden = false;
});