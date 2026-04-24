function initTipoProcessoMapear(config = {}) {

    // =========================================
    // 🔥 CONFIG
    // =========================================
    const urlHeranca = config.urlHeranca;
    window.isTrocandoTipo = false;

    // =========================================
    // 🔥 ELEMENTOS
    // =========================================
    const processoInput = document.getElementById("processo_input_visible");
    const subprocessoInput = document.getElementById("subprocesso_input_visible");
    const hiddenNome = document.getElementById("id_nome");

    const rbProcesso = document.getElementById("rb_processo");
    const rbSubprocesso = document.getElementById("rb_subprocesso");
    const rbOutro = document.getElementById("rb_outro");

    const btnAdicionar = document.getElementById("btn_adicionar");

    const lblProcesso = document.getElementById("lbl_processo");
    const lblSubprocesso = document.getElementById("lbl_subprocesso");
    const lblOutro = document.getElementById("lbl_outro");

    const lblCampoProcesso = document.getElementById("lbl_campo_processo");
    const lblCampoSubprocesso = document.getElementById("lbl_campo_subprocesso");

    const containerSelect = document.getElementById("processo_select_container");

    // =========================================
    // 🔥 ESTADO
    // =========================================
    let tipoAtual = "processo";

    let cacheValores = {
        processo: "",
        subprocesso: "",
        outro: ""
    };

    // =========================================
    // 🔥 UTIL
    // =========================================
    function getTipoSelecionado() {
        if (rbProcesso?.checked) return "processo";
        if (rbSubprocesso?.checked) return "subprocesso";
        return "outro";
    }

    function sincronizarNome() {
        if (!hiddenNome) return;

        if (tipoAtual === "processo") {
            hiddenNome.value = processoInput?.value || "";
        } else {
            hiddenNome.value = subprocessoInput?.value || "";
        }
    }

    // =========================================
    // 🔥 UI
    // =========================================
    function atualizarLabels() {

        // RESET
        lblProcesso?.classList.remove("text-blue-700", "text-gray-400")
        lblSubprocesso?.classList.remove("text-blue-700", "text-gray-400")
        lblOutro?.classList.remove("text-blue-700", "text-gray-400")

        lblCampoSubprocesso?.classList.remove("text-blue-700", "text-gray-400")

        if (rbProcesso?.checked) {

            lblProcesso?.classList.add("text-blue-700")
            lblSubprocesso?.classList.add("text-gray-400")
            lblOutro?.classList.add("text-gray-400")

            lblCampoProcesso.textContent = "Nome do Processo"

            lblCampoSubprocesso.textContent = "Nome do Subprocesso"
            lblCampoSubprocesso.classList.add("text-gray-400") // 🔥 desabilitado
        }

        else if (rbSubprocesso?.checked) {

            lblSubprocesso?.classList.add("text-blue-700")
            lblProcesso?.classList.add("text-gray-400")
            lblOutro?.classList.add("text-gray-400")

            lblCampoProcesso.textContent = "Selecionar Processo para associar"

            lblCampoSubprocesso.textContent = "Nome do Subprocesso"
            lblCampoSubprocesso.classList.add("text-blue-700") // 🔥 ativo
        }

        else if (rbOutro?.checked) {

            lblOutro?.classList.add("text-blue-700")
            lblProcesso?.classList.add("text-gray-400")
            lblSubprocesso?.classList.add("text-gray-400")

            lblCampoProcesso.textContent = "Selecionar Processo para associar"

            lblCampoSubprocesso.textContent = "Nome do Elemento"
            lblCampoSubprocesso.classList.add("text-blue-700") // 🔥 ativo
        }
    }

    function atualizarBotoes() {
        if (!btnAdicionar) return;

        btnAdicionar.textContent =
            tipoAtual === "outro"
                ? "Adicionar Elemento"
                : "Adicionar Processo a Mapear";
    }

    function atualizarVisibilidadeCampos() {

        if (tipoAtual === "processo") {

            processoInput?.classList.remove("hidden");
            containerSelect?.classList.add("hidden");

            if (subprocessoInput) {
                subprocessoInput.disabled = true;
                subprocessoInput.classList.add("bg-gray-100");
                subprocessoInput.value = "";
            }
        }

        else {

            processoInput?.classList.add("hidden");
            containerSelect?.classList.remove("hidden");

            if (subprocessoInput) {
                subprocessoInput.disabled = false;
                subprocessoInput.classList.remove("bg-gray-100");
            }
        }
    }

    // =========================================
    // 🔥 CACHE
    // =========================================
    function salvarCache(tipoAnterior) {

        if (tipoAnterior === "processo") {
            cacheValores.processo = processoInput?.value || "";
        }

        if (tipoAnterior === "subprocesso") {
            cacheValores.subprocesso = subprocessoInput?.value || "";
        }

        if (tipoAnterior === "outro") {
            cacheValores.outro = subprocessoInput?.value || "";
        }
    }

    function restaurarCache() {

        if (tipoAtual === "processo") {
            processoInput.value = cacheValores.processo || "";
        }

        if (tipoAtual === "subprocesso") {
            subprocessoInput.value = cacheValores.subprocesso || "";
        }

        if (tipoAtual === "outro") {
            subprocessoInput.value = cacheValores.outro || "";
        }
    }

    // =========================================
    // 🔥 HERANÇA
    // =========================================
    window.aplicarRegraHeranca = function () {

        const processoId = $('#id_parent_select').val();

        if (tipoAtual === "processo") {
            HerancaProcesso.limpar();
            return;
        }

        if (processoId) {
            HerancaProcesso.aplicar(processoId, {
                url: urlHeranca,
                onApply: () => restaurarCache()
            });
        } else {
            HerancaProcesso.limpar();
            restaurarCache();
        }
    };

    // =========================================
    // 🔥 TROCA DE TIPO (CORE)
    // =========================================
    function trocarTipo(event = null) {

        window.isTrocandoTipo = true;

        const novoTipo = event ? event.target.value : getTipoSelecionado();
        const tipoAnterior = tipoAtual;

        // 1. salva cache
        salvarCache(tipoAnterior);

        // 🔥 LIMPA SEMPRE O CAMPO VISUAL (garante não herdar valor do banco)
        if (processoInput) processoInput.value = ""
        if (subprocessoInput) subprocessoInput.value = ""

        // 3. atualiza estado
        tipoAtual = novoTipo;

        // 4. UI
        atualizarLabels();
        atualizarVisibilidadeCampos();
        atualizarBotoes();

        // 5. restaura cache
        restaurarCache();

        // 6. herança
        aplicarRegraHeranca();

        // 7. sync hidden
        sincronizarNome();

        setTimeout(() => window.isTrocandoTipo = false, 0);
    }

    // =========================================
    // 🔥 EVENTOS
    // =========================================
    rbProcesso?.addEventListener("click", trocarTipo);
    rbSubprocesso?.addEventListener("click", trocarTipo);
    rbOutro?.addEventListener("click", trocarTipo);

    processoInput?.addEventListener("input", sincronizarNome);
    subprocessoInput?.addEventListener("input", sincronizarNome);

    // =========================================
    // 🔥 INIT
    // =========================================
    tipoAtual = getTipoSelecionado();

    cacheValores.processo = processoInput?.value || "";
    cacheValores.subprocesso = subprocessoInput?.value || "";
    cacheValores.outro = subprocessoInput?.value || "";

    trocarTipo();
}