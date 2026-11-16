// Retorno da política de senha enquanto a pessoa digita. Espelha safeclick/politica_senha.py.
(() => {
    const MINIMO = 15;
    const MAXIMO = 128;
    const OBVIAS = ["senha", "password", "safeclick", "qwerty", "admin", "brasil", "teste", "abc", "123"];
    const SEQUENCIAS = ["abcdefghijklmnopqrstuvwxyz", "0123456789", "qwertyuiop", "asdfghjkl", "zxcvbnm"];
    const NIVEIS = ["Muito fraca", "Fraca", "Moderada", "Boa", "Forte"];
    const WORKER = new URL("forca_senha_worker.js", document.currentScript.src).href;

    const normalizar = (texto) => (texto || "").normalize("NFKD").toLowerCase().replace(/[^a-z0-9]/g, "");
    const vizinhas = (a, b) => SEQUENCIAS.some((s) => s.includes(a + b) || s.includes(b + a));

    function trivial(senha) {
        if (new Set([...senha.toLowerCase()]).size < 5) return true;
        let nucleo = normalizar(senha);
        for (const palavra of OBVIAS) nucleo = nucleo.split(palavra).join("");
        if (new Set(nucleo).size < 4) return true;
        let seguidos = 0;
        for (let i = 0; i < nucleo.length - 1; i += 1) if (vizinhas(nucleo[i], nucleo[i + 1])) seguidos += 1;
        return seguidos / (nucleo.length - 1) >= 0.7;
    }

    function pessoal(senha, nome, email) {
        const alvo = normalizar(senha);
        const partes = (nome || "").split(/\s+/).map(normalizar);
        partes.push(normalizar((email || "").split("@")[0]));
        return partes.some((parte) => parte.length >= 4 && alvo.includes(parte));
    }

    function item(regra, texto) {
        const li = document.createElement("li");
        li.dataset.regra = regra;
        li.textContent = texto;
        return li;
    }

    function preparar(formulario) {
        const [campo, confirmacao] = formulario.querySelectorAll('input[autocomplete="new-password"]');
        if (!campo) return;
        const campoNome = formulario.querySelector('input[name="nome"]');
        const campoEmail = formulario.querySelector('input[name="email"]');
        const temPessoais = Boolean(campoNome || campoEmail || formulario.dataset.nome || formulario.dataset.email);

        const painel = document.createElement("div");
        painel.className = "politica-senha";
        painel.id = `${campo.id}-politica`;
        painel.innerHTML = '<div class="politica-senha-forca" hidden><span class="politica-senha-barra" aria-hidden="true">'
            + "<i></i><i></i><i></i><i></i></span><span class=\"politica-senha-rotulo\"></span></div>";
        const lista = document.createElement("ul");
        const tamanho = item("tamanho", "Entre 15 e 128 caracteres");
        const contador = document.createElement("span");
        contador.className = "politica-senha-contador";
        tamanho.append(" ", contador);
        lista.append(tamanho, item("trivial", "Sem repetições, sequências ou palavras óbvias"));
        if (temPessoais) lista.append(item("pessoal", "Sem o seu nome ou e-mail"));
        if (confirmacao) lista.append(item("confirmacao", "As duas senhas são iguais"));
        painel.append(lista);

        const ancora = campo.closest(".autenticacao-campo, .conta-campo") || campo;
        ancora.after(painel);
        campo.setAttribute("aria-describedby", `${campo.getAttribute("aria-describedby") || ""} ${painel.id}`.trim());

        const forca = painel.querySelector(".politica-senha-forca");
        const rotulo = painel.querySelector(".politica-senha-rotulo");
        let worker = null;
        let pedido = 0;
        let pausa = null;

        function marcar(regra, ok) {
            const li = lista.querySelector(`[data-regra="${regra}"]`);
            if (!li) return;
            if (ok === null) delete li.dataset.ok;
            else li.dataset.ok = String(ok);
        }

        function estimar(senha) {
            if (!window.Worker) return;
            if (!worker) {
                try {
                    worker = new Worker(WORKER);
                } catch {
                    return;
                }
                worker.addEventListener("message", ({ data }) => {
                    if (data.id !== pedido || !data.avaliacao) return;
                    forca.hidden = false;
                    forca.dataset.nivel = String(data.avaliacao.nivel);
                    rotulo.textContent = `Força estimada: ${NIVEIS[data.avaliacao.nivel]}`;
                });
            }
            pedido += 1;
            worker.postMessage({ id: pedido, senha });
        }

        function atualizar() {
            const senha = campo.value;
            const quantidade = [...senha].length;
            contador.textContent = quantidade ? `(${quantidade})` : "";
            if (!senha) {
                ["tamanho", "trivial", "pessoal", "confirmacao"].forEach((r) => marcar(r, null));
                forca.hidden = true;
                pedido += 1;
                return;
            }
            marcar("tamanho", quantidade >= MINIMO && quantidade <= MAXIMO);
            marcar("trivial", quantidade >= MINIMO && !trivial(senha));
            const nome = campoNome ? campoNome.value : formulario.dataset.nome;
            const email = campoEmail ? campoEmail.value : formulario.dataset.email;
            marcar("pessoal", !pessoal(senha, nome, email));
            if (confirmacao) marcar("confirmacao", confirmacao.value ? confirmacao.value === senha : null);
            clearTimeout(pausa);
            pausa = setTimeout(() => estimar(senha), 250);
        }

        [campo, confirmacao, campoNome, campoEmail].forEach((el) => el?.addEventListener("input", atualizar));
        atualizar();
    }

    document.querySelectorAll("form").forEach(preparar);
})();
