(function () {
    const datas = document.querySelector("[data-datas]");
    if (datas) {
        document.addEventListener("click", (evento) => {
            if (datas.open && !datas.contains(evento.target)) {
                datas.open = false;
            }
        });
        document.addEventListener("keydown", (evento) => {
            if (evento.key === "Escape" && datas.open) {
                datas.open = false;
                datas.querySelector("summary").focus();
            }
        });
    }

    const elementoDados = document.getElementById("dados-painel");
    if (!elementoDados || typeof Chart === "undefined") {
        return;
    }

    const dados = JSON.parse(elementoDados.textContent);
    const estilo = getComputedStyle(document.querySelector(".painel-conteudo"));
    const cor = (nome) => estilo.getPropertyValue(nome).trim();

    const verde = cor("--painel-verde");
    const laranja = cor("--painel-laranja");
    const texto = cor("--visual-texto");
    const secundario = cor("--visual-secundario");
    const borda = cor("--painel-borda");

    Chart.defaults.font.family = getComputedStyle(document.body).fontFamily;
    Chart.defaults.font.size = 12;
    Chart.defaults.color = secundario;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
        Chart.defaults.animation = false;
    }

    function quebrarTexto(texto, limite) {
        const linhas = [];
        let atual = "";
        for (const palavra of texto.split(" ")) {
            if (atual && (atual + " " + palavra).length > limite) {
                linhas.push(atual);
                atual = palavra;
            } else {
                atual = atual ? atual + " " + palavra : palavra;
            }
        }
        if (atual) {
            linhas.push(atual);
        }
        return linhas;
    }

    const legenda = {
        position: "bottom",
        align: "start",
        labels: { usePointStyle: true, pointStyle: "rectRounded", boxWidth: 9, boxHeight: 9, padding: 18 },
    };

    const dica = {
        backgroundColor: texto,
        padding: 10,
        cornerRadius: 8,
        boxPadding: 4,
    };

    const canvasEvolucao = document.getElementById("grafico-evolucao");
    if (canvasEvolucao && dados.evolucao.length) {
        const valores = dados.evolucao.map((item) => item.percentual);
        const ultimo = valores.length - 1;

        const conjuntos = [{
            label: "Acertos por tentativa",
            data: valores,
            borderColor: verde,
            backgroundColor: (contexto) => {
                const area = contexto.chart.chartArea;
                if (!area) {
                    return "transparent";
                }
                const gradiente = contexto.chart.ctx.createLinearGradient(0, area.top, 0, area.bottom);
                gradiente.addColorStop(0, verde + "38");
                gradiente.addColorStop(1, verde + "00");
                return gradiente;
            },
            fill: true,
            tension: 0.4,
            cubicInterpolationMode: "monotone",
            clip: false,
            borderWidth: 2.5,
            pointRadius: (contexto) => (contexto.dataIndex === ultimo ? 6 : 4),
            pointHoverRadius: 7,
            pointBackgroundColor: (contexto) => (contexto.dataIndex === ultimo ? texto : "#ffffff"),
            pointBorderColor: (contexto) => (contexto.dataIndex === ultimo ? texto : verde),
            pointBorderWidth: 2,
        }];

        if (dados.media !== null) {
            conjuntos.push({
                label: "Média geral (" + dados.media + "%)",
                data: valores.map(() => dados.media),
                borderColor: laranja,
                backgroundColor: laranja,
                borderDash: [5, 4],
                borderWidth: 1.5,
                pointRadius: 0,
                pointHoverRadius: 0,
                fill: false,
            });
        }

        new Chart(canvasEvolucao, {
            type: "line",
            data: { labels: dados.evolucao.map((item) => item.data), datasets: conjuntos },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: { mode: "index", intersect: false },
                scales: {
                    y: {
                        min: 0,
                        max: 100,
                        ticks: { stepSize: 25, callback: (valor) => valor + "%" },
                        grid: { color: borda },
                        border: { display: false, dash: [3, 4] },
                    },
                    x: { grid: { display: false }, border: { color: borda } },
                },
                plugins: {
                    legend: {
                        ...legenda,
                        labels: {
                            ...legenda.labels,
                            generateLabels: (grafico) => Chart.defaults.plugins.legend.labels.generateLabels(grafico)
                                .map((item) => ({ ...item, fillStyle: item.strokeStyle })),
                        },
                    },
                    tooltip: {
                        ...dica,
                        callbacks: {
                            title: (itens) => {
                                const item = dados.evolucao[itens[0].dataIndex];
                                return item.data + " · " + item.titulo;
                            },
                            label: (item) => " " + item.dataset.label.split(" (")[0] + ": " + item.parsed.y + "%",
                        },
                    },
                },
            },
        });
    }

    const valoresNasColunas = {
        id: "valoresNasColunas",
        afterDatasetsDraw(grafico) {
            const { ctx } = grafico;
            ctx.save();
            ctx.font = "700 12px " + Chart.defaults.font.family;
            ctx.fillStyle = texto;
            ctx.textAlign = "center";
            ctx.textBaseline = "bottom";
            grafico.data.datasets.forEach((conjunto, indice) => {
                const meta = grafico.getDatasetMeta(indice);
                if (meta.hidden) {
                    return;
                }
                meta.data.forEach((barra, posicao) => {
                    ctx.fillText(conjunto.data[posicao], barra.x, barra.y - 4);
                });
            });
            ctx.restore();
        },
    };

    const canvasCenarios = document.getElementById("grafico-cenarios");
    if (canvasCenarios && dados.cenarios.length) {
        const larguraColuna = canvasCenarios.parentElement.clientWidth / dados.cenarios.length;
        const limiteRotulo = Math.max(8, Math.floor(larguraColuna / 7.5));
        const coluna = { borderRadius: { topLeft: 6, topRight: 6 }, borderSkipped: "bottom", maxBarThickness: 28, categoryPercentage: 0.6, barPercentage: 0.9 };

        new Chart(canvasCenarios, {
            type: "bar",
            data: {
                labels: dados.cenarios.map((item) => quebrarTexto(item.titulo, limiteRotulo)),
                datasets: [
                    { label: "Seguras", data: dados.cenarios.map((item) => item.seguras), backgroundColor: verde, ...coluna },
                    { label: "Arriscadas", data: dados.cenarios.map((item) => item.arriscadas), backgroundColor: laranja, ...coluna },
                ],
            },
            plugins: [valoresNasColunas],
            options: {
                responsive: true,
                maintainAspectRatio: false,
                layout: { padding: { top: 18 } },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: { precision: 0 },
                        grid: { color: borda },
                        border: { display: false, dash: [3, 4] },
                    },
                    x: {
                        grid: { display: false },
                        border: { color: borda },
                        ticks: { autoSkip: false, maxRotation: 0 },
                    },
                },
                plugins: {
                    legend: legenda,
                    tooltip: {
                        ...dica,
                        callbacks: { title: (itens) => dados.cenarios[itens[0].dataIndex].titulo },
                    },
                },
            },
        });
    }
})();
