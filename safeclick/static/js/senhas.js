(() => {
    const form = document.getElementById("formulario-senha");
    if (!form) return;

    const campo = document.getElementById("senha-consulta");
    const botao = document.getElementById("consultar-senha");
    const painel = document.getElementById("resultado-senha");
    const titulo = document.getElementById("titulo-resultado-senha");
    const texto = document.getElementById("texto-resultado-senha");
    const aviso = document.getElementById("aviso-javascript");

    const disponivel = Boolean(
        window.crypto?.subtle && window.TextEncoder && window.fetch
    );

    let controle = null;
    let sequencia = 0;

    function mostrar(estado, cabecalho, mensagem) {
        painel.dataset.estado = estado;
        titulo.textContent = cabecalho;
        texto.textContent = mensagem;
        painel.hidden = false;
    }

    form.addEventListener("submit", async (evento) => {
        evento.preventDefault();

        if (!disponivel || controle || !form.reportValidity()) return;

        const numero = ++sequencia;
        const consulta = new AbortController();
        controle = consulta;

        campo.disabled = botao.disabled = true;
        form.setAttribute("aria-busy", "true");
        mostrar("aguardando", "Consultando…", "Aguarde o resultado da verificação.");

        const prazo = setTimeout(() => consulta.abort(), 15000);

        try {
            const bytes = new TextEncoder().encode(campo.value);
            campo.value = "";

            let digest;
            try {
                digest = await crypto.subtle.digest("SHA-1", bytes);
            } finally {
                bytes.fill(0);
            }

            if (numero !== sequencia) return;

            const hash = Array.from(
                new Uint8Array(digest),
                (byte) => byte.toString(16).padStart(2, "0")
            ).join("").toUpperCase();

            const resposta = await fetch(form.action, {
                method: "POST",
                mode: "same-origin",
                credentials: "same-origin",
                cache: "no-store",
                signal: consulta.signal,
                body: new URLSearchParams({
                    prefixo: hash.slice(0, 5),
                    csrf_token: form.querySelector('[name="csrf_token"]').value,
                }),
            });

            if (numero !== sequencia) return;

            if (resposta.redirected) {
                mostrar(
                    "erro",
                    "Confirme seu acesso",
                    "Recarregue a página para verificar sua sessão e os termos de uso."
                );
                return;
            }

            if (!resposta.ok) {
                const mensagens = {
                    400: "Recarregue a página antes de fazer uma nova consulta.",
                    429: "Limite de consultas atingido. Aguarde cinco minutos.",
                    503: "O serviço está indisponível. Tente novamente mais tarde.",
                };

                mostrar(
                    "erro",
                    "Consulta não concluída",
                    mensagens[resposta.status] ||
                    "Não foi possível concluir a consulta agora."
                );
                return;
            }

            if (!resposta.headers.get("Content-Type")?.startsWith("text/plain")) {
                throw new Error();
            }

            const linhas = (await resposta.text()).trim().split(/\r?\n/);
            if (numero !== sequencia) return;

            let ocorrencias = 0;

            for (const linha of linhas) {
                const partes = /^([A-F0-9]{35}):([0-9]{1,15})$/.exec(linha);
                if (!partes) throw new Error();

                if (partes[1] === hash.slice(5)) {
                    ocorrencias = Math.max(ocorrencias, Number(partes[2]));
                }
            }

            if (ocorrencias > 0) {
                mostrar(
                    "encontrada",
                    "Senha encontrada na base",
                    `Essa combinação aparece ${ocorrencias.toLocaleString("pt-BR")} vez(es) na base. Se você a utiliza, troque-a por uma senha única em cada conta.`
                );
            } else {
                mostrar(
                    "ausente",
                    "Não encontrada nesta base",
                    "Isso não garante que a senha seja segura nem que nunca tenha vazado. Prefira senhas longas e exclusivas."
                );
            }
        } catch (erro) {
            if (numero !== sequencia) return;

            mostrar(
                "erro",
                "Consulta não concluída",
                erro.name === "AbortError"
                    ? "A consulta demorou mais que o esperado. Tente novamente mais tarde."
                    : "Não foi possível consultar a base. Confira sua conexão e tente novamente."
            );
        } finally {
            clearTimeout(prazo);

            if (numero === sequencia) {
                controle = null;
                campo.value = "";
                campo.disabled = botao.disabled = false;
                form.setAttribute("aria-busy", "false");
            }
        }
    });

    function limpar() {
        sequencia += 1;
        controle?.abort();
        controle = null;
        campo.value = "";
        titulo.textContent = texto.textContent = "";
        painel.hidden = true;
        campo.disabled = botao.disabled = !disponivel;
        form.setAttribute("aria-busy", "false");
    }

    window.addEventListener("pagehide", limpar);
    window.addEventListener("pageshow", limpar);
    limpar();

    aviso.hidden = disponivel;

    if (!disponivel) {
        aviso.textContent =
            "Use um navegador atualizado e conexão HTTPS (ou localhost durante os testes).";
    }
})();