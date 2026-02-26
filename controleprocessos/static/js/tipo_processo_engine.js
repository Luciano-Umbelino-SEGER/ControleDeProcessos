function initTipoProcesso(config = {}) {

    const {
        radioProcessoId = "rb_processo",
        radioSubprocessoId = "rb_subprocesso",
        processoInputId = "processo_input_visible",
        processoSelectContainerId = "processo_select_container",
        processoSelectId = "processo_select_visible",
        subprocessoInputId = "subprocesso_input_visible",
        hiddenNomeId = "id_nome",
        parentFieldId = "id_parent",
        labelCampoEsquerdoId = "lbl_campo_esquerdo"
    } = config;

    document.addEventListener("DOMContentLoaded", function () {

        const rbProcesso = document.getElementById(radioProcessoId);
        const rbSubprocesso = document.getElementById(radioSubprocessoId);

        const processoInput = document.getElementById(processoInputId);
        const processoSelectContainer = document.getElementById(processoSelectContainerId);
        const processoSelect = document.getElementById(parentFieldId);

        const subprocessoInput = document.getElementById(subprocessoInputId);

        const hiddenNome = document.getElementById(hiddenNomeId);
        const parentField = document.getElementById(parentFieldId);

        const lblCampoProcesso = document.getElementById("lbl_campo_processo");
        const lblCampoSubprocesso = document.getElementById("lbl_campo_subprocesso");

        if (!rbProcesso || !rbSubprocesso) return;

        function atualizarLayout() {

            const lblProcesso = document.getElementById("lbl_processo");
            const lblSubprocesso = document.getElementById("lbl_subprocesso");

            if (rbProcesso.checked) {

                // 🔵 Radios
                if (lblProcesso) {
                    lblProcesso.classList.add("text-blue-700");
                    lblProcesso.classList.remove("text-gray-400");
                }

                if (lblSubprocesso) {
                    lblSubprocesso.classList.remove("text-blue-700");
                    lblSubprocesso.classList.add("text-gray-400");
                }

                // 🔹 Label campo processo
                if (lblCampoProcesso) {
                    lblCampoProcesso.textContent = "Nome do Processo";
                    lblCampoProcesso.classList.add("text-blue-700");
                    lblCampoProcesso.classList.remove("text-gray-400");
                }

                // 🔹 Label campo subprocesso
                if (lblCampoSubprocesso) {
                    lblCampoSubprocesso.classList.remove("text-blue-700");
                    lblCampoSubprocesso.classList.add("text-gray-400");
                }

                // 🔹 Campos
                if (processoInput) processoInput.classList.remove("hidden");
                if (processoSelectContainer) processoSelectContainer.classList.add("hidden");

                if (subprocessoInput) {
                    subprocessoInput.disabled = true;
                    subprocessoInput.classList.add("bg-gray-100");
                }

                if (parentField) parentField.value = "";

            } else {

                // 🔵 Radios
                if (lblSubprocesso) {
                    lblSubprocesso.classList.add("text-blue-700");
                    lblSubprocesso.classList.remove("text-gray-400");
                }

                if (lblProcesso) {
                    lblProcesso.classList.remove("text-blue-700");
                    lblProcesso.classList.add("text-gray-400");
                }

                // 🔹 Label campo processo
                if (lblCampoProcesso) {
                    lblCampoProcesso.textContent = "Selecionar Processo para associar";
                    lblCampoProcesso.classList.add("text-blue-700");
                    lblCampoProcesso.classList.remove("text-gray-400");
                }

                // 🔹 Label campo subprocesso
                if (lblCampoSubprocesso) {
                    lblCampoSubprocesso.classList.add("text-blue-700");
                    lblCampoSubprocesso.classList.remove("text-gray-400");
                }

                // 🔹 Campos
                if (processoInput) processoInput.classList.add("hidden");
                if (processoSelectContainer) processoSelectContainer.classList.remove("hidden");

                if (subprocessoInput) {
                    subprocessoInput.disabled = false;
                    subprocessoInput.classList.remove("bg-gray-100");
                }
            }
        }

        function sincronizarNome() {
            if (!hiddenNome) return;

            if (rbProcesso.checked && processoInput) {
                hiddenNome.value = processoInput.value.trim();
            } else if (subprocessoInput) {
                hiddenNome.value = subprocessoInput.value.trim();
            }
        }

        if (processoInput) processoInput.addEventListener("input", sincronizarNome);
        if (subprocessoInput) subprocessoInput.addEventListener("input", sincronizarNome);

        rbProcesso.addEventListener("change", atualizarLayout);
        rbSubprocesso.addEventListener("change", atualizarLayout);

        atualizarLayout();
    });
}