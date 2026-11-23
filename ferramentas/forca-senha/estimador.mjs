import { ZxcvbnFactory } from "@zxcvbn-ts/core";
import * as comum from "@zxcvbn-ts/language-common";
import * as ingles from "@zxcvbn-ts/language-en";
import * as portugues from "@zxcvbn-ts/language-pt-br";

const traducoes = {
    ...portugues.translations,
    suggestions: {
        ...portugues.translations.suggestions,
        capitalization: "Só colocar a primeira letra em maiúscula não resolve um padrão previsível.",
        allUppercase: "Só trocar letras minúsculas por maiúsculas não resolve um padrão previsível.",
        longerKeyboardPattern: "Evite sequências e desenhos no teclado; escolha palavras aleatórias ou use um gerenciador.",
        anotherWord: "Aumente o comprimento com palavras escolhidas ao acaso; evite frases conhecidas.",
        useWords: "Use uma senha longa gerada por um gerenciador ou uma frase com palavras escolhidas ao acaso.",
    },
};

const estimador = new ZxcvbnFactory({
    translations: traducoes,
    graphs: comum.adjacencyGraphs,
    dictionary: {
        ...comum.dictionary,
        ...ingles.dictionary,
        ...portugues.dictionary,
        userInputs: ["safeclick"],
    },
    maxLength: 128,
});

const rotulos = ["Muito fraca", "Fraca", "Moderada", "Boa", "Forte"];
const avisosPermitidos = new Set(
    Object.entries(traducoes.warnings)
        .filter(([chave]) => chave !== "pwned")
        .map(([, mensagem]) => mensagem)
);
const sugestoesPermitidas = new Set(
    Object.entries(traducoes.suggestions)
        .filter(([chave]) => chave !== "pwned")
        .map(([, mensagem]) => mensagem)
);

export function avaliar(senha) {
    if (typeof senha !== "string" || senha.length > 128) {
        throw new TypeError("Informe um texto com até 128 caracteres.");
    }
    if (senha.length === 0) return null;

    const resultado = estimador.check(senha);
    const nivel = resultado.score;
    if (!Number.isInteger(nivel) || nivel < 0 || nivel > 4) {
        throw new Error("Não foi possível estimar a força agora.");
    }

    const aviso = avisosPermitidos.has(resultado.feedback.warning)
        ? resultado.feedback.warning
        : "";
    const orientacoes = [...new Set(resultado.feedback.suggestions)]
        .filter((mensagem) => sugestoesPermitidas.has(mensagem))
        .slice(0, 2);

    if (orientacoes.length === 0) {
        orientacoes.push(
            nivel <= 2
                ? traducoes.suggestions.useWords
                : "Use essa combinação em uma única conta. A estimativa não detecta reutilização nem todos os padrões possíveis."
        );
    }

    return { nivel, rotulo: rotulos[nivel], aviso, orientacoes };
}
