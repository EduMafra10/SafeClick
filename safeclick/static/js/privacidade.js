(() => {
    const sumario = document.querySelector('.privacidade-documento .privacidade-sumario');
    const lateral = document.querySelector('[data-privacidade-lateral]');
    if (sumario && lateral) lateral.append(sumario);
    const links = [...document.querySelectorAll('.privacidade-sumario a[href^="#"]')];
    const pares = links
        .map(link => [link, document.getElementById(decodeURIComponent(link.hash.slice(1)))])
        .filter(([, alvo]) => alvo);
    if (!pares.length) return;
    let pendente = false;
    const atualizar = () => {
        pendente = false;
        const linha = window.innerHeight * 0.3;
        let atual = null;
        for (const [link, alvo] of pares) {
            if (alvo.getBoundingClientRect().top <= linha) atual = link;
        }
        for (const [link] of pares) {
            if (link === atual) link.setAttribute('aria-current', 'true');
            else link.removeAttribute('aria-current');
        }
    };
    window.addEventListener('scroll', () => {
        if (!pendente) {
            pendente = true;
            requestAnimationFrame(atualizar);
        }
    }, { passive: true });
    atualizar();
})();
