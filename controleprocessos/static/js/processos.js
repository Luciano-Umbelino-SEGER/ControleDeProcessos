// ===============================
// processos.js – VERSÃO FINAL AJUSTADA
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
        })
        .then(r => {
            if (!r.ok) throw new Error("HTTP " + r.status);
            return r.json();
        });
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

    // ===============================
    // Funções auxiliares
    // ===============================
    function isTipoProcesso() {
    if (rbProcesso && rbProcesso.checked) return true;
        return !parentIdFromServer;
    }

    function isTipoSubprocesso() {
        if (rbSubprocesso && rbSubprocesso.checked) return true;
        return !!parentIdFromServer;
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
    // INCLUSÃO
    // ===============================
    function setModeProcesso_inclusao() {
        aplicarEstadoVisualLabels(false);

        if (processoInputVisible) {
            processoInputVisible.classList.remove("hidden");
            processoInputVisible.disabled = false;
            processoInputVisible.classList.add("bg-white");
            processoInputVisible.classList.remove("bg-gray-100");
        }

        if (processoSelectContainer) processoSelectContainer.classList.add("hidden");

        if (subprocessoInputVisible) {
            subprocessoInputVisible.disabled = true;
            subprocessoInputVisible.classList.add("bg-gray-100");
            subprocessoInputVisible.value = "";
        }

        if (parentField) {
            parentField.disabled = true;
            parentField.value = "";
        }

        limparVisiveis();
    }

    async function setModeSubprocesso_inclusao() {
        aplicarEstadoVisualLabels(true);

        if (processoInputVisible) processoInputVisible.classList.add("hidden");
        if (processoSelectContainer) processoSelectContainer.classList.remove("hidden");

        if (subprocessoInputVisible) {
            subprocessoInputVisible.disabled = false;
            subprocessoInputVisible.classList.add("bg-white");
            subprocessoInputVisible.classList.remove("bg-gray-100");
            subprocessoInputVisible.value = "";
        }

        if (parentField) parentField.disabled = false;

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

        limparVisiveis();

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
                if (processoInputVisible) processoInputVisible.classList.add("hidden");
                if (processoSelectContainer) processoSelectContainer.classList.remove("hidden");

                const processos = await carregarProcessosPai();

                if (processoSelectVisible) {
                    processoSelectVisible.innerHTML = `<option value="">---------</option>`;
                    processos.forEach(p => {
                        const opt = document.createElement("option");
                        opt.value = p.id;
                        opt.textContent = p.nome;
                        processoSelectVisible.appendChild(opt);
                    });

                    processoSelectVisible.value = parentIdFromServer;
                    processoSelectVisible.disabled = !formIsEditable();
                }

                if (subprocessoInputVisible) {
                    subprocessoInputVisible.disabled = !formIsEditable();
                    subprocessoInputVisible.value = nomeRegistro;
                }

                if (parentField) parentField.value = parentIdFromServer;

                if (!selectListenerAdded && processoSelectVisible) {
                    processoSelectVisible.addEventListener("change", () => {
                        parentField.value = processoSelectVisible.value;
                    });
                    selectListenerAdded = true;
                }
            }
            else {
                if (processoSelectContainer) processoSelectContainer.classList.add("hidden");
                if (processoInputVisible) {
                    processoInputVisible.classList.remove("hidden");
                    processoInputVisible.disabled = true;
                }

                const processos = await carregarProcessosPai();
                const parentObj = processos.find(p => String(p.id) === String(parentIdFromServer));
                if (processoInputVisible) processoInputVisible.value = parentObj ? parentObj.nome : "";

                if (subprocessoInputVisible) {
                    subprocessoInputVisible.disabled = true;
                    subprocessoInputVisible.value = nomeRegistro;
                }

                if (parentField) {
                    parentField.value = parentIdFromServer;
                    parentField.disabled = true;
                }
            }

        } else {
            if (rbProcesso) rbProcesso.checked = true;
            aplicarEstadoVisualLabels(false);

            if (processoSelectContainer) processoSelectContainer.classList.add("hidden");
            if (processoInputVisible) {
                processoInputVisible.classList.remove("hidden");
                processoInputVisible.disabled = !formIsEditable();
                processoInputVisible.value = nomeRegistro;
            }

            if (subprocessoInputVisible) {
                subprocessoInputVisible.disabled = true;
                subprocessoInputVisible.value = "";
            }

            if (parentField) {
                parentField.value = "";
                parentField.disabled = true;
            }
        }
    }

    // ===============================
    // Inicialização geral
    // ===============================
    (async function init() {
        if (modoInclusao) {
            if (rbProcesso) rbProcesso.disabled = false;
            if (rbSubprocesso) rbSubprocesso.disabled = false;

            if (rbProcesso) rbProcesso.addEventListener("change", () => rbProcesso.checked && setModeProcesso_inclusao());
            if (rbSubprocesso) rbSubprocesso.addEventListener("change", () => rbSubprocesso.checked && setModeSubprocesso_inclusao());

            if (rbSubprocesso && rbSubprocesso.checked) await setModeSubprocesso_inclusao();
            else setModeProcesso_inclusao();
        }
        else {
            await inicializacaoNaoInclusao();
        }
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

            if (hiddenNomeField) hiddenNomeField.value = nomeValor;
            if (parentField) parentField.value = parentValor;

            if (!nomeValor) {
                alert("Preencha o nome do Processo/Subprocesso antes de enviar.");
                ev.preventDefault();
                if (isTipoSubprocesso() && subprocessoInputVisible) {
                    subprocessoInputVisible.focus();
                } else if (processoInputVisible) {
                    processoInputVisible.focus();
                }
            }
        });
    })();

});


