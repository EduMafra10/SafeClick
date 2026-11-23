(() => {
    const MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho",
        "agosto", "setembro", "outubro", "novembro", "dezembro"];
    const TITULOS = MESES.map((nome) => nome[0].toUpperCase() + nome.slice(1));
    const DIAS = [["D", "Domingo"], ["S", "Segunda"], ["T", "Terça"], ["Q", "Quarta"],
        ["Q", "Quinta"], ["S", "Sexta"], ["S", "Sábado"]];
    const ICONE = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/></svg>';
    const SETA = (d) => `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="${d}"/></svg>`;

    const iso = (data) => [data.getFullYear(), String(data.getMonth() + 1).padStart(2, "0"),
        String(data.getDate()).padStart(2, "0")].join("-");
    const deIso = (texto) => {
        const partes = /^(\d{4})-(\d{2})-(\d{2})$/.exec(texto || "");
        if (!partes) return null;
        const data = new Date(+partes[1], partes[2] - 1, +partes[3]);
        return iso(data) === texto ? data : null;
    };
    const brasileiro = (texto) => (texto ? texto.split("-").reverse().join("/") : "");
    const mascarar = (texto) => {
        const numeros = texto.replace(/\D/g, "").slice(0, 8);
        return [numeros.slice(0, 2), numeros.slice(2, 4), numeros.slice(4)].filter(Boolean).join("/");
    };

    let aberto = null;

    function montar(original) {
        const minimo = original.min || "";
        const maximo = original.max || "";
        const apos = original.dataset.calendarioApos;
        const antes = original.dataset.calendarioAntes;
        const formulario = original.form;
        const oculto = document.createElement("input");
        oculto.type = "hidden";
        oculto.name = original.name;
        oculto.value = deIso(original.value) ? original.value : "";

        const campo = original;
        campo.removeAttribute("name");
        campo.type = "text";
        campo.inputMode = "numeric";
        campo.autocomplete = "off";
        campo.placeholder = "dd/mm/aaaa";
        campo.maxLength = 10;
        campo.value = brasileiro(oculto.value);

        const caixa = document.createElement("span");
        caixa.className = "calendario";
        campo.replaceWith(caixa);

        const botao = document.createElement("button");
        botao.type = "button";
        botao.className = "calendario-abrir";
        botao.setAttribute("aria-haspopup", "dialog");
        botao.setAttribute("aria-expanded", "false");
        botao.setAttribute("aria-label", "Abrir calendário");
        botao.innerHTML = ICONE;

        const painel = document.createElement("div");
        painel.className = "calendario-painel";
        painel.setAttribute("role", "dialog");
        painel.setAttribute("aria-label", "Escolher data");
        painel.hidden = true;
        caixa.append(campo, botao, oculto, painel);

        let mes = null;
        let foco = null;

        const vizinho = (nome) => (nome && formulario
            ? formulario.querySelector(`input[type="hidden"][name="${nome}"]`)?.value || "" : "");
        const periodo = () => ({ inicio: apos ? vizinho(apos) : oculto.value, fim: antes ? vizinho(antes) : oculto.value });
        const permitido = (texto) => (!minimo || texto >= minimo) && (!maximo || texto <= maximo)
            && (!vizinho(apos) || texto >= vizinho(apos)) && (!vizinho(antes) || texto <= vizinho(antes));

        function definir(texto) {
            oculto.value = texto;
            campo.value = brasileiro(texto);
            campo.setCustomValidity("");
            campo.dispatchEvent(new Event("change", { bubbles: true }));
        }

        function desenhar() {
            const ano = mes.getFullYear();
            const numero = mes.getMonth();
            const hoje = iso(new Date());
            const primeiro = new Date(ano, numero, 1).getDay();
            const total = new Date(ano, numero + 1, 0).getDate();
            const anterior = iso(new Date(ano, numero, 0));
            const seguinte = iso(new Date(ano, numero + 1, 1));
            const { inicio, fim } = periodo();

            let celulas = "";
            for (let i = 0; i < primeiro; i += 1) celulas += "<span></span>";
            for (let dia = 1; dia <= total; dia += 1) {
                const texto = iso(new Date(ano, numero, dia));
                const classes = ["calendario-dia"];
                if (texto === hoje) classes.push("calendario-dia--hoje");
                if (inicio && fim && texto >= inicio && texto <= fim) classes.push("calendario-dia--periodo");
                if (texto === inicio) classes.push("calendario-dia--inicio");
                if (texto === fim) classes.push("calendario-dia--fim");
                celulas += `<button type="button" class="${classes.join(" ")}" data-data="${texto}"`
                    + ` tabindex="${texto === foco ? 0 : -1}"`
                    + `${texto === oculto.value ? ' aria-pressed="true"' : ' aria-pressed="false"'}`
                    + `${permitido(texto) ? "" : " disabled"}`
                    + ` aria-label="${dia} de ${MESES[numero]} de ${ano}${texto === hoje ? ", hoje" : ""}">${dia}</button>`;
            }

            painel.innerHTML = `
                <div class="calendario-topo">
                    <button type="button" class="calendario-mes" data-mes="-1" aria-label="Mês anterior"
                        ${minimo && anterior < minimo ? "disabled" : ""}>${SETA("M15 6l-6 6 6 6")}</button>
                    <strong aria-live="polite">${TITULOS[numero]} de ${ano}</strong>
                    <button type="button" class="calendario-mes" data-mes="1" aria-label="Próximo mês"
                        ${maximo && seguinte > maximo ? "disabled" : ""}>${SETA("M9 6l6 6-6 6")}</button>
                </div>
                <div class="calendario-semana" aria-hidden="true">
                    ${DIAS.map(([letra, nome]) => `<abbr title="${nome}">${letra}</abbr>`).join("")}
                </div>
                <div class="calendario-grade">${celulas}</div>
                <div class="calendario-rodape">
                    <button type="button" data-acao="limpar">Limpar</button>
                    <button type="button" data-acao="hoje" ${permitido(hoje) ? "" : "disabled"}>Hoje</button>
                </div>`;
        }

        function focar() {
            painel.querySelector(`[data-data="${foco}"]`)?.focus();
        }

        function irPara(data) {
            let texto = iso(data);
            if (minimo && texto < minimo) texto = minimo;
            if (maximo && texto > maximo) texto = maximo;
            foco = texto;
            const alvo = deIso(texto);
            mes = new Date(alvo.getFullYear(), alvo.getMonth(), 1);
            desenhar();
            focar();
        }

        function abrir() {
            if (aberto && aberto !== fechar) aberto(false);
            const inicial = deIso(oculto.value) || deIso(maximo && iso(new Date()) > maximo ? maximo : iso(new Date()));
            painel.hidden = false;
            botao.setAttribute("aria-expanded", "true");
            const largura = 296;
            painel.classList.toggle("calendario-painel--direita",
                caixa.getBoundingClientRect().left + largura > document.documentElement.clientWidth - 16);
            aberto = fechar;
            irPara(inicial);
        }

        function fechar(devolverFoco = true) {
            if (painel.hidden) return;
            painel.hidden = true;
            botao.setAttribute("aria-expanded", "false");
            if (aberto === fechar) aberto = null;
            if (devolverFoco) botao.focus();
        }

        botao.addEventListener("click", () => (painel.hidden ? abrir() : fechar()));

        painel.addEventListener("click", (evento) => {
            const alvo = evento.target.closest("button");
            if (!alvo || alvo.disabled) return;
            if (alvo.dataset.data) {
                definir(alvo.dataset.data);
                fechar();
            } else if (alvo.dataset.mes) {
                const data = deIso(foco);
                const dia = Math.min(data.getDate(), new Date(data.getFullYear(), data.getMonth() + 2, 0).getDate());
                mes = new Date(mes.getFullYear(), mes.getMonth() + Number(alvo.dataset.mes), 1);
                foco = iso(new Date(mes.getFullYear(), mes.getMonth(),
                    Math.min(dia, new Date(mes.getFullYear(), mes.getMonth() + 1, 0).getDate())));
                desenhar();
                painel.querySelector(`[data-mes="${alvo.dataset.mes}"]`)?.focus();
            } else if (alvo.dataset.acao === "hoje") {
                definir(iso(new Date()));
                fechar();
            } else if (alvo.dataset.acao === "limpar") {
                definir("");
                fechar();
            }
        });

        painel.addEventListener("keydown", (evento) => {
            if (evento.key === "Escape") {
                evento.preventDefault();
                fechar();
                return;
            }
            if (!evento.target.dataset.data) return;
            const data = deIso(foco);
            const passos = { ArrowLeft: -1, ArrowRight: 1, ArrowUp: -7, ArrowDown: 7 };
            if (evento.key in passos) {
                data.setDate(data.getDate() + passos[evento.key]);
            } else if (evento.key === "PageUp" || evento.key === "PageDown") {
                data.setMonth(data.getMonth() + (evento.key === "PageUp" ? -1 : 1));
            } else if (evento.key === "Home") {
                data.setDate(data.getDate() - data.getDay());
            } else if (evento.key === "End") {
                data.setDate(data.getDate() + 6 - data.getDay());
            } else {
                return;
            }
            evento.preventDefault();
            irPara(data);
        });

        campo.addEventListener("input", () => {
            campo.value = mascarar(campo.value);
            const partes = campo.value.split("/");
            const texto = partes.length === 3 && partes[2].length === 4 ? `${partes[2]}-${partes[1]}-${partes[0]}` : "";
            if (!campo.value) {
                oculto.value = "";
                campo.setCustomValidity("");
            } else if (deIso(texto) && permitido(texto)) {
                oculto.value = texto;
                campo.setCustomValidity("");
            } else {
                oculto.value = "";
                campo.setCustomValidity(deIso(texto) && apos && texto < vizinho(apos)
                    ? "A data final precisa ser igual ou posterior à inicial."
                    : "Digite uma data válida no formato dd/mm/aaaa, até hoje.");
            }
        });

        caixa.addEventListener("focusout", () => {
            setTimeout(() => {
                if (!painel.hidden && !caixa.contains(document.activeElement)) fechar(false);
            });
        });
    }

    document.addEventListener("pointerdown", (evento) => {
        if (aberto && !evento.target.closest(".calendario")) aberto(false);
    });

    document.querySelectorAll('input[type="date"][data-calendario]').forEach(montar);
})();
