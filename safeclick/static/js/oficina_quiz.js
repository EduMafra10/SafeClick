(() => {
    const mesa = document.querySelector("[data-oficina]");
    if (!mesa) return;

    const formulario = mesa.closest("form");
    const encaixes = [...mesa.querySelectorAll("[data-oficina-encaixe]")];
    const espacos = [...mesa.querySelectorAll("[data-oficina-espaco]")];
    const cartoes = [...mesa.querySelectorAll("[data-oficina-cartao]")].map((item) => item.dataset.oficinaCartao);
    const mao = mesa.querySelector("[data-oficina-mao]");
    const livres = mesa.querySelector("[data-oficina-livres]");
    const contagem = mesa.querySelector("[data-oficina-contagem]");
    const status = mesa.querySelector("[data-oficina-status]");
    let escolhida = null;

    const cartaoDe = (encaixe) => encaixe.selectedOptions[0]?.dataset.cartao || "";
    const trechoCom = (cartao) => encaixes.findIndex((encaixe) => cartaoDe(encaixe) === cartao);

    function encaixar(indice, cartao) {
        const encaixe = encaixes[indice];
        const opcao = [...encaixe.options].find((item) => item.dataset.cartao === cartao);
        const anterior = cartao ? trechoCom(cartao) : -1;
        if (anterior !== -1 && anterior !== indice) {
            encaixes[anterior].value = "";
            status.textContent = `Carta movida do trecho ${anterior + 1} para o trecho ${indice + 1}.`;
        } else {
            status.textContent = cartao ? `Carta colocada no trecho ${indice + 1}.` : `Carta devolvida para a mão.`;
        }
        encaixe.value = opcao ? opcao.value : "";
    }

    function cartaVisual(texto, rotulo) {
        const carta = document.createElement("span");
        carta.className = "qz-carta";
        const topo = document.createElement("small");
        topo.textContent = rotulo;
        const corpo = document.createElement("span");
        corpo.textContent = texto;
        carta.append(topo, corpo);
        return carta;
    }

    function desenhar() {
        const usados = encaixes.filter(cartaoDe).length;
        contagem.textContent = `${usados} de ${encaixes.length} trechos`;
        livres.textContent = `· ${cartoes.filter((cartao) => trechoCom(cartao) === -1).length} cartas livres`;

        espacos.forEach((espaco, indice) => {
            const cartao = cartaoDe(encaixes[indice]);
            const rotulo = document.getElementById(`rotulo-${encaixes[indice].id}`).querySelector("small").textContent;
            espaco.replaceChildren();
            espaco.classList.toggle("qz-espaco--cheio", Boolean(cartao));
            espaco.classList.toggle("qz-espaco--alvo", Boolean(escolhida) && !cartao);
            if (cartao) {
                espaco.append(cartaVisual(cartao, "Toque para devolver"));
                espaco.setAttribute("aria-label", `${rotulo}: ${cartao}. Toque para devolver a carta.`);
            } else {
                espaco.textContent = escolhida ? "Toque para colocar a carta" : "Vazio";
                espaco.setAttribute("aria-label", `${rotulo}: vazio.${escolhida ? ` Colocar ${escolhida}.` : ""}`);
            }
        });

        mao.querySelectorAll("button").forEach((botao, indice) => {
            const cartao = cartoes[indice];
            const trecho = trechoCom(cartao);
            botao.setAttribute("aria-pressed", String(cartao === escolhida));
            botao.classList.toggle("qz-carta-mao--usada", trecho !== -1);
            botao.querySelector("small").textContent = trecho === -1 ? `Carta ${indice + 1}` : `No trecho ${trecho + 1}`;
        });
    }

    cartoes.forEach((cartao, indice) => {
        const item = document.createElement("li");
        const botao = document.createElement("button");
        botao.type = "button";
        botao.className = "qz-carta qz-carta-mao";
        botao.style.setProperty("--giro", `${indice % 2 ? 1.5 : -1.5}deg`);
        botao.append(...cartaVisual(cartao, `Carta ${indice + 1}`).childNodes);
        botao.addEventListener("click", () => {
            escolhida = escolhida === cartao ? null : cartao;
            status.textContent = escolhida ? "Agora toque no trecho que essa carta completa." : "";
            desenhar();
        });
        item.append(botao);
        mao.append(item);
    });

    espacos.forEach((espaco, indice) => {
        espaco.addEventListener("click", () => {
            if (escolhida) {
                encaixar(indice, escolhida);
                escolhida = null;
            } else if (cartaoDe(encaixes[indice])) {
                encaixar(indice, "");
            } else {
                status.textContent = "Escolha primeiro uma carta da sua mão.";
                mao.querySelector("button")?.focus();
            }
            desenhar();
        });
    });

    formulario.noValidate = true;
    formulario.addEventListener("submit", (evento) => {
        const vazio = encaixes.findIndex((encaixe) => !encaixe.value);
        if (vazio === -1) return;
        evento.preventDefault();
        const faltando = encaixes.filter((encaixe) => !encaixe.value).length;
        status.textContent = faltando === 1 ? `Falta encaixar o trecho ${vazio + 1}.` : `Faltam ${faltando} trechos. Comece pelo trecho ${vazio + 1}.`;
        espacos[vazio].focus();
    });

    encaixes.forEach((encaixe) => { encaixe.hidden = true; });
    espacos.forEach((espaco) => { espaco.hidden = false; });
    mesa.querySelector("[data-oficina-banco]").hidden = true;
    mesa.querySelector("[data-oficina-mao-area]").hidden = false;
    mesa.classList.add("qz-mesa--ativa");
    desenhar();
})();
