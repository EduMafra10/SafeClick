document.addEventListener("DOMContentLoaded", () => {
    const caixa = document.querySelector(".conquista-avisos");
    if (!caixa) {
        return;
    }

    const avisos = Array.from(caixa.querySelectorAll(".conquista-aviso"));
    const TEMPO_NA_TELA = 6000;
    let atual = -1;
    let temporizador = null;

    caixa.classList.add("conquista-avisos--fila");

    function mostrarProximo() {
        clearTimeout(temporizador);

        if (atual >= 0) {
            avisos[atual].classList.remove("conquista-aviso--visivel");
        }

        atual += 1;

        if (atual >= avisos.length) {
            // espera a animação de saída antes de remover os avisos da página
            setTimeout(() => caixa.remove(), 400);
            return;
        }

        avisos[atual].classList.add("conquista-aviso--visivel");
        temporizador = setTimeout(mostrarProximo, TEMPO_NA_TELA);
    }

    caixa.addEventListener("click", (evento) => {
        if (evento.target.closest(".conquista-aviso-fechar")) {
            mostrarProximo();
        }
    });

    caixa.addEventListener("mouseenter", () => clearTimeout(temporizador));
    caixa.addEventListener("focusin", () => clearTimeout(temporizador));
    caixa.addEventListener("mouseleave", () => {
        temporizador = setTimeout(mostrarProximo, TEMPO_NA_TELA / 2);
    });

    setTimeout(mostrarProximo, 500);
});