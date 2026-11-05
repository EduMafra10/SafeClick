import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { createContext, runInContext } from "node:vm";
import { avaliar } from "./estimador.mjs";

test("campo vazio não recebe nota", () => {
    assert.equal(avaliar(""), null);
});

test("entradas inválidas não são convertidas nem truncadas", () => {
    for (const valor of [null, undefined, 123456, {}, [], "x".repeat(129)]) {
        assert.throws(() => avaliar(valor), TypeError);
    }
});

test("senhas comuns, palavras portuguesas e padrões têm nota baixa", () => {
    for (const exemplo of ["123456", "password", "senha", "abacaxi", "qwerty", "aaaaaaaaaaaaaaaa", "abcabcabcabc", "SafeClick123!"]) {
        const resultado = avaliar(exemplo);
        assert.ok(resultado.nivel <= 2);
        assert.ok(resultado.orientacoes.length > 0);
    }
});

test("maiúsculas, símbolos e números não garantem força", () => {
    assert.ok(avaliar("Password1!").nivel <= 2);
    assert.ok(avaliar("P@ssw0rd!").nivel <= 2);
});

test("combinação longa sem padrão conhecido recebe nota maior", () => {
    const resultado = avaliar("vN7$zR2!bK9@wT5#qL8&xM4");
    assert.equal(resultado.nivel, 4);
    assert.equal(resultado.rotulo, "Forte");
    assert.match(resultado.orientacoes.join(" "), /única conta/);
});

test("espaços e acentos são entradas válidas", () => {
    for (const exemplo of [" ", " maçã ", "🐈‍⬛ lagoa açafrão vírgula", "a".repeat(128)]) {
        const resultado = avaliar(exemplo);
        assert.ok(Number.isInteger(resultado.nivel));
    }
});

test("retorno público contém apenas nota e orientação, sem senha ou hash", () => {
    const exemplo = "FICTICIO-vN7$zR2!bK9@wT5#";
    const resultado = avaliar(exemplo);
    assert.deepEqual(Object.keys(resultado).sort(), ["aviso", "nivel", "orientacoes", "rotulo"]);
    assert.equal(JSON.stringify(resultado).includes(exemplo), false);
    assert.equal(Object.hasOwn(resultado, "password"), false);
    assert.equal(Object.hasOwn(resultado, "sequence"), false);
    assert.equal(Object.hasOwn(resultado, "crackTimes"), false);
});

test("análise de padrões nunca afirma ter consultado vazamentos", () => {
    for (const exemplo of ["123456", "senha", "vN7$zR2!bK9@wT5#qL8&xM4"]) {
        assert.doesNotMatch(JSON.stringify(avaliar(exemplo)), /violação|vazamento|exposta|pwned/i);
    }
});

test("bundle executa sem APIs de rede ou armazenamento e equivale à fonte", async () => {
    const codigo = await readFile(new URL("../../safeclick/static/js/vendor/forca-senha.js", import.meta.url), "utf8");
    const contexto = createContext({});
    runInContext(codigo, contexto, { timeout: 5000 });
    assert.deepEqual(Object.keys(contexto.SafeClickForca), ["avaliar"]);
    for (const exemplo of ["", "123456", "abacaxi", "P@ssw0rd!", "vN7$zR2!bK9@wT5#qL8&xM4"]) {
        const resultado = contexto.SafeClickForca.avaliar(exemplo);
        assert.deepEqual(JSON.parse(JSON.stringify(resultado)), avaliar(exemplo));
    }
});
