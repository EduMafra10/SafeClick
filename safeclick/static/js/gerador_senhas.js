// Gerador de senhas do Laboratório.
// Tudo acontece no navegador: nenhuma senha gerada é enviada ao servidor.

(() => {
    const painel = document.getElementById("painel-gerador");
    const palavras = window.SafeClickPalavras;
    if (!painel || !palavras || !window.crypto?.getRandomValues) return;

    const tipos = [...painel.querySelectorAll('input[name="tipo-senha"]')];
    const quantidadePalavras = document.getElementById("quantidade-palavras");
    const quantidadeCaracteres = document.getElementById("quantidade-caracteres");
    const valorPalavras = document.getElementById("valor-palavras");
    const valorCaracteres = document.getElementById("valor-caracteres");
    const ajustePalavras = document.getElementById("ajuste-palavras");
    const ajusteCaracteres = document.getElementById("ajuste-caracteres");
    const saida = document.getElementById("senha-gerada");
    const gerar = document.getElementById("gerar-senha");
    const copiar = document.getElementById("copiar-senha");
    const forca = document.getElementById("forca-gerada");
    const rotuloForca = document.getElementById("rotulo-gerada");
    const entropia = document.getElementById("entropia-senha");
    const avisoCopia = document.getElementById("aviso-copia");
    const dica = document.getElementById("dica-caracteres");

    
    const GRUPOS = {
        maiusculas: { caixa: document.getElementById("incluir-maiusculas"), caracteres: "ABCDEFGHJKLMNPQRSTUVWXYZ" }, // sem I e O
        minusculas: { caixa: document.getElementById("incluir-minusculas"), caracteres: "abcdefghijkmnopqrstuvwxyz" }, // sem l
        numeros: { caixa: document.getElementById("incluir-numeros"), caracteres: "23456789" },                       // sem 0 e 1
        simbolos: { caixa: document.getElementById("incluir-simbolos"), caracteres: "!@#$%&*?-_=+" },
    };
    const caixas = Object.values(GRUPOS).map((grupo) => grupo.caixa);

    const NIVEIS = ["Muito fraca", "Fraca", "Moderada", "Boa", "Forte"];

    
    const TENTATIVAS_POR_SEGUNDO = 1e10;

    
    function sortear(limite) {
        const maximo = Math.floor(0x100000000 / limite) * limite;
        const valor = new Uint32Array(1);
        do {
            crypto.getRandomValues(valor);
        } while (valor[0] >= maximo);
        return valor[0] % limite;
    }

    const ligado = (nome) => GRUPOS[nome].caixa.checked;

    
    function gerarFrase(quantidade) {
        const simbolos = GRUPOS.simbolos.caracteres;
        let sorteadas = Array.from({ length: quantidade }, () => palavras[sortear(palavras.length)]);
        let bits = quantidade * Math.log2(palavras.length);

        if (ligado("maiusculas")) {
            sorteadas = sorteadas.map((palavra) => palavra[0].toUpperCase() + palavra.slice(1));
        }

        if (ligado("numeros")) {
            
            const posicao = sortear(quantidade);
            sorteadas[posicao] += String(sortear(100)).padStart(2, "0");
            bits += Math.log2(100) + Math.log2(quantidade);
        }

        let separador = "";
        if (ligado("simbolos")) {
            
            separador = simbolos[sortear(simbolos.length)];
            bits += Math.log2(simbolos.length);
        }

        return { senha: sorteadas.join(separador), bits };
    }


    function gerarAleatoria(tamanho) {
        const grupos = Object.keys(GRUPOS).filter(ligado).map((nome) => GRUPOS[nome].caracteres);
        const caracteres = grupos.join("");
        let senha;

        do {
            senha = Array.from({ length: tamanho }, () => caracteres[sortear(caracteres.length)]).join("");
        } while (!grupos.every((grupo) => [...senha].some((c) => grupo.includes(c))));

        return { senha, bits: tamanho * Math.log2(caracteres.length) };
    }

    
    function nivelPorBits(bits) {
        if (bits < 30) return 0;
        if (bits < 45) return 1;
        if (bits < 60) return 2;
        if (bits < 70) return 3;
        return 4;
    }

    function tempoParaDescobrir(bits) {
        
        const segundos = 2 ** (bits - 1) / TENTATIVAS_POR_SEGUNDO;
        const unidades = [
            [60 * 60 * 24 * 365, "ano", "anos"],
            [60 * 60 * 24, "dia", "dias"],
            [60 * 60, "hora", "horas"],
            [60, "minuto", "minutos"],
        ];

        if (segundos < 1) return "menos de 1 segundo";
        if (segundos > 60 * 60 * 24 * 365 * 1e9) return "mais de 1 bilhão de anos";

        for (const [tamanho, singular, plural] of unidades) {
            if (segundos >= tamanho) {
                const quantidade = Math.round(segundos / tamanho);
                return `cerca de ${quantidade.toLocaleString("pt-BR")} ${quantidade === 1 ? singular : plural}`;
            }
        }
        return `cerca de ${Math.round(segundos)} segundos`;
    }

    function tipoAtual() {
        return tipos.find((tipo) => tipo.checked).value;
    }

    
    function ajustarCaixas(frase) {
        const minusculas = GRUPOS.minusculas.caixa;
        if (frase) {
            minusculas.dataset.antes = String(minusculas.checked);
            minusculas.checked = true;
            minusculas.disabled = true;
            dica.textContent = "Na frase-senha, as letras minúsculas vêm das próprias palavras.";
        } else {
            if (minusculas.dataset.antes) minusculas.checked = minusculas.dataset.antes === "true";
            delete minusculas.dataset.antes;
            
            if (!caixas.some((caixa) => caixa.checked)) minusculas.checked = true;
            minusculas.disabled = false;
            dica.textContent = "";
        }
    }

    function atualizar() {
        const frase = tipoAtual() === "frase";
        ajustePalavras.hidden = !frase;
        ajusteCaracteres.hidden = frase;
        valorPalavras.textContent = quantidadePalavras.value;
        valorCaracteres.textContent = quantidadeCaracteres.value;

        const { senha, bits } = frase
            ? gerarFrase(Number(quantidadePalavras.value))
            : gerarAleatoria(Number(quantidadeCaracteres.value));

        saida.textContent = senha;
        avisoCopia.textContent = "";

        const nivel = nivelPorBits(bits);
        forca.dataset.nivel = String(nivel);
        rotuloForca.textContent = NIVEIS[nivel];

        entropia.textContent =
            `Cerca de ${Math.round(bits)} bits de aleatoriedade. ` +
            `Um computador testando 10 bilhões de combinações por segundo levaria ` +
            `${tempoParaDescobrir(bits)} para descobrir esta senha.`;
    }

    function trocarTipo() {
        ajustarCaixas(tipoAtual() === "frase");
        atualizar();
    }

    
    function trocarCaixa(evento) {
        if (!caixas.some((caixa) => caixa.checked)) {
            evento.target.checked = true;
            dica.textContent = "Mantenha pelo menos um tipo de caractere marcado.";
            return;
        }
        atualizar();
    }

    async function copiarSenha() {
        try {
            await navigator.clipboard.writeText(saida.textContent);
            avisoCopia.textContent = "Senha copiada. Guarde em um gerenciador de senhas.";
        } catch {
            
            const selecao = window.getSelection();
            const intervalo = document.createRange();
            intervalo.selectNodeContents(saida);
            selecao.removeAllRanges();
            selecao.addRange(intervalo);
            avisoCopia.textContent = "Não foi possível copiar automaticamente. A senha está selecionada: use Ctrl+C.";
        }
    }

    tipos.forEach((tipo) => tipo.addEventListener("change", trocarTipo));
    caixas.forEach((caixa) => caixa.addEventListener("change", trocarCaixa));
    quantidadePalavras.addEventListener("input", atualizar);
    quantidadeCaracteres.addEventListener("input", atualizar);
    gerar.addEventListener("click", atualizar);
    copiar.addEventListener("click", copiarSenha);

    
    window.addEventListener("pagehide", () => {
        saida.textContent = "—";
    });
    window.addEventListener("pageshow", (evento) => {
        if (evento.persisted) atualizar();
    });

    [...tipos, ...caixas, quantidadePalavras, quantidadeCaracteres, gerar, copiar]
        .forEach((controle) => { controle.disabled = false; });
    trocarTipo();
})();