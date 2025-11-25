// ===============================
// processos.js – COMPLETO
// ===============================

document.addEventListener("DOMContentLoaded", function () {

    // =====================================================================
    // 🔵 LINHA 2 — PROCESSO / SUBPROCESSO
    // =====================================================================

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

    let selectListenerAdded = false;

    function limparCampos() {
        if (processoInputVisible) processoInputVisible.value = "";
        if (subprocessoField) subprocessoField.value = "";
        if (parentField) parentField.value = "";
        if (processoSelectVisible) processoSelectVisible.selectedIndex = 0;
    }

    function setModeProcesso() {

        rbProcesso.checked = true;
        rbSubprocesso.checked = false;

        lblProcesso.classList.add("text-blue-700");
        lblProcesso.classList.remove("text-gray-400");

        lblSubprocesso.classList.add("text-gray-400");
        lblSubprocesso.classList.remove("text-blue-700");

        lblCampoProcesso.classList.add("text-blue-700");
        lblCampoProcesso.classList.remove("text-gray-400");

        lblCampoSubprocesso.classList.add("text-gray-400");
        lblCampoSubprocesso.classList.remove("text-blue-700");

        processoInputVisible.classList.remove("hidden");
        processoSelectContainer.classList.add("hidden");

        processoInputVisible.disabled = false;
        processoInputVisible.classList.remove("bg-gray-100");

        subprocessoField.disabled = true;
        subprocessoField.classList.add("bg-gray-100", "text-gray-500");
        subprocessoField.classList.remove("bg-white");

        parentField.value = "";
        parentField.disabled = true;

        limparCampos();
    }

    function setModeSubprocesso() {

        rbProcesso.checked = false;
        rbSubprocesso.checked = true;

        lblProcesso.classList.add("text-blue-700");
        lblProcesso.classList.remove("text-gray-400");

        lblSubprocesso.classList.add("text-blue-700");
        lblSubprocesso.classList.remove("text-gray-400");

        lblCampoProcesso.classList.add("text-blue-700");
        lblCampoProcesso.classList.remove("text-gray-400");

        lblCampoSubprocesso.classList.add("text-blue-700");
        lblCampoSubprocesso.classList.remove("text-gray-400");

        processoInputVisible.classList.add("hidden");
        processoSelectContainer.classList.remove("hidden");

        subprocessoField.disabled = false;
        subprocessoField.classList.remove("bg-gray-100", "text-gray-500");
        subprocessoField.classList.add("bg-white");

        parentField.disabled = false;

        limparCampos();

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

                if (parentField.value) {
                    processoSelectVisible.value = parentField.value;
                }
            });

        if (!selectListenerAdded) {
            processoSelectVisible.addEventListener("change", function () {
                parentField.value = this.value;
            });
            selectListenerAdded = true;
        }
    }

    rbProcesso.addEventListener("change", () => setModeProcesso());
    rbSubprocesso.addEventListener("change", () => setModeSubprocesso());

    if (parentField.value) {
        setModeSubprocesso();
        processoSelectVisible.value = parentField.value;
    } else {
        setModeProcesso();
    }



    // =====================================================================
    // 🔵 LINHA 6 — MODELO DE PROCESSO (ATUALIZA CAMPOS)
    // =====================================================================

    const modeloSelect = document.getElementById("id_modelagem_processo");

    const temaModelo = document.getElementById("tema_modelo");
    const versaoModelo = document.getElementById("versao_modelo");
    const emitenteModelo = document.getElementById("emitente_modelo");
    const sistemaModelo = document.getElementById("sistema_modelo");
    const vigenciaModelo = document.getElementById("vigencia_modelo");

    function formatarDataISO_para_BR(iso) {
        if (!iso) return "";
        const partes = iso.split("-");
        return `${partes[2]}/${partes[1]}/${partes[0]}`;
    }

    function formatarVersao(v) {
        if (!v) return "";
        return v.toString().padStart(2, "0");
    }

    modeloSelect.addEventListener("change", function () {
        const opt = this.options[this.selectedIndex];

        if (!opt || opt.value === "") {
            temaModelo.value = "";
            versaoModelo.value = "";
            emitenteModelo.value = "";
            sistemaModelo.value = "";
            vigenciaModelo.value = "";
            return;
        }

        temaModelo.value = opt.dataset.tema || "";
        versaoModelo.value = formatarVersao(opt.dataset.versao);
        emitenteModelo.value = opt.dataset.emitente || "";
        sistemaModelo.value = opt.dataset.sistema || "";
        vigenciaModelo.value = formatarDataISO_para_BR(opt.dataset.vigencia);
    });



    // =====================================================================
    // 🔵 LINHA 8 — NORMA DE PROCEDIMENTO (ATUALIZA CAMPOS)
    // =====================================================================

    const normaSelect = document.getElementById("norma_procedimento");

    const temaNorma = document.getElementById("tema_norma");
    const versaoNorma = document.getElementById("versao_norma");
    const emitenteNorma = document.getElementById("emitente_norma");
    const sistemaNorma = document.getElementById("sistema_norma");
    const vigenciaNorma = document.getElementById("vigencia_norma");

    normaSelect.addEventListener("change", function () {
        const opt = this.options[this.selectedIndex];

        if (!opt || opt.value === "") {
            temaNorma.value = "";
            versaoNorma.value = "";
            emitenteNorma.value = "";
            sistemaNorma.value = "";
            vigenciaNorma.value = "";
            return;
        }

        temaNorma.value = opt.dataset.tema || "";
        versaoNorma.value = formatarVersao(opt.dataset.versao);
        emitenteNorma.value = opt.dataset.emitente || "";
        sistemaNorma.value = opt.dataset.sistema || "";
        vigenciaNorma.value = formatarDataISO_para_BR(opt.dataset.vigencia);
    });

});
