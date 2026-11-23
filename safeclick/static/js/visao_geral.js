(() => {
    const painel = document.querySelector('[data-visao-geral-url]');
    if (!painel) return;
    const controles = document.querySelector('[data-visao-geral-controles]');
    const botao = document.querySelector('[data-visao-geral-atualizar]');
    const horario = document.querySelector('[data-visao-geral-horario]');
    const erro = document.querySelector('[data-visao-geral-erro]');
    let grafico;
    let consultando = false;
    let ultimoHtml;

    function desenharGrafico() {
        const elemento = painel.querySelector('#dados-visao-geral');
        const canvas = painel.querySelector('#grafico-atividades');
        if (!elemento || !canvas || typeof Chart === 'undefined') return;
        const dados = JSON.parse(elemento.textContent);
        const cores = { conteudo: '#2f6f57', quiz: '#3f6f8f', simulacao: '#b0703a', desafio: '#9aa58a' };
        Chart.defaults.font.family = getComputedStyle(document.body).fontFamily;
        Chart.defaults.color = '#586d72';
        grafico = new Chart(canvas, {
            type: 'bar',
            data: {
                labels: dados.dias,
                datasets: dados.series.map(serie => ({
                    label: serie.rotulo, data: serie.valores, backgroundColor: cores[serie.tipo],
                    borderRadius: 3, maxBarThickness: 28,
                })),
            },
            options: {
                maintainAspectRatio: false, animation: false,
                plugins: { legend: { display: false } },
                interaction: { mode: 'index', intersect: false },
                scales: {
                    x: { stacked: true, grid: { display: false }, ticks: { maxTicksLimit: 8, maxRotation: 0 } },
                    y: { stacked: true, beginAtZero: true, ticks: { precision: 0 }, grid: { color: '#e7eeec' } },
                },
            },
        });
    }

    function exibirPainel(html) {
        if (html === ultimoHtml) return;
        const pagina = new DOMParser().parseFromString(html, 'text/html');
        if (!pagina.querySelector('.admin-vg-numeros')) throw new Error('Resposta inválida');
        const focado = document.activeElement;
        const href = painel.contains(focado) ? focado.getAttribute('href') : null;
        const posicao = href ? Array.from(painel.querySelectorAll('a[href]'))
            .filter(link => link.getAttribute('href') === href).indexOf(focado) : -1;
        if (grafico) { grafico.destroy(); grafico = null; }
        painel.replaceChildren(...Array.from(pagina.body.childNodes, node => document.importNode(node, true)));
        ultimoHtml = html;
        desenharGrafico();
        if (posicao >= 0) {
            const destino = Array.from(painel.querySelectorAll('a[href]'))
                .filter(link => link.getAttribute('href') === href)[posicao];
            if (destino) destino.focus({ preventScroll: true });
        }
    }

    async function atualizar(manual = false) {
        if (document.hidden || consultando) return;
        consultando = true;
        botao.disabled = true;
        botao.textContent = 'Atualizando…';
        painel.setAttribute('aria-busy', 'true');
        const controle = new AbortController();
        const limite = setTimeout(() => controle.abort(), 10000);
        try {
            const resposta = await fetch(painel.dataset.visaoGeralUrl, {
                credentials: 'same-origin', cache: 'no-store', signal: controle.signal,
                headers: manual === true ? { 'X-SafeClick-Interacao': '1' } : {},
            });
            if (!resposta.ok || resposta.redirected) throw new Error('Consulta indisponível');
            const dados = await resposta.json();
            if (typeof dados.html !== 'string' || typeof dados.horario !== 'string'
                || typeof dados.atualizado_em !== 'string' || !Number.isFinite(Date.parse(dados.atualizado_em))) {
                throw new Error('Resposta inválida');
            }
            exibirPainel(dados.html);
            const momento = document.createElement('time');
            momento.dateTime = dados.atualizado_em;
            momento.textContent = dados.horario;
            horario.replaceChildren('Atualizado em ', momento, ' (Brasília).');
            erro.hidden = true;
        } catch {
            erro.textContent = 'Não foi possível atualizar. Os números exibidos são da última consulta bem-sucedida. Tente novamente.';
            erro.hidden = false;
        } finally {
            clearTimeout(limite);
            consultando = false;
            botao.disabled = false;
            botao.textContent = 'Atualizar agora';
            painel.removeAttribute('aria-busy');
        }
    }

    controles.hidden = false;
    desenharGrafico();
    botao.addEventListener('click', () => atualizar(true));
    setInterval(atualizar, 10000);
    document.addEventListener('visibilitychange', () => { if (!document.hidden) atualizar(); });
    window.addEventListener('pageshow', evento => { if (evento.persisted) atualizar(); });
    window.addEventListener('online', atualizar);
})();
