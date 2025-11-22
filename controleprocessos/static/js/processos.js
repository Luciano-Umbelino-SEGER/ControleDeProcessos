// ===============================
// LINHA 2 - Processo / Subprocesso
// ===============================
document.addEventListener("DOMContentLoaded", function () {

    // -----------------------------
    // ELEMENTOS
    // -----------------------------
    const rbProcesso = document.getElementById("rb_processo");
    const rbSubprocesso = document.getElementById("rb_subprocesso");

    const lblProcesso = document.getElementById("lbl_processo");
    const lblSubprocesso = document.getElementById("lbl_subprocesso");

    const lblCampoProcesso = document.getElementById("lbl_campo_processo");
    const lblCampoSubprocesso = document.getElementById("lbl_campo_subprocesso");

    const processoInputVisible = document.getElementById("processo_input_visible");
    const processoSelectContainer = document.getElementById("processo_select_container");
    const processoSelectVisible = document.getElementById("processo_select_visible");

    const parentField = document.getElementById("id_parent");
    const subprocessoField = document.getElementById("id_nome");

    // Controla listener único
    let selectListenerAdded = false;


    // --------------------------------------------------------
    // FUNÇÃO AUXILIAR — LIMPAR CAMPOS
    // --------------------------------------------------------
    function limparCampos() {
        if (processoInputVisible) processoInputVisible.value = "";
        if (subprocessoField) subprocessoField.value = "";
        if (parentField) parentField.value = "";
        if (processoSelectVisible) processoSelectVisible.selectedIndex = 0;
    }


    // --------------------------------------------------------
    // MODO PROCESSO
    // --------------------------------------------------------
    function setModeProcesso() {

        // Rádio
        rbProcesso.checked = true;
        rbSubprocesso.checked = false;

        // LABELS
        lblProcesso.classList.add("text-blue-700");
        lblProcesso.classList.remove("text-gray-400");

        lblSubprocesso.classList.add("text-gray-400");
        lblSubprocesso.classList.remove("text-blue-700");

        lblCampoProcesso.classList.add("text-blue-700");
        lblCampoProcesso.classList.remove("text-gray-400");

        lblCampoSubprocesso.classList.add("text-gray-400");
        lblCampoSubprocesso.classList.remove("text-blue-700");

        // Mostrar INPUT / ocultar SELECT
        processoInputVisible.classList.remove("hidden");
        processoSelectContainer.classList.add("hidden");

        // processo ATIVO (input)
        processoInputVisible.disabled = false;
        processoInputVisible.classList.remove("bg-gray-100");

        // Subprocesso desativado (quando modo Processo)
        subprocessoField.disabled = true;
        subprocessoField.classList.add("bg-gray-100", "text-gray-500");
        subprocessoField.classList.remove("bg-white");

        // hidden parent desativado
        parentField.value = "";
        parentField.disabled = true;

        limparCampos();
    }


    // --------------------------------------------------------
    // MODO SUBPROCESSO
    // --------------------------------------------------------
    function setModeSubprocesso() {

        rbProcesso.checked = false;
        rbSubprocesso.checked = true;

        // LABELS
        lblProcesso.classList.add("text-blue-700");  // Processo sempre azul
        lblProcesso.classList.remove("text-gray-400");

        lblSubprocesso.classList.add("text-blue-700");
        lblSubprocesso.classList.remove("text-gray-400");

        lblCampoProcesso.classList.add("text-blue-700");
        lblCampoProcesso.classList.remove("text-gray-400");

        lblCampoSubprocesso.classList.add("text-blue-700");
        lblCampoSubprocesso.classList.remove("text-gray-400");

        // Ocultar input / mostrar select
        processoInputVisible.classList.add("hidden");
        processoSelectContainer.classList.remove("hidden");

        // Subprocesso ativado (quando modo Subprocesso)
        subprocessoField.disabled = false;
        subprocessoField.classList.remove("bg-gray-100", "text-gray-500");
        subprocessoField.classList.add("bg-white");

        // parent habilitado
        parentField.disabled = false;

        limparCampos();

        // Carregar processos pai via API
        fetch("/api/processos_pai/")
            .then(r => r.json())
            .then(data => {
                processoSelectVisible.innerHTML = `<option value="">---------</option>`;

                data.processos_pai.forEach(p => {
                    const opt = document.createElement("option");
                    opt.value = p.id;
                    opt.textContent = p.nome;
                    processoSelectVisible.appendChild(opt);
                });

                // Se estiver editando — restaura seleção
                if (parentField.value) {
                    processoSelectVisible.value = parentField.value;
                }
            });

        // Listener único
        if (!selectListenerAdded) {
            processoSelectVisible.addEventListener("change", function () {
                parentField.value = this.value;
            });
            selectListenerAdded = true;
        }
    }


    // --------------------------------------------------------
    // EVENTOS DOS RÁDIOS
    // --------------------------------------------------------
    rbProcesso.addEventListener("change", () => setModeProcesso());
    rbSubprocesso.addEventListener("change", () => setModeSubprocesso());


    // --------------------------------------------------------
    // ESTADO INICIAL — EDIÇÃO OU INCLUSÃO
    // --------------------------------------------------------
    if (parentField.value) {
        // É SUBPROCESSO
        setModeSubprocesso();
        processoSelectVisible.value = parentField.value;
    } else {
        // É PROCESSO
        setModeProcesso();
    }

});
