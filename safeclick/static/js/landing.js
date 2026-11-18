(() => {
    const raiz = document.documentElement;
    const CHAVE = 'safeclick-tema';

    raiz.classList.add('js');

    let tema = 'claro';
    try {
        tema = localStorage.getItem(CHAVE) || (matchMedia('(prefers-color-scheme: dark)').matches ? 'escuro' : 'claro');
    } catch (erro) {
        tema = 'claro';
    }
    raiz.setAttribute('data-tema', tema);

    document.addEventListener('DOMContentLoaded', () => {
        const botaoTema = document.querySelector('[data-alternar-tema]');

        const rotularTema = () => {
            const escuro = raiz.getAttribute('data-tema') === 'escuro';
            const rotulo = escuro ? 'Mudar para tema claro' : 'Mudar para tema escuro';
            botaoTema.setAttribute('aria-label', rotulo);
            botaoTema.setAttribute('title', rotulo);
        };

        if (botaoTema) {
            rotularTema();
            botaoTema.addEventListener('click', () => {
                const novo = raiz.getAttribute('data-tema') === 'escuro' ? 'claro' : 'escuro';
                raiz.setAttribute('data-tema', novo);
                try {
                    localStorage.setItem(CHAVE, novo);
                } catch (erro) {
                    // sem armazenamento, o tema vale só nesta visita
                }
                rotularTema();
            });
        }

        const botaoMenu = document.querySelector('[data-abrir-menu]');
        const menu = document.getElementById('menu-secoes');

        if (botaoMenu && menu) {
            const fechar = () => {
                menu.classList.remove('aberto');
                botaoMenu.setAttribute('aria-expanded', 'false');
            };

            botaoMenu.addEventListener('click', () => {
                const abrir = !menu.classList.contains('aberto');
                menu.classList.toggle('aberto', abrir);
                botaoMenu.setAttribute('aria-expanded', String(abrir));
            });

            menu.addEventListener('click', (evento) => {
                if (evento.target.closest('a')) {
                    fechar();
                }
            });

            document.addEventListener('keydown', (evento) => {
                if (evento.key === 'Escape' && menu.classList.contains('aberto')) {
                    fechar();
                    botaoMenu.focus();
                }
            });

            document.addEventListener('click', (evento) => {
                if (!menu.contains(evento.target) && !botaoMenu.contains(evento.target)) {
                    fechar();
                }
            });
        }

        const trilho = document.querySelector('[data-trilho]');
        const anterior = document.querySelector('[data-trilho-anterior]');
        const proximo = document.querySelector('[data-trilho-proximo]');

        if (trilho && anterior && proximo) {
            const reduzir = matchMedia('(prefers-reduced-motion: reduce)');

            const mover = (direcao) => {
                const painel = trilho.querySelector('.painel');
                const passo = painel ? painel.offsetWidth + 28 : trilho.clientWidth;
                trilho.scrollBy({ left: direcao * passo, behavior: reduzir.matches ? 'auto' : 'smooth' });
            };

            const atualizar = () => {
                const fim = trilho.scrollWidth - trilho.clientWidth - 4;
                anterior.disabled = trilho.scrollLeft <= 4;
                proximo.disabled = trilho.scrollLeft >= fim;
            };

            anterior.addEventListener('click', () => mover(-1));
            proximo.addEventListener('click', () => mover(1));
            trilho.addEventListener('scroll', atualizar, { passive: true });
            window.addEventListener('resize', atualizar);
            atualizar();
        }
    });
})();
