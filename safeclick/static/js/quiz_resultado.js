(() => {
    const grupo = document.querySelector("[data-resultado-filtro]");
    if (!grupo) return;
    const botoes = [...grupo.querySelectorAll("[data-filtro]")];
    const itens = [...document.querySelectorAll(".qz-respostas > li")];

    botoes.forEach((botao) => {
        botao.addEventListener("click", () => {
            const soRevisar = botao.dataset.filtro === "revisar";
            botoes.forEach((outro) => outro.setAttribute("aria-pressed", String(outro === botao)));
            itens.forEach((item) => {
                item.hidden = soRevisar && item.querySelector("[data-acertou]").dataset.acertou === "sim";
            });
        });
    });
    grupo.hidden = false;
})();
