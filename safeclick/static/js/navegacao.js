document.querySelectorAll('.site-conta').forEach((menu) => {
    const botao = menu.querySelector('summary');

    document.addEventListener('click', (evento) => {
        if (!menu.contains(evento.target)) {
            menu.open = false;
        }
    });

    document.addEventListener('keydown', (evento) => {
        if (evento.key === 'Escape' && menu.open) {
            menu.open = false;
            botao.focus();
        }
    });

    menu.addEventListener('focusout', (evento) => {
        if (evento.relatedTarget && !menu.contains(evento.relatedTarget)) {
            menu.open = false;
        }
    });
});