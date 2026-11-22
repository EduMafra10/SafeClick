// Mostra uma pergunta por vez com o mapa ao lado. O formulário continua o mesmo e é enviado de uma vez no final.
(() => {
    const formulario = document.querySelector("[data-quiz-formulario]");
    const perguntas = [...document.querySelectorAll("[data-quiz-pergunta]")];
    if (!formulario || !perguntas.length) return;

    const links = [...document.querySelectorAll("[data-quiz-ir]")];
    const contagem = document.querySelector("[data-quiz-contagem]");
    const dica = document.querySelector("[data-quiz-dica]");
    const finalizar = document.querySelector("[data-quiz-finalizar]");
    const falta = document.querySelector("[data-quiz-falta]");
    let atual = 0;

    const respondida = (pergunta) => Boolean(pergunta.querySelector('input[type="radio"]:checked'));

    function atualizarMapa() {
        const total = perguntas.filter(respondida).length;
        links.forEach((link, indice) => {
            const feita = respondida(perguntas[indice]);
            const item = link.parentElement;
            item.classList.toggle("qz-feita", feita);
            item.classList.toggle("qz-atual", indice === atual);
            link.querySelector("[data-quiz-rotulo]").textContent =
                indice === atual ? "Agora" : feita ? "Respondida" : `Pergunta ${indice + 1}`;
            if (indice === atual) link.setAttribute("aria-current", "step");
            else link.removeAttribute("aria-current");
        });
        contagem.textContent = `${total} de ${perguntas.length} respondidas`;
        const completo = total === perguntas.length;
        finalizar.classList.toggle("qz-botao--espera", !completo);
        dica.textContent = completo
            ? "Tudo respondido. Revise se quiser e finalize."
            : "Libera quando todas forem respondidas.";
    }

    function mostrar(indice, focar = false) {
        atual = Math.max(0, Math.min(indice, perguntas.length - 1));
        perguntas.forEach((pergunta, i) => pergunta.classList.toggle("qz-atual", i === atual));
        atualizarMapa();
        if (focar) perguntas[atual].focus({ preventScroll: true });
        if (focar && perguntas[atual].getBoundingClientRect().top < 0) {
            perguntas[atual].scrollIntoView({ block: "start" });
        }
    }

    perguntas.forEach((pergunta) => {
        pergunta.tabIndex = -1;
        pergunta.querySelector("[data-quiz-nav]").hidden = false;
        pergunta.querySelector("[data-quiz-anterior]")?.addEventListener("click", () => mostrar(atual - 1, true));
        pergunta.querySelector("[data-quiz-proxima]")?.addEventListener("click", () => mostrar(atual + 1, true));
        pergunta.addEventListener("change", () => {
            falta.hidden = true;
            atualizarMapa();
        });
    });

    links.forEach((link, indice) => {
        link.addEventListener("click", (evento) => {
            evento.preventDefault();
            mostrar(indice, true);
        });
    });

    formulario.noValidate = true;
    formulario.addEventListener("submit", (evento) => {
        const pendente = perguntas.findIndex((pergunta) => !respondida(pergunta));
        if (pendente === -1) return;
        evento.preventDefault();
        const faltando = perguntas.filter((pergunta) => !respondida(pergunta)).length;
        falta.textContent = faltando === 1
            ? `Falta responder a pergunta ${pendente + 1}.`
            : `Faltam ${faltando} perguntas. Começando pela pergunta ${pendente + 1}.`;
        falta.hidden = false;
        mostrar(pendente, true);
    });

    const pedida = perguntas.findIndex((pergunta) => `#${pergunta.id}` === location.hash);
    const primeiraAberta = perguntas.findIndex((pergunta) => !respondida(pergunta));
    formulario.classList.add("qz-uma-por-vez");
    mostrar(pedida >= 0 ? pedida : Math.max(primeiraAberta, 0));
})();
