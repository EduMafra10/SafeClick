const encaixes = [...document.querySelectorAll("[data-oficina-encaixe]")];
const cartoes = document.querySelectorAll("[data-oficina-cartao]");
const statusOficina = document.querySelector("[data-oficina-status]");

function marcarCartoes() {
    const usados = new Set(encaixes.map(encaixe => encaixe.selectedOptions[0].dataset.cartao));
    for (const cartao of cartoes) {
        cartao.lastElementChild.hidden = !usados.has(cartao.dataset.oficinaCartao);
    }
}

for (const encaixe of encaixes) {
    encaixe.addEventListener("change", () => {
        const cartao = encaixe.selectedOptions[0].dataset.cartao;
        statusOficina.textContent = "";
        if (cartao) {
            const anterior = encaixes.find(outro =>
                outro !== encaixe && outro.selectedOptions[0].dataset.cartao === cartao,
            );
            if (anterior) {
                anterior.value = "";
                statusOficina.textContent = "Cartão movido. Preencha o trecho que ficou vazio.";
            }
        }
        marcarCartoes();
    });
}
marcarCartoes();
