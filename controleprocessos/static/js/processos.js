// ===============================
// processos.js – FINAL (robusto, reverse-update DESATIVADO por padrão)
// ===============================

document.addEventListener("DOMContentLoaded", function () {

    // =========================
    // Config
    // =========================
    const ENABLE_REVERSE_UPDATE = false; // mudar para true só se quiser reativar a seleção reversa (com cautela)

    // -------------------------
    // Helpers de segurança
    // -------------------------
    function safeGet(id) { try { return document.getElementById(id); } catch(e) { return null; } }
    function safeFetchJson(url) { return fetch(url, { headers: { 'X-Requested-With': 'XMLHttpRequest' } }).then(r => r.json()); }

    // =====================================================================
    // 🔵 LINHA 2 — PROCESSO / SUBPROCESSO (mantido)
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
        if (!rbProcesso || !rbSubprocesso) return;

        rbProcesso.checked = true;
        rbSubprocesso.checked = false;

        if (lblProcesso) lblProcesso.classList.add("text-blue-700");
        if (lblProcesso) lblProcesso.classList.remove("text-gray-400");
        if (lblSubprocesso) lblSubprocesso.classList.add("text-gray-400");
        if (lblSubprocesso) lblSubprocesso.classList.remove("text-blue-700");

        if (lblCampoProcesso) lblCampoProcesso.classList.add("text-blue-700");
        if (lblCampoProcesso) lblCampoProcesso.classList.remove("text-gray-400");
        if (lblCampoSubprocesso) lblCampoSubprocesso.classList.add("text-gray-400");
        if (lblCampoSubprocesso) lblCampoSubprocesso.classList.remove("text-blue-700");

        if (processoInputVisible) processoInputVisible.classList.remove("hidden");
        if (processoSelectContainer) processoSelectContainer.classList.add("hidden");

        if (processoInputVisible) { processoInputVisible.disabled = false; processoInputVisible.classList.remove("bg-gray-100"); }

        if (subprocessoField) { subprocessoField.disabled = true; subprocessoField.classList.add("bg-gray-100", "text-gray-500"); subprocessoField.classList.remove("bg-white"); }

        if (parentField) { parentField.value = ""; parentField.disabled = true; }

        limparCampos();
    }

    function setModeSubprocesso() {
        if (!rbProcesso || !rbSubprocesso) return;

        rbProcesso.checked = false;
        rbSubprocesso.checked = true;

        if (lblProcesso) lblProcesso.classList.add("text-blue-700");
        if (lblProcesso) lblProcesso.classList.remove("text-gray-400");
        if (lblSubprocesso) lblSubprocesso.classList.add("text-blue-700");
        if (lblSubprocesso) lblSubprocesso.classList.remove("text-gray-400");

        if (lblCampoProcesso) lblCampoProcesso.classList.add("text-blue-700");
        if (lblCampoProcesso) lblCampoProcesso.classList.remove("text-gray-400");
        if (lblCampoSubprocesso) lblCampoSubprocesso.classList.add("text-blue-700");
        if (lblCampoSubprocesso) lblCampoSubprocesso.classList.remove("text-gray-400");

        if (processoInputVisible) processoInputVisible.classList.add("hidden");
        if (processoSelectContainer) processoSelectContainer.classList.remove("hidden");

        if (subprocessoField) { subprocessoField.disabled = false; subprocessoField.classList.remove("bg-gray-100", "text-gray-500"); subprocessoField.classList.add("bg-white"); }

        if (parentField) parentField.disabled = false;

        limparCampos();

        if (processoSelectVisible) {
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
                    if (parentField && parentField.value) {
                        processoSelectVisible.value = parentField.value;
                    }
                }).catch(e => console.error("Erro ao carregar processos pai:", e));
        }

        if (!selectListenerAdded && processoSelectVisible) {
            processoSelectVisible.addEventListener("change", function () {
                if (parentField) parentField.value = this.value;
            });
            selectListenerAdded = true;
        }
    }

    if (rbProcesso && rbSubprocesso) {
        rbProcesso.addEventListener("change", () => setModeProcesso());
        rbSubprocesso.addEventListener("change", () => setModeSubprocesso());
    }

    try {
        if (parentField && parentField.value) {
            setModeSubprocesso();
            if (processoSelectVisible) processoSelectVisible.value = parentField.value;
        } else {
            setModeProcesso();
        }
    } catch (e) {
        // ignore if elements missing in some contexts
    }

    // =====================================================================
    // 🔵 MODELO DE PROCESSO / NORMA – atualizações informativas
    // =====================================================================
    const modeloSelect = safeGet("id_modelagem_processo");
    const temaModelo = safeGet("tema_modelo");
    const versaoModelo = safeGet("versao_modelo");
    const emitenteModelo = safeGet("emitente_modelo");
    const sistemaModelo = safeGet("sistema_modelo");
    const vigenciaModelo = safeGet("vigencia_modelo");

    function formatarDataISO_para_BR(iso) {
        if (!iso) return "";
        const partes = iso.split("-");
        return `${partes[2]}/${partes[1]}/${partes[0]}`;
    }
    function formatarVersao(v) { if (!v) return ""; return v.toString().padStart(2, "0"); }

    if (modeloSelect) {
        modeloSelect.addEventListener("change", function () {
            const opt = this.options[this.selectedIndex];
            if (!opt || opt.value === "") {
                if (temaModelo) temaModelo.value = "";
                if (versaoModelo) versaoModelo.value = "";
                if (emitenteModelo) emitenteModelo.value = "";
                if (sistemaModelo) sistemaModelo.value = "";
                if (vigenciaModelo) vigenciaModelo.value = "";
                return;
            }
            if (temaModelo) temaModelo.value = opt.dataset.tema || "";
            if (versaoModelo) versaoModelo.value = formatarVersao(opt.dataset.versao);
            if (emitenteModelo) emitenteModelo.value = opt.dataset.emitente || "";
            if (sistemaModelo) sistemaModelo.value = opt.dataset.sistema || "";
            if (vigenciaModelo) vigenciaModelo.value = formatarDataISO_para_BR(opt.dataset.vigencia);
        });
    }

    const normaSelect = safeGet("norma_procedimento");
    const temaNorma = safeGet("tema_norma");
    const versaoNorma = safeGet("versao_norma");
    const emitenteNorma = safeGet("emitente_norma");
    const sistemaNorma = safeGet("sistema_norma");
    const vigenciaNorma = safeGet("vigencia_norma");

    if (normaSelect) {
        normaSelect.addEventListener("change", function () {
            const opt = this.options[this.selectedIndex];
            if (!opt || opt.value === "") {
                if (temaNorma) temaNorma.value = "";
                if (versaoNorma) versaoNorma.value = "";
                if (emitenteNorma) emitenteNorma.value = "";
                if (sistemaNorma) sistemaNorma.value = "";
                if (vigenciaNorma) vigenciaNorma.value = "";
                return;
            }
            if (temaNorma) temaNorma.value = opt.dataset.tema || "";
            if (versaoNorma) versaoNorma.value = formatarVersao(opt.dataset.versao);
            if (emitenteNorma) emitenteNorma.value = opt.dataset.emitente || "";
            if (sistemaNorma) sistemaNorma.value = opt.dataset.sistema || "";
            if (vigenciaNorma) vigenciaNorma.value = formatarDataISO_para_BR(opt.dataset.vigencia);
        });
    }

    // =====================================================================
    // 🔵 TRIPLE FILTER: Classificação ↔ Macro1 ↔ Macro2
    // =====================================================================
    (function tripleFilter() {
        const selClass = safeGet("id_classificacao");
        const selMacro1 = safeGet("id_macroprocesso_nivel1");
        const selMacro2 = safeGet("id_macroprocesso_nivel2");

        if (!selClass || !selMacro1 || !selMacro2) return;

        // Endpoints
        const API_MACRO1_BY_CLASS = "/api/macroprocessos_por_classificacao/";
        const API_MACRO2_BY_MACRO1 = "/api/macro2_por_macro1/";
        const API_CLASS_BY_MACRO1 = "/api/classificacao_por_macro1/";
        const API_MACRO1_ALL = "/api/macro1_todos/";
        const API_MACRO2_ALL = "/api/macro2_todos/";

        // Cache
        let cacheMacro1 = null;
        let cacheMacro2 = null;

        function clearOptions(select) { while (select.options.length > 0) select.remove(0); }

        function addOptions(select, items, selectedValue = null) {
            const previous = selectedValue ?? select.value;
            clearOptions(select);
            const placeholder = document.createElement("option");
            placeholder.value = "";
            placeholder.textContent = "---------";
            select.appendChild(placeholder);
            items.forEach(item => {
                const opt = document.createElement("option");
                opt.value = item.id;
                opt.textContent = item.nome;
                select.appendChild(opt);
            });
            // PRESERVAÇÃO DA SELEÇÃO (se a opção ainda existe)
            if (previous && Array.from(select.options).some(o => o.value == previous)) {
                select.value = previous;
            } else {
                select.value = "";
            }
        }

        async function loadAllMacro1() {
            if (cacheMacro1) return cacheMacro1;
            const data = await safeFetchJson(API_MACRO1_ALL);
            cacheMacro1 = data.macro1 || [];
            return cacheMacro1;
        }
        async function loadAllMacro2() {
            if (cacheMacro2) return cacheMacro2;
            const data = await safeFetchJson(API_MACRO2_ALL);
            cacheMacro2 = data.macro2 || [];
            return cacheMacro2;
        }

        // CLASSIFICAÇÃO mudou -> filtra Macro1 e Macro2 (esquerda -> direita)
        selClass.addEventListener("change", async function () {
            const classId = this.value;
            if (!classId) {
                addOptions(selMacro1, await loadAllMacro1(), "");
                addOptions(selMacro2, await loadAllMacro2(), "");
                return;
            }
            const resp = await fetch(API_MACRO1_BY_CLASS + classId + "/");
            const data = await resp.json();
            addOptions(selMacro1, data.macroprocessos || []);
            const todosMacro2 = await loadAllMacro2();
            const macro1Ids = (data.macroprocessos || []).map(m => m.id);
            const filtrado = todosMacro2.filter(m => macro1Ids.includes(m.macroprocesso_nivel1_id));
            addOptions(selMacro2, filtrado || []);
        });

        // MACRO1 mudou -> filtra Macro2 e harmoniza Classificação (esquerda -> direita)
        selMacro1.addEventListener("change", async function () {
            const macro1Id = this.value;
            if (!macro1Id) {
                addOptions(selMacro2, await loadAllMacro2(), "");
                return;
            }
            const respC = await fetch(API_CLASS_BY_MACRO1 + macro1Id + "/");
            const dataC = await respC.json();
            if (dataC.classificacao_id) selClass.value = String(dataC.classificacao_id);
            // dispara filtro da classificação (que por sua vez preenche macro1/macro2 coerentemente)
            selClass.dispatchEvent(new Event("change"));
            // carrega Macro2 deste Macro1 explicitamente (garante opção correta)
            const resp2 = await fetch(API_MACRO2_BY_MACRO1 + macro1Id + "/");
            const data2 = await resp2.json();
            addOptions(selMacro2, data2.macro2 || []);
        });

        // MACRO2 mudou -> comportamento especial (reverse-update controlado)
        selMacro2.addEventListener("change", async function () {
            const macro2Id = this.value;
            if (!macro2Id) {
                // usuário limpou Macro2 -> não faz mais nada (dependentes à direita não existem)
                return;
            }

            if (!ENABLE_REVERSE_UPDATE) {
                // Apenas preserva a seleção e NÃO causa alterações à direita(esquerda já será atualizada somente se usuário limpar)
                return;
            }

            // Se reverse-update ativado: só executa se TODOS os campos à esquerda estiverem vazios
            const classEmpty = selClass.value === "";
            const macro1Empty = selMacro1.value === "";

            if (!classEmpty || !macro1Empty) {
                // Há valores à esquerda — evitar loops
                return;
            }

            try {
                const resp = await fetch("/api/macro1_e_classificacao_por_macro2/" + macro2Id + "/");
                const data = await resp.json();

                if (data.macroprocesso_nivel1?.id) selMacro1.value = String(data.macroprocesso_nivel1.id);
                if (data.classificacao?.id) selClass.value = String(data.classificacao.id);

                // disparamos o evento de classificação para refiltrar (se necessário)
                selClass.dispatchEvent(new Event("change"));
            } catch (e) {
                console.error("Erro no reverse-update:", e);
            }
        });

        // Inicialização — carrega todos (preserva seleção atual se houver)
        (async function init() {
            addOptions(selMacro1, await loadAllMacro1());
            addOptions(selMacro2, await loadAllMacro2());
        })();

    })(); // fim tripleFilter

}); // fim DOMContentLoaded
