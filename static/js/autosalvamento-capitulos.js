(() => {
    const titulo = document.getElementById("titulo-capitulo");
    const ordem = document.getElementById("ordem-capitulo");
    const conteudo = document.getElementById("conteudo-capitulo");
    const idCampo = document.getElementById("capitulo-id");
    const mensagem = document.getElementById("mensagem-capitulo");
    const formulario = document.getElementById("form-capitulo");

    if (!titulo || !ordem || !conteudo || !idCampo ||
        !mensagem || !formulario) return;

    let temporizador = null;
    let versao = 0;
    let salvando = false;
    let precisaSalvar = false;

    function agendarSalvamento() {
        versao++;
        precisaSalvar = true;
        clearTimeout(temporizador);

        if (!idCampo.value) {
            mensagem.textContent = "Capítulo novo: salve manualmente.";
            return;
        }

        mensagem.textContent = "Alterações pendentes…";
        temporizador = setTimeout(salvarAutomaticamente, 2000);
    }

    async function salvarAutomaticamente() {
        const id = idCampo.value;

        if (!id || salvando || !precisaSalvar) return;

        const versaoAtual = versao;
        const dados = {
            titulo: titulo.value.trim(),
            ordem: Number(ordem.value),
            conteudo: conteudo.value
        };

        if (!dados.titulo || !Number.isInteger(dados.ordem) ||
            dados.ordem < 1) {
            mensagem.textContent = "Confira o título e a ordem do capítulo.";
            return;
        }

        salvando = true;
        precisaSalvar = false;
        mensagem.textContent = "Salvando…";

        try {
            const resposta = await fetch("/api/capitulos/" + id, {
                method: "PUT",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify(dados)
            });

            let resultado = {};
            try {
                resultado = await resposta.json();
            } catch (_) {
                // A resposta pode não conter JSON válido.
            }

            if (!resposta.ok) {
                throw new Error(
                    resultado.erro || "Falha no salvamento automático."
                );
            }

            if (idCampo.value === id && versao === versaoAtual) {
                mensagem.textContent = "Salvo automaticamente.";
            }
        } catch (erro) {
            if (idCampo.value === id && versao === versaoAtual) {
                mensagem.textContent = erro.message;
            }
        } finally {
            salvando = false;

            if (idCampo.value === id && precisaSalvar) {
                clearTimeout(temporizador);
                temporizador = setTimeout(salvarAutomaticamente, 500);
            }
        }
    }

    [titulo, ordem, conteudo].forEach(campo => {
        campo.addEventListener("input", agendarSalvamento);
    });

    formulario.addEventListener("submit", () => {
        clearTimeout(temporizador);
        precisaSalvar = false;
    });

    document.getElementById("botao-cancelar-capitulo")
        ?.addEventListener("click", () => {
            clearTimeout(temporizador);
            precisaSalvar = false;
        });

    document.getElementById("botao-fechar-capitulos")
        ?.addEventListener("click", () => {
            clearTimeout(temporizador);
            precisaSalvar = false;
        });

    document.getElementById("botao-organizar-paragrafos")
        ?.addEventListener("click", () => {
            if (idCampo.value) agendarSalvamento();
        });
})();
