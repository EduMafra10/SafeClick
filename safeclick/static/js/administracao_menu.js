// No celular, o menu da área administrativa começa fechado.
(() => {
    const menu = document.querySelector(".admin-menu");
    const telaPequena = window.matchMedia("(max-width: 960px)");
    if (!menu) return;

    const ajustar = () => {
        menu.open = !telaPequena.matches;
    };
    ajustar();
    telaPequena.addEventListener("change", ajustar);
})();
