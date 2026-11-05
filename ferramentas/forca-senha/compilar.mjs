import { build } from "esbuild";
import { createHash } from "node:crypto";
import { readFile, writeFile, mkdir, readdir } from "node:fs/promises";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const pasta = dirname(fileURLToPath(import.meta.url));
const destino = resolve(pasta, "../../safeclick/static/js/vendor");
await mkdir(destino, { recursive: true });
const arquivo = join(destino, "forca-senha.js");

await build({
    absWorkingDir: pasta,
    entryPoints: [join(pasta, "estimador.mjs")],
    outfile: arquivo,
    bundle: true,
    minify: true,
    platform: "browser",
    format: "iife",
    globalName: "SafeClickForca",
    target: ["es2020"],
    tsconfigRaw: {},
    charset: "utf8",
    legalComments: "inline",
    banner: { js: "/*! SafeClick — estimador local baseado em zxcvbn-ts. Licenças: forca-senha.LICENSE.txt. Fonte: ferramentas/forca-senha/estimador.mjs. */" },
});

const pacotes = [
    "@zxcvbn-ts/core", "@zxcvbn-ts/language-common",
    "@zxcvbn-ts/language-en", "@zxcvbn-ts/language-pt-br",
    "@zxcvbn-ts/dictionary-compression", "fastest-levenshtein",
];
const licencas = [];
const versoes = [];
for (const nome of pacotes) {
    const raiz = join(pasta, "node_modules", nome);
    const pacote = JSON.parse(await readFile(join(raiz, "package.json"), "utf8"));
    const licenca = (await readdir(raiz)).find((nomeArquivo) => /^license(?:\.txt|\.md)?$/i.test(nomeArquivo));
    if (!licenca) throw new Error(`Licença não encontrada para ${nome}.`);
    versoes.push({ pacote: nome, versao: pacote.version, licenca: pacote.license });
    licencas.push(`${nome} ${pacote.version}\n${await readFile(join(raiz, licenca), "utf8")}`);
}
await writeFile(join(destino, "forca-senha.LICENSE.txt"), licencas.join("\n\n----------------------------------------\n\n"));
const conteudo = await readFile(arquivo);
await writeFile(join(destino, "forca-senha.manifesto.json"), JSON.stringify({
    biblioteca: "https://github.com/zxcvbn-ts/zxcvbn",
    compilador: "esbuild 0.28.2",
    arquivo: "forca-senha.js",
    bytes: conteudo.length,
    sha256: createHash("sha256").update(conteudo).digest("hex"),
    pacotes: versoes,
}, null, 2) + "\n");
console.log(`Estimador compilado: ${conteudo.length} bytes. Licenças e manifesto gerados.`);
