(() => {
    const campo = document.getElementById('token-recuperacao');
    const fragmento = new URLSearchParams(window.location.hash.slice(1));
    const token = fragmento.get('token');

    if (campo && token && token.length === 43 && /^[A-Za-z0-9_-]{43}$/.test(token)) {
        campo.value = token;
    }

    // retira o token da barra de enderecos depois de preencher o form
    if (window.location.hash) {
        window.history.replaceState(null, '', window.location.pathname + window.location.search);
    }

    if (campo && !campo.value) {
        campo.form.hidden = true;
        document.getElementById('recuperacao-orientacao').hidden = false;
    }
})();
