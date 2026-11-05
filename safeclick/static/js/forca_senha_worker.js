
importScripts("./vendor/forca-senha.js");

self.addEventListener("message", (evento) => {
    const dados = evento.data;
    if (!dados || !Number.isSafeInteger(dados.id) || dados.id < 0) return;

    try {
        const avaliacao = SafeClickForca.avaliar(dados.senha);
        self.postMessage({ id: dados.id, avaliacao });
    } catch {
        self.postMessage({ id: dados.id, erro: "Não foi possível estimar a força agora." });
    }
});
