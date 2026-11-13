// Gráfico de atividades por dia da Visão geral (Chart.js).
(() => {
    const elemento = document.getElementById("dados-visao-geral");
    const canvas = document.getElementById("grafico-atividades");
    if (!elemento || !canvas || typeof Chart === "undefined") return;

    const dados = JSON.parse(elemento.textContent);
    const cores = { conteudo: "#2f6f57", quiz: "#3f6f8f", simulacao: "#b0703a", desafio: "#9aa58a" };

    Chart.defaults.font.family = getComputedStyle(document.body).fontFamily;
    Chart.defaults.color = "#586d72";

    new Chart(canvas, {
        type: "bar",
        data: {
            labels: dados.dias,
            datasets: dados.series.map((serie) => ({
                label: serie.rotulo,
                data: serie.valores,
                backgroundColor: cores[serie.tipo],
                borderRadius: 3,
                maxBarThickness: 28,
            })),
        },
        options: {
            maintainAspectRatio: false,
            animation: false,
            plugins: { legend: { display: false } },
            interaction: { mode: "index", intersect: false },
            scales: {
                x: { stacked: true, grid: { display: false }, ticks: { maxTicksLimit: 8, maxRotation: 0 } },
                y: { stacked: true, beginAtZero: true, ticks: { precision: 0 }, grid: { color: "#e7eeec" } },
            },
        },
    });
})();
