(() => {
    const grupo = document.querySelector("[data-quiz-abas]");
    if (!grupo) return;
    const abas = [...grupo.querySelectorAll('[role="tab"]')];
    const paineis = abas.map((aba) => document.getElementById(aba.getAttribute("aria-controls")));

    abas.forEach((aba, indice) => {
        paineis[indice].setAttribute("role", "tabpanel");
        paineis[indice].setAttribute("aria-labelledby", aba.id);
    });

    function selecionar(indice, focar = false) {
        abas.forEach((aba, i) => {
            const ativa = i === indice;
            aba.setAttribute("aria-selected", String(ativa));
            aba.tabIndex = ativa ? 0 : -1;
            paineis[i].hidden = !ativa;
        });
        if (focar) abas[indice].focus();
        history.replaceState(null, "", indice ? "#oficina" : location.pathname + location.search);
    }

    abas.forEach((aba, indice) => {
        aba.addEventListener("click", () => selecionar(indice));
        aba.addEventListener("keydown", (evento) => {
            const passo = { ArrowRight: 1, ArrowLeft: -1 }[evento.key];
            if (!passo) return;
            evento.preventDefault();
            selecionar((indice + passo + abas.length) % abas.length, true);
        });
    });

    grupo.hidden = false;
    selecionar(location.hash === "#oficina" ? 1 : 0);
})();
