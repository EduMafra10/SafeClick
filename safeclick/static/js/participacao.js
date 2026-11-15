"use strict";
for (const widget of document.querySelectorAll('[data-avaliacoes-url]')) {
    let carregado = false;
    let carregando = false;
    const status = widget.querySelector('[data-avaliacoes-status]');
    const repetir = widget.querySelector('[data-avaliacoes-repetir]');
    async function carregar() {
        if (carregado || carregando) return;
        carregando = true;
        repetir.hidden = true;
        status.hidden = false;
        status.textContent = 'Carregando avaliações…';
        widget.setAttribute('aria-busy', 'true');
        const controle = new AbortController();
        const tempo = setTimeout(() => controle.abort(), 12000);
        try {
            const resposta = await fetch(widget.dataset.avaliacoesUrl, { signal: controle.signal, credentials: 'same-origin' });
            if (!resposta.ok || resposta.redirected || !resposta.headers.get('Content-Type')?.includes('text/html')) throw new Error();
            const pagina = new DOMParser().parseFromString(await resposta.text(), 'text/html');
            const resumo = pagina.querySelector('.participacao-resumo');
            if (!resumo) throw new Error();
            widget.querySelector('[data-avaliacoes-dados]').replaceChildren(resumo);
            carregado = true;
            status.textContent = 'Avaliações carregadas.';
        } catch {
            status.textContent = 'Não foi possível carregar agora. Use o link da atividade ou tente novamente.';
            repetir.hidden = false;
        } finally {
            clearTimeout(tempo);
            carregando = false;
            widget.setAttribute('aria-busy', 'false');
        }
    }
    widget.addEventListener('toggle', () => { if (widget.open) carregar(); });
    repetir.addEventListener('click', carregar);
}
for (const formulario of document.querySelectorAll('form[data-confirmar]')) {
    formulario.addEventListener('submit', evento => { if (!window.confirm(formulario.dataset.confirmar)) evento.preventDefault(); });
}
for (const formulario of document.querySelectorAll('form[data-espera]')) {
    formulario.addEventListener('submit', () => {
        if (formulario.checkValidity()) {
            formulario.setAttribute('aria-busy', 'true');
            const aviso = document.querySelector('[data-carregando]');
            if (aviso) aviso.hidden = false;
        }
    });
}
window.addEventListener('pageshow', () => {
    for (const formulario of document.querySelectorAll('[aria-busy]')) formulario.setAttribute('aria-busy','false');
    for (const aviso of document.querySelectorAll('[data-carregando]')) aviso.hidden = true;
});
const filtroHistorico = document.querySelector('[data-historico-filtro]');
if (filtroHistorico) {
    const busca = document.querySelector('[data-historico-busca]');
    const linhas = [...document.querySelectorAll('[data-historico-tipo]')];
    function filtrar() {
        const texto = busca.value.trim().toLocaleLowerCase('pt-BR');
        for (const linha of linhas) linha.hidden = Boolean((filtroHistorico.value && linha.dataset.historicoTipo !== filtroHistorico.value) || !linha.textContent.toLocaleLowerCase('pt-BR').includes(texto));
        document.querySelector('[data-historico-status]').textContent = `${linhas.filter(linha => !linha.hidden).length} atividades exibidas.`;
    }
    filtroHistorico.addEventListener('change', filtrar);
    busca.addEventListener('input', filtrar);
}
