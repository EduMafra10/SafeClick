"use strict";

const avisoAvaliacoes = document.querySelector("[data-avaliacoes-pendentes-url]");

if (avisoAvaliacoes) {
    let consultando = false;
    const botaoModeracao = document.querySelector("[data-avaliacoes-moderacao]");
    const sinalModeracao = document.querySelector("[data-avaliacoes-sinal]");

    async function atualizarPendencias() {
        if (document.hidden || consultando) return;
        consultando = true;
        const controle = new AbortController();
        const tempo = setTimeout(() => controle.abort(), 10000);

        try {
            const resposta = await fetch(avisoAvaliacoes.dataset.avaliacoesPendentesUrl, {
                credentials: "same-origin",
                cache: "no-store",
                signal: controle.signal,
            });
            if (!resposta.ok || resposta.redirected) throw new Error();
            const dados = await resposta.json();
            if (!Number.isSafeInteger(dados.total) || dados.total < 0) throw new Error();

            avisoAvaliacoes.hidden = dados.total === 0;
            const mensagem = dados.total === 1
                ? "Um comentário aguarda revisão para publicação."
                : `${dados.total} comentários aguardam revisão para publicação.`;
            avisoAvaliacoes.title = mensagem;
            avisoAvaliacoes.setAttribute("aria-label", mensagem);
            if (botaoModeracao) {
                botaoModeracao.classList.toggle("tem-pendencias", dados.total > 0);
                botaoModeracao.title = dados.total ? mensagem : "Nenhum comentário aguarda aprovação.";
                botaoModeracao.setAttribute("aria-label", dados.total
                    ? `Comentários e moderação. ${mensagem}` : "Comentários e moderação");
                sinalModeracao.hidden = dados.total === 0;
            }
        } catch {
            avisoAvaliacoes.title = "Não foi possível atualizar o aviso. Abra a lista para conferir as pendências.";
        } finally {
            clearTimeout(tempo);
            consultando = false;
        }
    }

    atualizarPendencias();
    setInterval(atualizarPendencias, 30000);
    window.addEventListener("pageshow", atualizarPendencias);
    document.addEventListener("visibilitychange", atualizarPendencias);
}
