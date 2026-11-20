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
            status.textContent = '';
            status.hidden = true;
        } catch {
            status.textContent = 'Não foi possível carregar agora. Use o link da atividade ou tente novamente.';
            repetir.hidden = false;
        } finally {
            clearTimeout(tempo);
            carregando = false;
            widget.setAttribute('aria-busy', 'false');
        }
    }
    repetir.addEventListener('click', carregar);
    if (widget.tagName === 'DETAILS') {
        widget.addEventListener('toggle', () => { if (widget.open) carregar(); });
    } else if ('IntersectionObserver' in window) {
        // Só consulta quando o bloco chega perto da tela.
        const observador = new IntersectionObserver(entradas => {
            if (entradas.some(entrada => entrada.isIntersecting)) {
                observador.disconnect();
                carregar();
            }
        }, { rootMargin: '300px 0px' });
        observador.observe(widget);
    } else {
        carregar();
    }
}
for (const campo of document.querySelectorAll('[data-nota]')) {
    const saida = campo.querySelector('[data-nota-saida]');
    campo.addEventListener('change', evento => {
        const rotulo = evento.target.closest('label');
        if (rotulo && saida) saida.textContent = rotulo.title;
    });
}
for (const contador of document.querySelectorAll('[data-contador]')) {
    const area = contador.closest('.av-campo')?.querySelector('textarea');
    if (!area) continue;
    area.addEventListener('input', () => { contador.textContent = `${area.value.length} de ${area.maxLength}`; });
}
// Confirmação no próprio lugar do botão: as ações dão lugar a uma linha com a pergunta.
for (const formulario of document.querySelectorAll('form[data-confirmar]')) {
    formulario.addEventListener('submit', evento => {
        evento.preventDefault();
        const acoes = formulario.closest('[data-confirmar-local]') || formulario.parentElement;
        if (acoes.nextElementSibling?.classList.contains('confirmar-linha')) return;
        const linha = document.createElement('div');
        linha.className = 'confirmar-linha';
        linha.setAttribute('role', 'alert');
        const texto = document.createElement('p');
        texto.textContent = formulario.dataset.confirmar;
        const cancelar = document.createElement('button');
        cancelar.type = 'button';
        cancelar.className = 'confirmar-cancelar';
        cancelar.textContent = 'Cancelar';
        const confirmar = document.createElement('button');
        confirmar.type = 'button';
        confirmar.className = 'confirmar-ok';
        confirmar.textContent = formulario.dataset.confirmarAcao || 'Confirmar';
        const fechar = () => {
            linha.remove();
            acoes.hidden = false;
            formulario.querySelector('button')?.focus();
        };
        cancelar.addEventListener('click', fechar);
        linha.addEventListener('keydown', tecla => { if (tecla.key === 'Escape') fechar(); });
        confirmar.addEventListener('click', () => {
            confirmar.disabled = cancelar.disabled = true;
            formulario.submit();
        });
        linha.append(texto, cancelar, confirmar);
        acoes.hidden = true;
        acoes.after(linha);
        cancelar.focus();
    });
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
for (const previa of document.querySelectorAll('[data-previa]')) {
    const formulario = previa.closest('.av-metades')?.querySelector('form');
    if (!formulario) continue;
    const texto = previa.querySelector('[data-previa-texto]');
    const estrelas = previa.querySelectorAll('[data-previa-estrelas] > span');
    const atualizar = () => {
        const nota = Number(formulario.querySelector('input[name="nota"]:checked')?.value || 0);
        estrelas.forEach((estrela, indice) => estrela.classList.toggle('av-estrela--on', indice < nota));
        texto.textContent = formulario.elements.comentario.value.trim() || texto.dataset.vazio;
        const campos = formulario.elements;
        const estado = !campos.publicar_nota.checked ? 'privada' : !campos.maior_de_idade.checked ? 'idade'
            : campos.publicar_comentario.checked ? 'comentario' : 'nota';
        previa.dataset.estado = estado;
        previa.querySelectorAll('[data-previa-estado]').forEach(linha => { linha.hidden = linha.dataset.previaEstado !== estado; });
    };
    formulario.addEventListener('input', atualizar);
    formulario.addEventListener('change', atualizar);
}
