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

    // 🔥 Memória inicia com valor real atual
    let memoriaSubprocesso = hiddenNome?.value || "";

    /* =====================================================
       FONTE ÚNICA DE VERDADE
    ====================================================== */
    function sincronizarNome() {
        if (!hiddenNome) return;

        if (rbProcesso.checked) {
            hiddenNome.value = processoInput?.value.trim() || "";
        } else {
            hiddenNome.value = subprocessoInput?.value.trim() || "";
        }
    }

    processoInput?.addEventListener("input", sincronizarNome);
    subprocessoInput?.addEventListener("input", sincronizarNome);

    /* =====================================================
       ATUALIZA LAYOUT
    ====================================================== */
    function atualizarLayout() {

        const modoProcesso = rbProcesso.checked;

        if (modoProcesso) {

            // Visual
            lblProcesso?.classList.add("text-blue-700");
            lblProcesso?.classList.remove("text-gray-400");

            lblSubprocesso?.classList.remove("text-blue-700");
            lblSubprocesso?.classList.add("text-gray-400");

            if (lblCampoProcesso) {
                lblCampoProcesso.textContent = "Nome do Processo";
            }

            processoInput?.classList.remove("hidden");
            processoSelectContainer?.classList.add("hidden");

            // 🔥 Guarda antes de limpar
            if (subprocessoInput) {
                memoriaSubprocesso = subprocessoInput.value;
                subprocessoInput.value = "";
                subprocessoInput.disabled = true;
                subprocessoInput.classList.add("bg-gray-100");
            }

            if (parentField) {
                parentField.value = "";
            }

        } else {

            // Visual
            lblSubprocesso?.classList.add("text-blue-700");
            lblSubprocesso?.classList.remove("text-gray-400");

            lblProcesso?.classList.remove("text-blue-700");
            lblProcesso?.classList.add("text-gray-400");

            if (lblCampoProcesso) {
                lblCampoProcesso.textContent = "Selecionar Processo para associar";
            }

            processoInput?.classList.add("hidden");
            processoSelectContainer?.classList.remove("hidden");

            if (subprocessoInput) {
                subprocessoInput.disabled = false;
                subprocessoInput.classList.remove("bg-gray-100");

                // 🔥 RESTAURA
                subprocessoInput.value = memoriaSubprocesso;
            }
        }

        sincronizarNome();
    }

    rbProcesso.addEventListener("change", atualizarLayout);
    rbSubprocesso.addEventListener("change", atualizarLayout);

    /* =====================================================
       HIDRATAÇÃO INICIAL
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
       SINCRONIZA SELECT DJANGO COM HIDDEN PARENT
    ====================================================== */

    const djangoSelectParent = document.querySelector("#processo_select_container select");

    if (djangoSelectParent && parentField) {

        djangoSelectParent.value = parentField.value || "";

        djangoSelectParent.addEventListener("change", function () {
            parentField.value = this.value;
        });
    }

    atualizarLayout();
}