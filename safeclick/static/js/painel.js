// Desenha os gráficos do painel de progresso com o Chart.js
// Os dados chegam do servidor no bloco <script id="dados-painel"> (JSON)
(function () {
    const elementoDados = document.getElementById("dados-painel");

    // Sem atividades (estado vazio) ou sem a biblioteca: não há o que desenhar.
    if (!elementoDados || typeof Chart === "undefined") {
        return;
    }

    const dados = JSON.parse(elementoDados.textContent);

    
    const estilo = getComputedStyle(document.querySelector(".painel-conteudo"));
    const cor = (nome) => estilo.getPropertyValue(nome).trim();

    const azul = cor("--painel-azul");
    const verde = cor("--visual-verde");
    const laranja = cor("--painel-laranja");
    const secundario = cor("--visual-secundario");
    const borda = cor("--visual-borda");

    Chart.defaults.font.family = getComputedStyle(document.body).fontFamily;
    Chart.defaults.color = secundario;

  
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
        labels: { usePointStyle: true, boxWidth: 8, padding: 16 },
    };

    // ---------- Evolução nos quizzes (linha) ----------
    const canvasEvolucao = document.getElementById("grafico-evolucao");

    if (canvasEvolucao && dados.evolucao.length) {
        const valores = dados.evolucao.map((item) => item.percentual);

        const conjuntos = [
            {
                label: "Acertos",
                data: valores,
                borderColor: azul,
                backgroundColor: azul + "1a", 
                fill: true,
                tension: 0.3,
                cubicInterpolationMode: "monotone", 
                clip: false, 
                borderWidth: 3,
                pointRadius: 6,
                pointHoverRadius: 8,
                pointBackgroundColor: "#ffffff",
                pointBorderColor: azul,
                pointBorderWidth: 3,
            },
        ];

        
        if (dados.media !== null) {
            conjuntos.push({
                label: "Média geral (" + dados.media + "%)",
                data: valores.map(() => dados.media),
                borderColor: secundario,
                borderDash: [5, 5],
                borderWidth: 1.5,
                pointRadius: 0,
                pointHoverRadius: 0,
                pointStyle: "line", 
                fill: false,
            });
        }

        new Chart(canvasEvolucao, {
            type: "line",
            data: {
                labels: dados.evolucao.map((item) => item.data),
                datasets: conjuntos,
            },
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
                        border: { display: false },
                    },
                    x: { grid: { display: false } },
                },
                plugins: {
                    legend: legenda,
                    tooltip: {
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

    // ---------- Escolhas por cenário (barras empilhadas) ----------
    const canvasCenarios = document.getElementById("grafico-cenarios");

    if (canvasCenarios && dados.cenarios.length) {
        new Chart(canvasCenarios, {
            type: "bar",
            data: {
                
                labels: dados.cenarios.map((item) =>
                    quebrarTexto(item.titulo, window.innerWidth < 600 ? 14 : 22)
                ),
                datasets: [
                    {
                        label: "Seguras",
                        data: dados.cenarios.map((item) => item.seguras),
                        backgroundColor: verde,
                        borderRadius: 4,
                    },
                    {
                        label: "Arriscadas",
                        data: dados.cenarios.map((item) => item.arriscadas),
                        backgroundColor: laranja,
                        borderRadius: 4,
                    },
                ],
            },
            options: {
                indexAxis: "y", 
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        stacked: true,
                        beginAtZero: true,
                        ticks: { precision: 0 }, 
                        grid: { color: borda },
                        border: { display: false },
                    },
                    y: {
                        stacked: true,
                        grid: { display: false },
                        ticks: { autoSkip: false }, 
                    },
                },
                plugins: { legend: legenda },
            },
        });
    }
})();