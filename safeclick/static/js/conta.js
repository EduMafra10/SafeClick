(() => {
    for (const botao of document.querySelectorAll("[data-abrir]")) {
        botao.addEventListener("click", () => document.getElementById(botao.dataset.abrir)?.showModal());
    }
    for (const dialogo of document.querySelectorAll(".conta-dialogo")) {
        dialogo.querySelector("[data-fechar]")?.addEventListener("click", () => dialogo.close());
        dialogo.addEventListener("click", evento => {
            if (evento.target === dialogo) dialogo.close();
        });
        if (dialogo.hasAttribute("data-abrir-ao-carregar")) dialogo.showModal();
    }

    const links = [...document.querySelectorAll(".conta-menu a[data-secao]")];
    const marcar = id => links.forEach(link => link.setAttribute("aria-current", String(link.dataset.secao === id)));
    marcar("perfil");
    if ("IntersectionObserver" in window) {
        const observador = new IntersectionObserver(entradas => {
            const visivel = entradas.find(entrada => entrada.isIntersecting);
            if (visivel) marcar(visivel.target.id);
        }, { rootMargin: "0px 0px -60% 0px" });
        links.forEach(link => {
            const secao = document.getElementById(link.dataset.secao);
            if (secao) observador.observe(secao);
        });
    }
})();
