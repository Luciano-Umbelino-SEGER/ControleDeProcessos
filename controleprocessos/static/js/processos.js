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

        // 🔒 Bloqueio FINAL após toda a inicialização
        setTimeout(() => {
            bloquearBotoesAdicionarRemover();
        }, 0);

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
// VISUALIZAR DOCUMENTO — BLOCOS CLONADOS
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

function preencherCamposModelo(block, dados) {
    block.querySelector('[id^="tema_modelo"]').value = dados.tema || "";
    //block.querySelector('[id^="versao_modelo"]').value = dados.versao || "";
    block.querySelector('[id^="versao_modelo"]').value = formatarVersao(dados.versao);
    block.querySelector('[id^="emitente_modelo"]').value = dados.emitente || "";
    block.querySelector('[id^="sistema_modelo"]').value = dados.sistema || "";
    //block.querySelector('[id^="vigencia_modelo"]').value = dados.vigencia || "";
    block.querySelector('[id^="vigencia_modelo"]').value = formatarDataISO_para_BR(dados.vigencia);

}

function preencherCamposNorma(block, dados) {
    block.querySelector('[id^="tema_norma"]').value = dados.tema || "";
    //block.querySelector('[id^="versao_norma"]').value = dados.versao || "";
    block.querySelector('[id^="versao_norma"]').value = formatarVersao(dados.versao);
    block.querySelector('[id^="emitente_norma"]').value = dados.emitente || "";
    block.querySelector('[id^="sistema_norma"]').value = dados.sistema || "";
    //block.querySelector('[id^="vigencia_norma"]').value = dados.vigencia || "";
    block.querySelector('[id^="vigencia_norma"]').value = formatarDataISO_para_BR(dados.vigencia);

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
    // ==========================================
    // HIDRATAÇÃO — BLOCOS CLONADOS (MODELO)
    // Usa $nextTick para garantir Alpine pronto
    // ==========================================
    MODELOS_HIDRATADOS.slice(1).forEach((dados, idx) => {
        const uid = `hidratado_${idx}_${Date.now()}`;
        const bloco = clonarTemplate("template-modelo", container, uid);
        if (!bloco) return;

        const select = bloco.querySelector('select[name="modelagem_processo_extra[]"]');
        if (!select) return;

        // Seleciona o modelo correto
        select.value = dados.id;

        // 🔥 AGORA SIM: espera Alpine finalizar completamente
        atualizarBlocoAlpine(bloco, select);

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
    // ==========================================
    // HIDRATAÇÃO — BLOCOS CLONADOS (NORMA)
    // Usa Alpine.nextTick para garantir x-data pronto
    // ==========================================
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

// ==========================================
// AÇÕES GLOBAIS — BOTÕES + / -
// ==========================================
function addModelo(botao) {
    const container = document.getElementById("modelos_container");
    if (!container) return;

    const uid = `modelo_${Date.now()}`;
    clonarTemplate("template-modelo", container, uid);

    atualizarEstadoBotoes(container);
}

function removeModelo(botao) {
    const container = document.getElementById("modelos_container");
    if (!container) return;

    const blocos = Array.from(
        container.querySelectorAll('.modelo-block')
    );

    // 🔹 só existe o bloco base → limpar
    if (blocos.length <= 1) {
        limparBlocoModelo(blocos[0]);

        // 🔥 AJUSTE ESSENCIAL
        atualizarEstadoBotoes(container);

        // 🔥 recalcula estado
        atualizarStatus();

        return;
    }

    // 🔹 remove o último bloco clonado (nunca o base)
    const ultimo = blocos[blocos.length - 1];
    ultimo.remove();

    // 🔥 após remover, reavaliar botões
    atualizarEstadoBotoes(container);

    // 🔥 Atualiza o Estado do Processo
    setTimeout(atualizarStatus, 50)
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

function limparBlocoModelo(bloco) {
    const select = bloco.querySelector("select");
    if (select) select.selectedIndex = 0;

    bloco.querySelectorAll("input[type='text']").forEach(input => {
        input.value = "";
    });

    atualizarEstadoBotoes(bloco);
}

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
    if (!e.target.matches("#modelos_container select, #normas_container select")) {
        return;
    }

    const container = e.target.closest("#modelos_container, #normas_container");
    atualizarEstadoBotoes(container);
});




