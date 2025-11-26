// ===============================
// processos.js – VERSÃO FINAL
// ===============================

document.addEventListener("DOMContentLoaded", function () {

    // =========================
    // Helpers
    // =========================
    function safeGet(id) { try { return document.getElementById(id); } catch(e) { return null; } }
    function safeFetchJson(url) { return fetch(url, { headers: { 'X-Requested-With': 'XMLHttpRequest' } }).then(r => r.json()); }

    const ENABLE_REVERSE_UPDATE = false;

    // =====================================================================
    // 🔵 LINHA 2 — PROCESSO / SUBPROCESSO
    // =====================================================================
    const rbProcesso = safeGet("rb_processo");
    const rbSubprocesso = safeGet("rb_subprocesso");

    const lblProcesso = safeGet("lbl_processo");
    const lblSubprocesso = safeGet("lbl_subprocesso");

    const lblCampoProcesso = safeGet("lbl_campo_processo");
    const lblCampoSubprocesso = safeGet("lbl_campo_subprocesso");

    const processoInputVisible = safeGet("processo_input_visible");
    const processoSelectContainer = safeGet("processo_select_container");
    const processoSelectVisible = safeGet("processo_select_visible");

    const parentField = safeGet("id_parent");
    const subprocessoField = safeGet("id_nome");

    let selectListenerAdded = false;

    function limparCampos() {
        if (processoInputVisible) processoInputVisible.value = "";
        if (subprocessoField) subprocessoField.value = "";
        if (parentField) parentField.value = "";
        if (processoSelectVisible) processoSelectVisible.selectedIndex = 0;
    }

    function setModeProcesso() {
        if (!rbProcesso) return;

        rbProcesso.checked = true;
        rbSubprocesso.checked = false;

        if (lblProcesso) lblProcesso.classList.add("text-blue-700");
        if (lblProcesso) lblProcesso.classList.remove("text-gray-400");

        if (lblSubprocesso) lblSubprocesso.classList.add("text-gray-400");
        if (lblSubprocesso) lblSubprocesso.classList.remove("text-blue-700");

        if (lblCampoProcesso) lblCampoProcesso.classList.add("text-blue-700");
        if (lblCampoSubprocesso) lblCampoSubprocesso.classList.add("text-gray-400");

        processoInputVisible.classList.remove("hidden");
        processoSelectContainer.classList.add("hidden");

        processoInputVisible.disabled = false;
        subprocessoField.disabled = true;
        subprocessoField.classList.add("bg-gray-100");

        parentField.value = "";
        parentField.disabled = true;

        limparCampos();
    }

    function setModeSubprocesso() {
        rbSubprocesso.checked = true;
        rbProcesso.checked = false;

        if (lblSubprocesso) lblSubprocesso.classList.add("text-blue-700");
        if (lblSubprocesso) lblSubprocesso.classList.remove("text-gray-400");

        processoInputVisible.classList.add("hidden");
        processoSelectContainer.classList.remove("hidden");

        subprocessoField.disabled = false;
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
                if (parentField.value) processoSelectVisible.value = parentField.value;
            });

        if (!selectListenerAdded) {
            processoSelectVisible.addEventListener("change", function () {
                parentField.value = this.value;
            });
            selectListenerAdded = true;
        }
    }

    if (rbProcesso) rbProcesso.addEventListener("change", setModeProcesso);
    if (rbSubprocesso) rbSubprocesso.addEventListener("change", setModeSubprocesso);

    if (parentField && parentField.value) setModeSubprocesso();
    else setModeProcesso();


    // =====================================================================
    // 🔵 MODELO / NORMA – atualizações informativas
    // =====================================================================
    function formatarDataISO_para_BR(iso) {
        if (!iso) return "";
        const p = iso.split("-");
        return `${p[2]}/${p[1]}/${p[0]}`;
    }
    const modeloSelect = safeGet("id_modelagem_processo");
    if (modeloSelect) {
        modeloSelect.addEventListener("change", function () {
            const opt = this.options[this.selectedIndex];
            safeGet("tema_modelo").value = opt.dataset.tema || "";
            safeGet("emitente_modelo").value = opt.dataset.emitente || "";
            safeGet("sistema_modelo").value = opt.dataset.sistema || "";
            safeGet("versao_modelo").value = opt.dataset.versao || "";
            safeGet("vigencia_modelo").value = formatarDataISO_para_BR(opt.dataset.vigencia);
        });
    }

    const normaSelect = safeGet("norma_procedimento");
    if (normaSelect) {
        normaSelect.addEventListener("change", function () {
            const opt = this.options[this.selectedIndex];
            safeGet("tema_norma").value = opt.dataset.tema || "";
            safeGet("emitente_norma").value = opt.dataset.emitente || "";
            safeGet("sistema_norma").value = opt.dataset.sistema || "";
            safeGet("versao_norma").value = opt.dataset.versao || "";
            safeGet("vigencia_norma").value = formatarDataISO_para_BR(opt.dataset.vigencia);
        });
    }


    // =====================================================================
    // 🔵 TRIPLE FILTER
    // =====================================================================
    (function tripleFilter() {

        const selClass = safeGet("id_classificacao");
        const selMacro1 = safeGet("id_macroprocesso_nivel1");
        const selMacro2 = safeGet("id_macroprocesso_nivel2");

        if (!selClass) return;

        const API_MACRO1_BY_CLASS = "/api/macroprocessos_por_classificacao/";
        const API_MACRO2_BY_MACRO1 = "/api/macro2_por_macro1/";
        const API_CLASS_BY_MACRO1 = "/api/classificacao_por_macro1/";
        const API_MACRO1_ALL = "/api/macro1_todos/";
        const API_MACRO2_ALL = "/api/macro2_todos/";

        let cacheMacro1 = null;
        let cacheMacro2 = null;

        function addOptions(select, items) {
            select.innerHTML = `<option value="">---------</option>`;
            items.forEach(i => {
                const opt = document.createElement("option");
                opt.value = i.id;
                opt.textContent = i.nome;
                select.appendChild(opt);
            });
        }

        async function loadCache1() {
            if (!cacheMacro1) cacheMacro1 = (await safeFetchJson(API_MACRO1_ALL)).macro1;
            return cacheMacro1;
        }
        async function loadCache2() {
            if (!cacheMacro2) cacheMacro2 = (await safeFetchJson(API_MACRO2_ALL)).macro2;
            return cacheMacro2;
        }

        selClass.addEventListener("change", async function () {
            const classId = this.value;
            if (!classId) {
                addOptions(selMacro1, await loadCache1());
                addOptions(selMacro2, await loadCache2());
                return;
            }
            const r = await safeFetchJson(API_MACRO1_BY_CLASS + classId + "/");
            addOptions(selMacro1, r.macroprocessos);
            const m2 = await loadCache2();
            addOptions(selMacro2, m2.filter(x => r.macroprocessos.map(m => m.id).includes(x.macroprocesso_nivel1_id)));
        });

        selMacro1.addEventListener("change", async function () {
            const id = this.value;
            if (!id) { addOptions(selMacro2, await loadCache2()); return; }
            const c = await safeFetchJson(API_CLASS_BY_MACRO1 + id + "/");
            selClass.value = c.classificacao_id;
            selClass.dispatchEvent(new Event("change"));
            const r = await safeFetchJson(API_MACRO2_BY_MACRO1 + id + "/");
            addOptions(selMacro2, r.macro2);
        });

    })();

    // =====================================================================
    // 🔴 DESTACAR CAMPOS COM ERRO
    // =====================================================================
    const errorBlocks = document.querySelectorAll(".alert ul li strong");
    errorBlocks.forEach(err => {
        const fieldName = err.textContent.replace(":", "").trim();
        const field = document.querySelector(`[name="${fieldName}"]`);
        if (field) {
            field.classList.add("border-red-500", "ring-2", "ring-red-300");
        }
    });

    // ======================================================
    // 🔵 SINCRONIZAÇÃO FINAL DOS CAMPOS ANTES DO SUBMIT
    // ======================================================
    const formProcesso = document.getElementById("form-processo");
    if (formProcesso) {
        formProcesso.addEventListener("submit", function (e) {

            const tipo = rbProcesso?.checked ? "processo" : "subprocesso";

            // campo nome real do Django
            const fieldNome = safeGet("id_nome");

            if (!fieldNome) return; // segurança máxima

            if (tipo === "processo") {
                // nome = input texto do processo
                fieldNome.value = processoInputVisible?.value || "";

                // parent = vazio
                if (parentField) parentField.value = "";

            } else {
                // nome = input texto do subprocesso
                fieldNome.value = subprocessoField?.value || "";

                // parent = option selecionado no combo
                if (parentField) {
                    parentField.value = processoSelectVisible?.value || "";
                }
            }

        });
    }

}); // DOM READY
