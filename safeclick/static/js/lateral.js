(function () {
    const lateral = document.querySelector("[data-lateral]");
    if (!lateral) {
        return;
    }

    const botao = lateral.querySelector(".lateral-abrir");
    const estreita = window.matchMedia("(max-width: 900px)");

    function definir(aberta) {
        botao.setAttribute("aria-expanded", String(aberta));
        lateral.classList.toggle("lateral--aberta", aberta);
    }

    lateral.classList.add("lateral--js");
    botao.addEventListener("click", () => definir(botao.getAttribute("aria-expanded") !== "true"));

    document.addEventListener("keydown", (evento) => {
        if (evento.key === "Escape" && lateral.classList.contains("lateral--aberta")) {
            definir(false);
            botao.focus();
        }
    });

    estreita.addEventListener("change", () => definir(false));
})();
