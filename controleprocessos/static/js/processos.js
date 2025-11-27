// ===============================
// processos.js – FINAL (robusto, reverse-update DESATIVADO por padrão)
// ===============================

document.addEventListener("DOMContentLoaded", function () {

    // =========================
    // Config
    // =========================
    const ENABLE_REVERSE_UPDATE = false; // mudar para true só se quiser reativar a seleção reversa (com cautela)
    const modoInclusao = document.body.dataset.modoInclusao === "true";


    // -------------------------
    // Helpers de segurança
    // -------------------------
    function safeGet(id) {
        try { return document.getElementById(id); }
        catch (e) { return null; }
    }

    function safeFetchJson(url) {
        return fetch(url, {
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
        }).then(r => r.json());
    }

    // =====================================================================
    // 🔵 LINHA 2 — PROCESSO / SUBPROCESSO (mantido e sincronizado)
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

    // novo: campo visível do subprocesso (não ligado ao model diretamente)
    const subprocessoInputVisible = safeGet("subprocesso_input_visible");

    // campos ocultos que realmente entram no form
    const parentField = safeGet("id_parent");   // hidden original {{ form.parent }} ou input hidden
    const hiddenNomeField = safeGet("id_nome"); // agora é input hidden name="nome"

    let selectListenerAdded = false;

    function limparCampos() {
        if (processoInputVisible) processoInputVisible.value = "";
        if (subprocessoInputVisible) subprocessoInputVisible.value = "";
        if (hiddenNomeField) hiddenNomeField.value = "";
        if (parentField) parentField.value = "";
        if (processoSelectVisible) processoSelectVisible.selectedIndex = 0;
    }

    function setModeProcesso() {
        if (!rbProcesso || !rbSubprocesso) return;

        rbProcesso.checked = true;
        rbSubprocesso.checked = false;

        if (lblProcesso) {
            lblProcesso.classList.add("text-blue-700");
            lblProcesso.classList.remove("text-gray-400");
        }

        if (lblSubprocesso) {
            lblSubprocesso.classList.add("text-gray-400");
            lblSubprocesso.classList.remove("text-blue-700");
        }

        if (lblCampoProcesso) {
            lblCampoProcesso.classList.add("text-blue-700");
            lblCampoProcesso.classList.remove("text-gray-400");
        }

        if (lblCampoSubprocesso) {
            lblCampoSubprocesso.classList.add("text-gray-400");
            lblCampoSubprocesso.classList.remove("text-blue-700");
        }

        // Mostrar input de processo, esconder select
        if (processoInputVisible) processoInputVisible.classList.remove("hidden");
        if (processoSelectContainer) processoSelectContainer.classList.add("hidden");

        // Processo: input editável
        if (processoInputVisible) {
            processoInputVisible.disabled = false;
            processoInputVisible.classList.remove("bg-gray-100");
            processoInputVisible.classList.add("bg-white");
        }

        // Subprocesso: desabilitado e fundo cinza (visível apenas se template antigo)
        if (subprocessoInputVisible) {
            subprocessoInputVisible.disabled = true;
            subprocessoInputVisible.classList.add("bg-gray-100", "text-gray-500");
            subprocessoInputVisible.classList.remove("bg-white");
        }

        // parent deve ficar vazio em modo processo
        if (parentField) {
            parentField.value = "";
            parentField.disabled = true;
        }

        // limpar visíveis (conforme solicitado)
        limparCampos();
    }

    function setModeSubprocesso() {
        if (!rbProcesso || !rbSubprocesso) return;

        rbProcesso.checked = false;
        rbSubprocesso.checked = true;

        if (lblProcesso) {
            lblProcesso.classList.add("text-blue-700");
            lblProcesso.classList.remove("text-gray-400");
        }

        if (lblSubprocesso) {
            lblSubprocesso.classList.add("text-blue-700");
            lblSubprocesso.classList.remove("text-gray-400");
        }

        if (lblCampoProcesso) {
            lblCampoProcesso.classList.add("text-blue-700");
            lblCampoProcesso.classList.remove("text-gray-400");
        }

        if (lblCampoSubprocesso) {
            lblCampoSubprocesso.classList.add("text-blue-700");
            lblCampoSubprocesso.classList.remove("text-gray-400");
        }

        // esconder input processo e mostrar select de seleção de processo pai
        if (processoInputVisible) processoInputVisible.classList.add("hidden");
        if (processoSelectContainer) processoSelectContainer.classList.remove("hidden");

        // Subprocesso: habilitado e fundo branco para digitação
        if (subprocessoInputVisible) {
            subprocessoInputVisible.disabled = false;
            subprocessoInputVisible.classList.remove("bg-gray-100", "text-gray-500");
            subprocessoInputVisible.classList.add("bg-white");
        }

        // parent ficará enabled (será preenchido ao escolher no select)
        if (parentField) parentField.disabled = false;

        // limpar visíveis (conforme solicitado)
        limparCampos();

        // carregar lista de processos pai no select
        if (processoSelectVisible) {
            fetch("/api/processos_pai/")
                .then(r => r.json())
                .then(data => {
                    processoSelectVisible.innerHTML = `<option value="">---------</option>`;
                    (data.processos_pai || []).forEach(p => {
                        const opt = document.createElement("option");
                        opt.value = p.id;
                        opt.textContent = p.nome;
                        processoSelectVisible.appendChild(opt);
                    });
                    if (parentField && parentField.value) {
                        processoSelectVisible.value = parentField.value;
                    }
                })
                .catch(e => console.error("Erro ao carregar processos pai:", e));
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

    // inicialização: se o form já vier com parent preenchido tratamos como subprocesso
    try {
        if (parentField && parentField.value) {
            // preencher visible inputs a partir dos ocultos (caso venham do servidor)
            setModeSubprocesso();
            if (processoSelectVisible) processoSelectVisible.value = parentField.value;
            if (hiddenNomeField && subprocessoInputVisible) subprocessoInputVisible.value = hiddenNomeField.value || "";
        } else {
            // se houver nome vindo do servidor e parent vazio, colocamos no processo input
            setModeProcesso();
            if (hiddenNomeField && processoInputVisible) processoInputVisible.value = hiddenNomeField.value || "";
        }
    } catch (e) { /* ignora */ }

    // =====================================================================
    // 🔵 MODELO DE PROCESSO / NORMA – atualizações informativas (mantido)
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
    // 🔵 TRIPLE FILTER: Classificação ↔ Macro1 ↔ Macro2 (mantido)
    // =====================================================================
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
            while (select.options.length > 0) select.remove(0);
        }

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

        selMacro1.addEventListener("change", async function () {
            const macro1Id = this.value;

            if (!macro1Id) {
                addOptions(selMacro2, await loadAllMacro2(), "");
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

            if (!macro2Id) {
                return;
            }

            if (!ENABLE_REVERSE_UPDATE) {
                return;
            }

            const classEmpty = selClass.value === "";
            const macro1Empty = selMacro1.value === "";

            if (!classEmpty || !macro1Empty) return;

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
            catch (e) {
                console.error("Erro no reverse-update:", e);
            }
        });

        (async function init() {
            addOptions(selMacro1, await loadAllMacro1());
            addOptions(selMacro2, await loadAllMacro2());
        })();

    })(); // fim tripleFilter

    // =====================================================================
    // 🔵 SINCRONIZAÇÃO ANTES DO SUBMIT (garante que backend receba nome/parent corretos)
    // =====================================================================
    (function syncNomeBeforeSubmit() {
        const form = document.getElementById("form-processo");
        if (!form) return;

        form.addEventListener("submit", function (ev) {
            // Determina valor de nome e parent conforme modo atual
            let nomeValor = "";
            let parentValor = "";

            if (rbSubprocesso && rbSubprocesso.checked) {
                if (subprocessoInputVisible) nomeValor = subprocessoInputVisible.value.trim();
                if (processoSelectVisible) parentValor = processoSelectVisible.value || "";
            } else {
                if (processoInputVisible) nomeValor = processoInputVisible.value.trim();
                parentValor = "";
            }

            // sincroniza com os campos reais
            if (hiddenNomeField) hiddenNomeField.value = nomeValor;
            if (parentField) parentField.value = parentValor;

            // validação cliente simples (evitar envio sem nome)
            if (!nomeValor) {
                // marca visualmente o(s) campo(s) visíveis
                if (rbSubprocesso && rbSubprocesso.checked) {
                    if (subprocessoInputVisible) {
                        subprocessoInputVisible.classList.add('border-red-500','ring-2','ring-red-300');
                        subprocessoInputVisible.focus();
                    }
                } else {
                    if (processoInputVisible) {
                        processoInputVisible.classList.add('border-red-500','ring-2','ring-red-300');
                        processoInputVisible.focus();
                    }
                }

                alert("Preencha o nome do Processo/Subprocesso antes de enviar.");
                ev.preventDefault();
                return false;
            }

            // segue com o envio normal (back-end fará validações finais)
            return true;
        });
    })();


    // =====================================================================
    // 🔴 DESTAQUE AUTOMÁTICO DE CAMPOS COM ERRO (INCLUSÃO/EDIÇÃO)
    // =====================================================================
    // Além de marcar o campo real (campo oculto), também marcou o input visível correspondente.
    (function destaqueCamposErro() {
        document.querySelectorAll('.alert ul li strong').forEach(err => {
            const fieldName = err.textContent.replace(':', '').trim();
            const field = document.querySelector(`[name="${fieldName}"]`);

            if (field) {
                // adiciona estilo ao campo real (se visível)
                field.classList.add('border-red-500', 'ring-2', 'ring-red-300');

                // se o campo é "nome" (hidden), marca o input visível correspondente
                if (fieldName === 'nome') {
                    if (rbSubprocesso && rbSubprocesso.checked) {
                        if (subprocessoInputVisible) subprocessoInputVisible.classList.add('border-red-500', 'ring-2', 'ring-red-300');
                    } else {
                        if (processoInputVisible) processoInputVisible.classList.add('border-red-500', 'ring-2', 'ring-red-300');
                    }
                }

                // se o campo é "parent" (FK), marca o select visível quando aplicável
                if (fieldName === 'parent') {
                    if (processoSelectVisible) processoSelectVisible.classList.add('border-red-500', 'ring-2', 'ring-red-300');
                }
            }
        });
    })();

}); // fim DOMContentLoaded
