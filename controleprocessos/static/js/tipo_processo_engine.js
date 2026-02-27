function initTipoProcesso(config = {}) {

    const {
        radioProcessoId = "rb_processo",
        radioSubprocessoId = "rb_subprocesso",
        processoInputId = "processo_input_visible",
        processoSelectContainerId = "processo_select_container",
        subprocessoInputId = "subprocesso_input_visible",
        hiddenNomeId = "id_nome",
        parentFieldId = "id_parent"
    } = config;

    const rbProcesso = document.getElementById(radioProcessoId);
    const rbSubprocesso = document.getElementById(radioSubprocessoId);

    const processoInput = document.getElementById(processoInputId);
    const processoSelectContainer = document.getElementById(processoSelectContainerId);
    const subprocessoInput = document.getElementById(subprocessoInputId);

    const hiddenNome = document.getElementById(hiddenNomeId);
    const parentField = document.getElementById(parentFieldId);

    const lblProcesso = document.getElementById("lbl_processo");
    const lblSubprocesso = document.getElementById("lbl_subprocesso");
    const lblCampoProcesso = document.getElementById("lbl_campo_processo");
    const lblCampoSubprocesso = document.getElementById("lbl_campo_subprocesso");

    if (!rbProcesso || !rbSubprocesso) return;

    /* =====================================================
       ATUALIZA LAYOUT (VISUAL)
    ====================================================== */
    function atualizarLayout() {

        const modoProcesso = rbProcesso.checked;

        if (modoProcesso) {

            // Radios
            lblProcesso?.classList.add("text-blue-700");
            lblProcesso?.classList.remove("text-gray-400");

            lblSubprocesso?.classList.remove("text-blue-700");
            lblSubprocesso?.classList.add("text-gray-400");

            // Labels
            if (lblCampoProcesso) {
                lblCampoProcesso.textContent = "Nome do Processo";
                lblCampoProcesso.classList.add("text-blue-700");
                lblCampoProcesso.classList.remove("text-gray-400");
            }

            lblCampoSubprocesso?.classList.remove("text-blue-700");
            lblCampoSubprocesso?.classList.add("text-gray-400");

            // Campos
            processoInput?.classList.remove("hidden");
            processoSelectContainer?.classList.add("hidden");

            if (subprocessoInput) {
                subprocessoInput.disabled = true;
                subprocessoInput.classList.add("bg-gray-100");
            }

            if (parentField) parentField.value = "";

        } else {

            // Radios
            lblSubprocesso?.classList.add("text-blue-700");
            lblSubprocesso?.classList.remove("text-gray-400");

            lblProcesso?.classList.remove("text-blue-700");
            lblProcesso?.classList.add("text-gray-400");

            // Labels
            if (lblCampoProcesso) {
                lblCampoProcesso.textContent = "Selecionar Processo para associar";
                lblCampoProcesso.classList.add("text-blue-700");
                lblCampoProcesso.classList.remove("text-gray-400");
            }

            lblCampoSubprocesso?.classList.add("text-blue-700");
            lblCampoSubprocesso?.classList.remove("text-gray-400");

            // Campos
            processoInput?.classList.add("hidden");
            processoSelectContainer?.classList.remove("hidden");

            if (subprocessoInput) {
                subprocessoInput.disabled = false;
                subprocessoInput.classList.remove("bg-gray-100");
            }
        }
    }

    /* =====================================================
       SINCRONIZA NOME COM HIDDEN
    ====================================================== */
    function sincronizarNome() {
        if (!hiddenNome) return;

        if (rbProcesso.checked && processoInput) {
            hiddenNome.value = processoInput.value.trim();
        } else if (rbSubprocesso.checked && subprocessoInput) {
            hiddenNome.value = subprocessoInput.value.trim();
        }
    }

    processoInput?.addEventListener("input", sincronizarNome);
    subprocessoInput?.addEventListener("input", sincronizarNome);

    rbProcesso.addEventListener("change", atualizarLayout);
    rbSubprocesso.addEventListener("change", atualizarLayout);

    /* =====================================================
       HIDRATAÇÃO INICIAL (AQUI ESTAVA O PROBLEMA)
    ====================================================== */

    if (hiddenNome) {
        if (rbProcesso.checked && processoInput) {
            processoInput.value = hiddenNome.value || "";
        }

        if (rbSubprocesso.checked && subprocessoInput) {
            subprocessoInput.value = hiddenNome.value || "";
        }
    }

    /* =====================================================
       SINCRONIZA SELECT DO DJANGO COM HIDDEN PARENT
    ====================================================== */

    const djangoSelectParent = document.querySelector("#processo_select_container select");

    if (djangoSelectParent && parentField) {

        // Preenche select com valor existente
        djangoSelectParent.value = parentField.value || "";

        // Mantém hidden atualizado
        djangoSelectParent.addEventListener("change", function () {
            parentField.value = this.value;
        });
    }

    // Aplica layout final
    atualizarLayout();
}