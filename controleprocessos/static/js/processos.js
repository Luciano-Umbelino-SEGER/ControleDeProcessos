// ===============================
// processos.js – VERSÃO FINAL 100% REVISADA
// ===============================

document.addEventListener("DOMContentLoaded", function () {

    // =========================
    // Config / modos
    // =========================
    const MODO = (typeof window !== "undefined" && window.MODO) ? window.MODO : {
        inclusao: document.body.dataset.modoInclusao === "true",
        edicao: document.body.dataset.modoEdicao === "true",
        visualizacao: document.body.dataset.modoVisualizacao === "true",
        exclusao: document.body.dataset.modoExclusao === "true",
        parentId: document.body.dataset.parentId || ""
    };

    const modoInclusao = !!MODO.inclusao;
    const modoEdicao = !!MODO.edicao;
    const modoVisualizacao = !!MODO.visualizacao;
    const modoExclusao = !!MODO.exclusao;
    const parentIdFromServer = (MODO.parentId || "").toString();

    const ENABLE_REVERSE_UPDATE = false;

    function safeGet(id) {
        try { return document.getElementById(id); } catch { return null; }
    }

    function safeFetchJson(url) {
        return fetch(url, {
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
        }).then(r => r.json());
    }

    // =====================================================================
    // Elementos principais
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

    const subprocessoInputVisible = safeGet("subprocesso_input_visible");

    // campos backend
    const parentField = safeGet("id_parent");
    const hiddenNomeField = safeGet("id_nome");
    const hiddenTipoProcField = document.querySelector('input[name="tipo_processo"]');

    // ===============================
    // Funções auxiliares
    // ===============================
    function isTipoProcesso() {
        return (
            (rbProcesso && rbProcesso.checked) ||
            (hiddenTipoProcField && hiddenTipoProcField.value === "processo")
        );
    }

    function isTipoSubprocesso() {
        return (
            (rbSubprocesso && rbSubprocesso.checked) ||
            (hiddenTipoProcField && hiddenTipoProcField.value === "subprocesso")
        );
    }

    const formIsEditable = () => modoInclusao || modoEdicao;

    let selectListenerAdded = false;

    function limparVisiveis() {
        if (processoInputVisible) processoInputVisible.value = "";
        if (subprocessoInputVisible) subprocessoInputVisible.value = "";
        if (hiddenNomeField) hiddenNomeField.value = "";
        if (parentField) parentField.value = "";
        if (processoSelectVisible) processoSelectVisible.selectedIndex = 0;
    }

    function carregarProcessosPai() {
        return safeFetchJson("/api/processos_pai/")
            .then(d => d.processos_pai || [])
            .catch(() => []);
    }

    function aplicarEstadoVisualLabels(isSub) {
        if (lblProcesso) {
            lblProcesso.classList.toggle("text-blue-700", !isSub);
            lblProcesso.classList.toggle("text-gray-400", isSub);
        }
        if (lblSubprocesso) {
            lblSubprocesso.classList.toggle("text-blue-700", isSub);
            lblSubprocesso.classList.toggle("text-gray-400", !isSub);
        }
        if (lblCampoProcesso) {
            lblCampoProcesso.classList.add("text-blue-700");
            lblCampoProcesso.classList.remove("text-gray-400");
        }
        if (lblCampoSubprocesso) {
            lblCampoSubprocesso.classList.toggle("text-blue-700", isSub);
            lblCampoSubprocesso.classList.toggle("text-gray-400", !isSub);
        }
    }

    // ===============================
    // INCLUSÃO – mudar modos
    // ===============================
    function setModeProcesso_inclusao() {
        aplicarEstadoVisualLabels(false);

        processoInputVisible.classList.remove("hidden");
        processoSelectContainer.classList.add("hidden");

        processoInputVisible.disabled = false;
        processoInputVisible.classList.add("bg-white");
        processoInputVisible.classList.remove("bg-gray-100");

        subprocessoInputVisible.disabled = true;
        subprocessoInputVisible.classList.add("bg-gray-100");
        subprocessoInputVisible.value = "";

        parentField.disabled = true;
        parentField.value = "";

        limparVisiveis();
    }

    async function setModeSubprocesso_inclusao() {
        aplicarEstadoVisualLabels(true);

        processoInputVisible.classList.add("hidden");
        processoSelectContainer.classList.remove("hidden");

        subprocessoInputVisible.disabled = false;
        subprocessoInputVisible.classList.add("bg-white");
        subprocessoInputVisible.classList.remove("bg-gray-100");
        subprocessoInputVisible.value = "";

        parentField.disabled = false;

        limparVisiveis();

        if (processoSelectVisible) {
            const processos = await carregarProcessosPai();
            processoSelectVisible.innerHTML = `<option value="">---------</option>`;
            processos.forEach(p => {
                const opt = document.createElement("option");
                opt.value = p.id;
                opt.textContent = p.nome;
                processoSelectVisible.appendChild(opt);
            });
        }

        if (!selectListenerAdded && processoSelectVisible) {
            processoSelectVisible.addEventListener("change", function () {
                parentField.value = this.value;
            });
            selectListenerAdded = true;
        }
    }

    // ===============================
    // EDIÇÃO / VISUALIZAÇÃO / EXCLUSÃO
    // ===============================
    async function inicializacaoNaoInclusao() {

        if (rbProcesso) rbProcesso.disabled = true;
        if (rbSubprocesso) rbSubprocesso.disabled = true;

        const isSub = !!parentIdFromServer;
        const nomeRegistro = hiddenNomeField?.value || "";

        if (isSub) {
            if (rbSubprocesso) rbSubprocesso.checked = true;
            aplicarEstadoVisualLabels(true);

            if (modoEdicao) {
                processoInputVisible.classList.add("hidden");
                processoSelectContainer.classList.remove("hidden");

                const processos = await carregarProcessosPai();

                processoSelectVisible.innerHTML = `<option value="">---------</option>`;
                processos.forEach(p => {
                    const opt = document.createElement("option");
                    opt.value = p.id;
                    opt.textContent = p.nome;
                    processoSelectVisible.appendChild(opt);
                });

                processoSelectVisible.value = parentIdFromServer;
                processoSelectVisible.disabled = !formIsEditable();

                subprocessoInputVisible.disabled = !formIsEditable();
                subprocessoInputVisible.value = nomeRegistro;

                parentField.value = processoSelectVisible.value;

                if (!selectListenerAdded) {
                    processoSelectVisible.addEventListener("change", () => {
                        parentField.value = processoSelectVisible.value;
                    });
                    selectListenerAdded = true;
                }
            }
            else {
                processoSelectContainer.classList.add("hidden");
                processoInputVisible.classList.remove("hidden");
                processoInputVisible.disabled = true;

                const processos = await carregarProcessosPai();
                const parentObj = processos.find(p => String(p.id) === String(parentIdFromServer));
                processoInputVisible.value = parentObj ? parentObj.nome : "";

                subprocessoInputVisible.disabled = true;
                subprocessoInputVisible.value = nomeRegistro;

                parentField.value = parentIdFromServer;
                parentField.disabled = true;
            }

        } else {
            if (rbProcesso) rbProcesso.checked = true;
            aplicarEstadoVisualLabels(false);

            processoSelectContainer.classList.add("hidden");
            processoInputVisible.classList.remove("hidden");

            processoInputVisible.disabled = !formIsEditable();
            processoInputVisible.value = nomeRegistro;

            subprocessoInputVisible.disabled = true;
            subprocessoInputVisible.value = "";

            parentField.value = "";
            parentField.disabled = true;
        }
    }

    // ===============================
    // Inicialização geral
    // ===============================
    (async function init() {
        if (modoInclusao) {
            rbProcesso.disabled = false;
            rbSubprocesso.disabled = false;

            rbProcesso.addEventListener("change", () => rbProcesso.checked && setModeProcesso_inclusao());
            rbSubprocesso.addEventListener("change", () => rbSubprocesso.checked && setModeSubprocesso_inclusao());

            if (rbSubprocesso.checked) await setModeSubprocesso_inclusao();
            else setModeProcesso_inclusao();
        }
        else {
            await inicializacaoNaoInclusao();

            // 🔥 HIDRATAÇÃO (somente fora da inclusão)
            if (typeof MODELOS_HIDRATADOS !== "undefined") {
                hidratarModelos();
                hidratarNormas();
            }

            // ⛔ BLOQUEIO FINAL — somente visualização / exclusão
            if (modoVisualizacao || modoExclusao) {

                // desabilita todos os selects de modelos e normas
                document
                    .querySelectorAll('#modelos_container select, #normas_container select')
                    .forEach(el => el.disabled = true);

                // esconde botões + e − dos blocos dinâmicos
                document
                    .querySelectorAll('[data-action="add"], [data-action="remove"]')
                    .forEach(btn => btn.style.display = "none");
            }

            // 🎨 Ajuste visual dos blocos extras em visualização / exclusão
            if (modoVisualizacao || modoExclusao) {
                document
                    .querySelectorAll(
                        '#modelos_container input, #modelos_container select,' +
                        '#normas_container input, #normas_container select'
                    )
                    .forEach(el => {
                        el.classList.add("bg-gray-100", "opacity-70", "cursor-not-allowed");
                    });
            }

        }
    })();

    // ===============================
    // MODELAGEM E NORMA — não alterado
    // ===============================
    const modeloSelect = safeGet("id_modelagem_processo");
    const temaModelo = safeGet("tema_modelo");
    const versaoModelo = safeGet("versao_modelo");
    const emitenteModelo = safeGet("emitente_modelo");
    const sistemaModelo = safeGet("sistema_modelo");
    const vigenciaModelo = safeGet("vigencia_modelo");

    function formatarDataISO_para_BR(iso) {
        if (!iso) return "";
        const [a,m,d] = iso.split("-");
        return `${d}/${m}/${a}`;
    }

    function formatarVersao(v) { return v ? String(v).padStart(2,"0") : ""; }

    if (modeloSelect) {
        modeloSelect.addEventListener("change", function() {
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
    }

    // NORMA
    const normaSelect = safeGet("norma_procedimento");
    const temaNorma = safeGet("tema_norma");
    const versaoNorma = safeGet("versao_norma");
    const emitenteNorma = safeGet("emitente_norma");
    const sistemaNorma = safeGet("sistema_norma");
    const vigenciaNorma = safeGet("vigencia_norma");

    if (normaSelect) {
        normaSelect.addEventListener("change", function() {
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
    }

    // ===============================
    // Triple Filter
    // ===============================
    (function tripleFilter() {
        const selClass = safeGet("id_classificacao");
        const selMacro1 = safeGet("id_macroprocesso_nivel1");
        const selMacro2 = safeGet("id_macroprocesso_nivel2");

        if (!selClass || !selMacro1 || !selMacro2) return;

        const API_MACRO1_BY_CLASS = "/api/macroprocessos_por_classificacao/";
        const API_MACRO2_BY_MACRO1 = "/api/macro2_por_macro1/";
        const API_CLASS_BY_MACRO1 = "/api/classificacao_por_macro1/";
        const API_MACRO1_ALL = "/api/macro1_todos/";
        const API_MACRO2_ALL = "/api/macro2_todos/";

        let cacheMacro1 = null;
        let cacheMacro2 = null;

        function clearOptions(select) {
            while (select.options.length) select.remove(0);
        }

        function addOptions(select, items, selectedValue=null) {
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

            if (previous && Array.from(select.options).some(o => o.value == previous)) {
                select.value = previous;
            }
        }

        async function loadAllMacro1() {
            if (cacheMacro1) return cacheMacro1;
            const d = await safeFetchJson(API_MACRO1_ALL);
            cacheMacro1 = d.macro1 || [];
            return cacheMacro1;
        }
        async function loadAllMacro2() {
            if (cacheMacro2) return cacheMacro2;
            const d = await safeFetchJson(API_MACRO2_ALL);
            cacheMacro2 = d.macro2 || [];
            return cacheMacro2;
        }

        selClass.addEventListener("change", async function () {
            const classId = this.value;

            if (!classId) {
                addOptions(selMacro1, await loadAllMacro1());
                addOptions(selMacro2, await loadAllMacro2());
                return;
            }

            const resp = await fetch(API_MACRO1_BY_CLASS + classId + "/");
            const data = await resp.json();

            addOptions(selMacro1, data.macroprocessos || []);

            const all2 = await loadAllMacro2();
            const ids = (data.macroprocessos || []).map(m => m.id);
            const filtrado = all2.filter(m => ids.includes(m.macroprocesso_nivel1_id));

            addOptions(selMacro2, filtrado);
        });

        selMacro1.addEventListener("change", async function () {
            const macro1Id = this.value;

            if (!macro1Id) {
                addOptions(selMacro2, await loadAllMacro2());
                return;
            }

            const respC = await fetch(API_CLASS_BY_MACRO1 + macro1Id + "/");
            const dataC = await respC.json();

            if (dataC.classificacao_id) {
                selClass.value = String(dataC.classificacao_id);
            }

            selClass.dispatchEvent(new Event("change"));

            const resp2 = await fetch(API_MACRO2_BY_MACRO1 + macro1Id + "/");
            const data2 = await resp2.json();

            addOptions(selMacro2, data2.macro2 || []);
        });

        selMacro2.addEventListener("change", async function () {
            const macro2Id = this.value;

            if (!macro2Id) return;
            if (!ENABLE_REVERSE_UPDATE) return;

            try {
                const resp = await fetch("/api/macro1_e_classificacao_por_macro2/" + macro2Id + "/");
                const data = await resp.json();

                if (data.macroprocesso_nivel1?.id) {
                    selMacro1.value = String(data.macroprocesso_nivel1.id);
                }
                if (data.classificacao?.id) {
                    selClass.value = String(data.classificacao.id);
                }

                selClass.dispatchEvent(new Event("change"));
            }
            catch {}
        });

        // inicialização
        (async function initTF() {
            addOptions(selMacro1, await loadAllMacro1());
            addOptions(selMacro2, await loadAllMacro2());
        })();

    })();

    // ===============================
    // Antes do submit – sincronizar nome e parent
    // ===============================
    (function syncBeforeSubmit() {
        const form = document.getElementById("form-processo");
        if (!form) return;

        form.addEventListener("submit", function (ev) {
            let nomeValor = "";
            let parentValor = "";

            if (isTipoSubprocesso()) {
                nomeValor = (subprocessoInputVisible?.value || "").trim();
                parentValor = processoSelectVisible?.value || "";
            }
            else if (isTipoProcesso()) {
                nomeValor = (processoInputVisible?.value || "").trim();
                parentValor = "";
            }

            hiddenNomeField.value = nomeValor;
            parentField.value = parentValor;

            if (!nomeValor) {
                if (isTipoSubprocesso()) {
                    subprocessoInputVisible.classList.add('border-red-500','ring-2','ring-red-300');
                    subprocessoInputVisible.focus();
                } else {
                    processoInputVisible.classList.add('border-red-500','ring-2','ring-red-300');
                    processoInputVisible.focus();
                }
                alert("Preencha o nome antes de enviar.");
                ev.preventDefault();
            }
        });
    })();

    // ===============================
    // Destaque de erros
    // ===============================
    (function destaqueCamposErro() {
        document.querySelectorAll('.alert ul li strong').forEach(err => {
            const fieldName = err.textContent.replace(':', '').trim();
            const field = document.querySelector(`[name="${fieldName}"]`);

            if (field) {
                field.classList.add('border-red-500', 'ring-2', 'ring-red-300');

                if (fieldName === 'nome') {
                    if (isTipoSubprocesso()) {
                        subprocessoInputVisible.classList.add('border-red-500','ring-2','ring-red-300');
                    } else {
                        processoInputVisible.classList.add('border-red-500','ring-2','ring-red-300');
                    }
                }

                if (fieldName === 'parent') {
                    processoSelectVisible.classList.add('border-red-500','ring-2','ring-red-300');
                }
            }
        });
    })();

});

// ==================================================
// HIDRATAÇÃO DE DOCUMENTOS (1 → N)
// ==================================================

function hidratarSelect(selectEl, dados) {
    if (!selectEl || !dados) return;
    selectEl.value = dados.id;
    selectEl.dispatchEvent(new Event("change", { bubbles: true }));
}

function preencherCamposModelo(block, dados) {
    block.querySelector('[id^="tema_modelo"]').value = dados.tema || "";
    block.querySelector('[id^="versao_modelo"]').value = dados.versao || "";
    block.querySelector('[id^="emitente_modelo"]').value = dados.emitente || "";
    block.querySelector('[id^="sistema_modelo"]').value = dados.sistema || "";
    block.querySelector('[id^="vigencia_modelo"]').value = dados.vigencia || "";
}

function preencherCamposNorma(block, dados) {
    block.querySelector('[id^="tema_norma"]').value = dados.tema || "";
    block.querySelector('[id^="versao_norma"]').value = dados.versao || "";
    block.querySelector('[id^="emitente_norma"]').value = dados.emitente || "";
    block.querySelector('[id^="sistema_norma"]').value = dados.sistema || "";
    block.querySelector('[id^="vigencia_norma"]').value = dados.vigencia || "";
}

function hidratarModelos() {
    if (!Array.isArray(MODELOS_HIDRATADOS) || MODELOS_HIDRATADOS.length === 0) return;

    const container = document.getElementById("modelos_container");
    const baseBlock = container.querySelector('.modelo-block[data-uid="base"]');

    // 🔹 BLOCO BASE
    hidratarSelect(
        baseBlock.querySelector('select[name="modelagem_processo"]'),
        MODELOS_HIDRATADOS[0]
    );
    preencherCamposModelo(baseBlock, MODELOS_HIDRATADOS[0]);

    // 🔹 BLOCOS EXTRAS (sem botão +)
    MODELOS_HIDRATADOS.slice(1).forEach((dados, idx) => {
        const uid = `hidratado_${idx}_${Date.now()}`;
        const novo = clonarTemplate("template-modelo", container, uid);
        if (!novo) return;

        const select = novo.querySelector('select[name="modelagem_processo_extra[]"]');
        hidratarSelect(select, dados);
        preencherCamposModelo(novo, dados);
    });
}

function hidratarNormas() {
    if (!Array.isArray(NORMAS_HIDRATADAS) || NORMAS_HIDRATADAS.length === 0) return;

    const container = document.getElementById("normas_container");
    const baseBlock = container.querySelector('.norma-block[data-uid="base"]');

    // 🔹 BLOCO BASE
    hidratarSelect(
        baseBlock.querySelector('select[name="norma_procedimento"]'),
        NORMAS_HIDRATADAS[0]
    );
    preencherCamposNorma(baseBlock, NORMAS_HIDRATADAS[0]);

    // 🔹 BLOCOS EXTRAS
    NORMAS_HIDRATADAS.slice(1).forEach((dados, idx) => {
        const uid = `hidratado_${idx}_${Date.now()}`;
        const novo = clonarTemplate("template-norma", container, uid);
        if (!novo) return;

        const select = novo.querySelector('select[name="norma_procedimento_extra[]"]');
        hidratarSelect(select, dados);
        preencherCamposNorma(novo, dados);
    });
}

function clonarTemplate(templateId, container, uid) {
    const tpl = document.getElementById(templateId);
    if (!tpl) return null;

    const html = tpl.innerHTML.replaceAll("__UID__", uid);
    const wrapper = document.createElement("div");
    wrapper.innerHTML = html.trim();

    const bloco = wrapper.firstElementChild;
    if (bloco) container.appendChild(bloco);

    return bloco;
}


