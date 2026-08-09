// ===========================================
// processos.js – VERSÃO FINAL 100% REVISADA
// ===========================================
document.addEventListener("DOMContentLoaded", function () {

    // =========================
    // Config / modos (FONTE ÚNICA)
    // =========================
    const MODO = (typeof window !== "undefined" && window.MODO)
        ? window.MODO
        : {
            inclusao: document.body.dataset.modoInclusao === "true",
            edicao: document.body.dataset.modoEdicao === "true",
            visualizacao: document.body.dataset.modoVisualizacao === "true",
            exclusao: document.body.dataset.modoExclusao === "true",
            parentId: document.body.dataset.parentId || ""
        };

    // Flags normalizadas
    const modoInclusao = Boolean(MODO.inclusao);
    const modoEdicao = Boolean(MODO.edicao);
    const modoVisualizacao = Boolean(MODO.visualizacao);
    const modoExclusao = Boolean(MODO.exclusao);

    // 👉 VERDADE ÚNICA (ainda não usada em todo lugar)
    window.modoBloqueado = modoVisualizacao || modoExclusao;

    // Outros
    const parentIdFromServer = (MODO.parentId || "").toString();

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
    const hiddenTipoProcField = document.querySelector('input[name="tipo_processo_fake"]');

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
        // NÃO limpar o parent.
        // O valor pode ter vindo de um POST inválido e será reutilizado.
        //if (parentField) parentField.value = "";
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

        if (!hiddenNomeField?.value) {
            limparVisiveis();
        }
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

        if (!hiddenNomeField?.value) {
            limparVisiveis();
        }

        // Load parent processes and restore the selected parent after an invalid POST
        if (processoSelectVisible) {

            const processos = await carregarProcessosPai();

            processoSelectVisible.innerHTML = `<option value="">---------</option>`;

            processos.forEach(p => {
                const opt = document.createElement("option");
                opt.value = p.id;
                opt.textContent = p.nome;
                processoSelectVisible.appendChild(opt);
            });

            // Restore the parent process sent in the POST
            if (parentField?.value) {

                const parentId = parentField.value;

                const parentOption = Array.from(
                    processoSelectVisible.options
                ).find(
                    option => String(option.value) === String(parentId)
                );

                if (parentOption) {

                    processoSelectVisible.value = parentId;

                    // Synchronize Select2, when initialized
                    if (
                        window.$ &&
                        $(processoSelectVisible).hasClass("select2-hidden-accessible")
                    ) {
                        $(processoSelectVisible).trigger("change");
                    }
                }
            }
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
            if (typeof NORMAS_HIDRATADAS !== "undefined") {
                hidratarNormas();
            }

            // 🎨 Ajuste visual dos blocos extras em visualização / exclusão
            if (modoVisualizacao || modoExclusao) {
                document
                    .querySelectorAll(
                        '#normas_container input, #normas_container select'
                    )
                    .forEach(el => {
                        el.classList.add("bg-gray-100", "opacity-70", "cursor-not-allowed");
                    });
            }

        }

        // 🔒 Bloqueio FINAL após toda a inicialização
        setTimeout(() => {
            bloquearBotoesAdicionarRemover();
        }, 0);

    })();

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
            versaoNorma.value = formatarVersao(opt.dataset.versao);
            emitenteNorma.value = opt.dataset.emitente || "";
            sistemaNorma.value = opt.dataset.sistema || "";
            vigenciaNorma.value = formatarDataISO_para_BR(opt.dataset.vigencia);
        });
    }

    // ============================================
    // Antes do submit – sincronizar nome e parent
    // ============================================
    (function syncBeforeSubmit() {
        const form = document.getElementById("form-processo") || document.getElementById("form-processomapear");
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

        });
    })();

    // ===============================
    // Destaque de erros
    // ===============================
    (function destaqueCamposErro() {
        document.querySelectorAll('.alert ul li strong').forEach(err => {
            const fieldName = err.dataset.field || err.textContent.replace(':', '').trim();
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

// ==========================================
// UTILITÁRIOS DE FORMATAÇÃO
// ==========================================
function formatarDataISO_para_BR(iso) {
    if (!iso) return "";
    const [a, m, d] = iso.split("-");
    return `${d}/${m}/${a}`;
}

function formatarVersao(v) {
    return v ? String(v).padStart(2, "0") : "";
}

// ==========================================
// VISUALIZAR NORMA DE PROCEDIMENTO
// ==========================================
document.addEventListener("click", function (e) {
    const botao = e.target.closest('button[data-action="visualizar"]');
    if (!botao) return;

    const bloco = botao.closest('.modelo-block, .norma-block');
    if (!bloco) return;

    const select = bloco.querySelector("select");
    if (!select) return;

    const opt = select.options[select.selectedIndex];
    const url = opt?.dataset?.url;

    if (!url) {
        console.warn("⚠️ Nenhuma URL encontrada para visualização");
        return;
    }

    const titulo = bloco.classList.contains("modelo-block")
        ? "Modelo de Processo"
        : "Norma de Procedimento";

    abrirModalDocumento(url, titulo);
});

// ==================================================
// HIDRATAÇÃO DE DOCUMENTOS (1 → N)
// ==================================================
function hidratarSelect(selectEl, dados) {

    if (!selectEl || !dados) return;
    selectEl.value = dados.id;
    selectEl.dispatchEvent(new Event("change", { bubbles: true }));
}

function preencherCamposNorma(block, dados) {

    if (!block || !dados) return;

    const setValue = (selector, value) => {
        const campo = block.querySelector(selector);
        if (campo) {
            campo.value = value ?? "";
        }
    };

    setValue('[id^="codigo_norma"]', dados.codigo_norma);
    setValue('[id^="versao_norma"]', formatarVersao(dados.versao));
    setValue('[id^="emitente_norma"]', dados.emitente);
    setValue('[id^="sistema_norma"]', dados.sistema);
    setValue('[id^="vigencia_norma"]', formatarDataISO_para_BR(dados.vigencia));
}

// ==========================================
// HELPER — Atualiza bloco Alpine após clonagem
// ==========================================
function atualizarBlocoAlpine(bloco, select) {
    if (!window.Alpine || !bloco || !select) return;

    Alpine.nextTick(() => {
        const alpineData = Alpine.$data(bloco);
        if (alpineData && typeof alpineData.update === "function") {
            alpineData.update(select);
        }
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
    // ================================================
    // HIDRATAÇÃO — BLOCOS CLONADOS (NORMA)
    // Usa Alpine.nextTick para garantir x-data pronto
    // ================================================
    NORMAS_HIDRATADAS.slice(1).forEach((dados, idx) => {
        const uid = `hidratado_norma_${idx}_${Date.now()}`;
        const bloco = clonarTemplate("template-norma", container, uid);

        if (!bloco) return;

        const select = bloco.querySelector('select[name="norma_procedimento_extra[]"]');
        if (!select) return;

        // 1️⃣ Seleciona a norma correta
        select.value = dados.id;



        // 2️⃣ Aguarda Alpine finalizar completamente
        atualizarBlocoAlpine(bloco, select);

    });

}

function clonarTemplate(templateId, container, uid) {
    const tpl = document.getElementById(templateId);
    if (!tpl) return null;

    const html = tpl.innerHTML.replaceAll("__UID__", uid);
    const wrapper = document.createElement("div");
    wrapper.innerHTML = html.trim();

    const bloco = wrapper.firstElementChild;
    if (!bloco) return null;

    container.appendChild(bloco);

    // 🔥 PASSO ESSENCIAL — inicializar Alpine no bloco clonado
    if (window.Alpine) {
        window.Alpine.initTree(bloco);
    }

    return bloco;
}


// ==========================================
// BLOQUEIO FINAL — VISUALIZAÇÃO / EXCLUSÃO
// ==========================================
function bloquearBotoesAdicionarRemover() {
    if (!(window.MODO?.visualizacao || window.MODO?.exclusao)) return;

    window.BLOQUEIO_TOTAL_ATIVO = true;

    document
        .querySelectorAll('button[data-action="add"], button[data-action="remove"]')
        .forEach(btn => {
            btn.disabled = true;

            btn.classList.remove(
                'text-blue-600',
                'text-red-600',
                'hover:text-blue-800',
                'hover:text-red-800',
                'cursor-pointer'
            );

            btn.classList.add(
                'text-gray-400',
                'cursor-not-allowed'
            );

            btn.style.pointerEvents = 'none';
        });
}

// ==========================================
// CONTROLE DE ESTADO DOS BOTÕES + / -
// ==========================================

function atualizarEstadoBotoes(container) {
    if (!container) return;

    const baseBlock = container.querySelector('[data-uid="base"]');
    if (!baseBlock) return;

    const btnAdd = baseBlock.querySelector('button[data-action="add"]');
    const btnRemove = baseBlock.querySelector('button[data-action="remove"]');

    if (!btnAdd || !btnRemove) return;

    // todos os blocos (base + clonados)
    const blocks = Array.from(
        container.querySelectorAll('.modelo-block, .norma-block')
    );

    if (blocks.length === 0) {
        btnAdd.disabled = true;
        btnRemove.disabled = true;
        return;
    }

    const lastBlock = blocks[blocks.length - 1];
    const lastSelect = lastBlock.querySelector('select');

    const ultimoTemDocumento =
        lastSelect && lastSelect.value && lastSelect.value !== "";

    const existeAlgumDocumento = blocks.some(block => {
        const sel = block.querySelector('select');
        return sel && sel.value && sel.value !== "";
    });

    // regra FINAL
    btnAdd.disabled = !ultimoTemDocumento;
    btnRemove.disabled = !existeAlgumDocumento;
}

function addNorma(botao) {
    const container = document.getElementById("normas_container");
    if (!container) return;

    const uid = `norma_${Date.now()}`;
    clonarTemplate("template-norma", container, uid);

    atualizarEstadoBotoes(container);
}

function removeNorma(botao) {
    const container = document.getElementById("normas_container");
    if (!container) return;

    const blocos = Array.from(
        container.querySelectorAll('.norma-block')
    );

    // 🔹 só existe o bloco base → limpar
    if (blocos.length <= 1) {
        limparBlocoNorma(blocos[0]);

        // 🔥 AJUSTE ESSENCIAL
        atualizarEstadoBotoes(container);

        // 🔥 recalcula estado
        atualizarStatus();

        return;
    }

    // 🔹 remove o último bloco clonado
    const ultimo = blocos[blocos.length - 1];
    ultimo.remove();

    // 🔥 após remover, reavaliar botões
    atualizarEstadoBotoes(container);

    // 🔥 Atualiza o Estado do Processo
    setTimeout(atualizarStatus, 50)
}

// ==========================================
// LIMPEZA DE BLOCOS BASE
// ==========================================
function limparBlocoNorma(bloco) {
    const select = bloco.querySelector("select");
    if (select) select.selectedIndex = 0;

    bloco.querySelectorAll("input[type='text']").forEach(input => {
        input.value = "";
    });

    atualizarEstadoBotoes(bloco);
}

// ==========================================
// REAÇÃO AO CHANGE DO SELECT
// ==========================================
document.addEventListener("change", function (e) {
    if (!e.target.matches("#normas_container select")) {
        return;
    }

    const container = e.target.closest("#normas_container");
    atualizarEstadoBotoes(container);
});




