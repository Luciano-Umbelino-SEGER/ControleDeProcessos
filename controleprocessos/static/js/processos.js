// ===============================
// processos.js – FINAL (robusto, modos integrados)
// ===============================

document.addEventListener("DOMContentLoaded", function () {

    // =========================
    // Config / modos (usa window.MODO se disponível)
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

    // =========================
    // Config adicional
    // =========================
    const ENABLE_REVERSE_UPDATE = false; // manter conforme sua versão original

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
    // Elementos compartilhados
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

    // campos ocultos reais que o backend espera
    const parentField = safeGet("id_parent");   // <input type="hidden" name="parent">
    const hiddenNomeField = safeGet("id_nome"); // <input type="hidden" name="nome">

    let selectListenerAdded = false;

    // utilitário para determinar se os campos devem ser editáveis
    const formIsEditable = () => modoInclusao || modoEdicao;

    // =====================================================================
    // Funções utilitárias
    // =====================================================================
    function limparVisiveis() {
        if (processoInputVisible) processoInputVisible.value = "";
        if (subprocessoInputVisible) subprocessoInputVisible.value = "";
        if (hiddenNomeField) hiddenNomeField.value = "";
        if (parentField) parentField.value = "";
        if (processoSelectVisible) processoSelectVisible.selectedIndex = 0;
    }

    // popula select de processos pai via API e retorna Promise com array
    function carregarProcessosPai() {
        return safeFetchJson("/api/processos_pai/")
            .then(data => data.processos_pai || [])
            .catch(e => {
                console.error("Erro ao carregar processos pai:", e);
                return [];
            });
    }

    function aplicarEstadoVisualLabels(isSubprocesso) {
        if (lblProcesso) {
            lblProcesso.classList.toggle("text-blue-700", true);
            lblProcesso.classList.toggle("text-gray-400", !isSubprocesso);
        }
        if (lblSubprocesso) {
            // se isSubprocesso true, sub é ativo
            lblSubprocesso.classList.toggle("text-blue-700", isSubprocesso);
            lblSubprocesso.classList.toggle("text-gray-400", !isSubprocesso);
        }

        if (lblCampoProcesso) {
            lblCampoProcesso.classList.toggle("text-blue-700", true);
            lblCampoProcesso.classList.remove("text-gray-400");
        }
        if (lblCampoSubprocesso) {
            lblCampoSubprocesso.classList.toggle("text-blue-700", isSubprocesso);
            lblCampoSubprocesso.classList.toggle("text-gray-400", !isSubprocesso);
        }
    }

    // =====================================================================
    // Modos: setModeProcesso / setModeSubprocesso para modo_inclusao
    // =====================================================================
    function setModeProcesso_inclusao() {
        aplicarEstadoVisualLabels(false);

        // mostrar input processo, esconder select
        if (processoInputVisible) processoInputVisible.classList.remove("hidden");
        if (processoSelectContainer) processoSelectContainer.classList.add("hidden");

        // processo editável (em inclusão)
        if (processoInputVisible) {
            processoInputVisible.disabled = false;
            processoInputVisible.classList.remove("bg-gray-100");
            processoInputVisible.classList.add("bg-white");
        }

        // subprocesso visível mas desabilitado
        if (subprocessoInputVisible) {
            subprocessoInputVisible.disabled = true;
            subprocessoInputVisible.classList.remove("bg-white");
            subprocessoInputVisible.classList.add("bg-gray-100", "text-gray-500");
            subprocessoInputVisible.value = "";
        }

        if (parentField) {
            parentField.value = "";
            parentField.disabled = true;
        }

        // limpamos visíveis conforme especificado
        limparVisiveis();
    }

    async function setModeSubprocesso_inclusao() {
        aplicarEstadoVisualLabels(true);

        // esconder input processo, mostrar select
        if (processoInputVisible) processoInputVisible.classList.add("hidden");
        if (processoSelectContainer) processoSelectContainer.classList.remove("hidden");

        // subprocesso habilitado para digitação
        if (subprocessoInputVisible) {
            subprocessoInputVisible.disabled = false;
            subprocessoInputVisible.classList.remove("bg-gray-100", "text-gray-500");
            subprocessoInputVisible.classList.add("bg-white");
            subprocessoInputVisible.value = "";
        }

        if (parentField) parentField.disabled = false;

        // limpar visíveis
        limparVisiveis();

        // carregar lista de processos pai
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

        // listener para sincronizar parent oculto
        if (!selectListenerAdded && processoSelectVisible) {
            processoSelectVisible.addEventListener("change", function () {
                if (parentField) parentField.value = this.value;
            });
            selectListenerAdded = true;
        }
    }

    // =====================================================================
    // Inicialização e comportamento quando NÃO é modo_inclusao (edição/visualização/exclusao)
    // Regras específicas pedidas:
    // - radios desabilitados
    // - se parentId presente => registro é Subprocesso
    //   * modo_edicao: Processo vira select (com valor selecionado), Subprocesso fica editável (se modo_edicao)
    //   * modo_visualizacao/exclusao: Processo é input text desabilitado, Subprocesso desabilitado
    // - se parentId ausente => registro é Processo
    //   * modo_edicao: Processo é input text editável
    //   * modo_visualizacao/exclusao: input text desabilitado
    // =====================================================================
    async function inicializacaoNaoInclusao() {
        // Desabilitar radios (template já desabilita, mas reforçamos)
        if (rbProcesso) rbProcesso.disabled = true;
        if (rbSubprocesso) rbSubprocesso.disabled = true;

        const isSub = !!parentIdFromServer;

        // preencher hiddenNome (caso backend já tenha colocado o valor no hidden)
        const nomeDoRegistro = (hiddenNomeField && hiddenNomeField.value) ? hiddenNomeField.value : "";

        // se é Subprocesso (parent_id presente)
        if (isSub) {
            // marcar radio Subprocesso
            if (rbProcesso) rbProcesso.checked = false;
            if (rbSubprocesso) rbSubprocesso.checked = true;

            aplicarEstadoVisualLabels(true);

            // Modo EDIÇÃO -> trocar para select (mas se não for editável, select será disabled)
            if (modoEdicao) {
                // esconder input processo e mostrar select preenchido
                if (processoInputVisible) processoInputVisible.classList.add("hidden");
                if (processoSelectContainer) processoSelectContainer.classList.remove("hidden");

                // carregar processos pai e selecionar parentId
                if (processoSelectVisible) {
                    const processos = await carregarProcessosPai();
                    processoSelectVisible.innerHTML = `<option value="">---------</option>`;
                    processos.forEach(p => {
                        const opt = document.createElement("option");
                        opt.value = p.id;
                        opt.textContent = p.nome;
                        processoSelectVisible.appendChild(opt);
                    });

                    // selecionar parentId
                    if (parentIdFromServer) processoSelectVisible.value = parentIdFromServer;

                    // se não for editável, deixar select disabled; se for edição, permitir editar parent (opcional)
                    processoSelectVisible.disabled = !formIsEditable();
                }

                // preencher subprocesso input com o nome do registro (nome próprio)
                if (subprocessoInputVisible) {
                    subprocessoInputVisible.disabled = !formIsEditable();
                    subprocessoInputVisible.classList.toggle("bg-white", formIsEditable());
                    subprocessoInputVisible.classList.toggle("bg-gray-100", !formIsEditable());
                    // se hiddenNomeField vazio, tentamos obter do servidor listagem (procura no processos pai)
                    if (nomeDoRegistro) {
                        subprocessoInputVisible.value = nomeDoRegistro;
                    } else {
                        // tenta extrair o nome do objeto via API /api/processo/<id>/ (não implementado por padrão)
                        // fallback: vazio
                        subprocessoInputVisible.value = "";
                    }
                }

                // sincroniza parentField com select (caso backend não tenha definido)
                if (parentField) parentField.value = processoSelectVisible ? processoSelectVisible.value : parentIdFromServer;

                // listener para manter hidden parent atualizado (se select editável)
                if (!selectListenerAdded && processoSelectVisible) {
                    processoSelectVisible.addEventListener("change", function () {
                        if (parentField) parentField.value = this.value;
                    });
                    selectListenerAdded = true;
                }
            }
            else {
                // modo visualização ou exclusão => processo deve ser input text (desabilitado)
                if (processoSelectContainer) processoSelectContainer.classList.add("hidden");
                if (processoInputVisible) {
                    processoInputVisible.classList.remove("hidden");
                    processoInputVisible.disabled = true;
                    processoInputVisible.classList.add("bg-gray-100");
                }

                // queremos mostrar o NOME do PROCESSO pai no campo Processo (visível e desabilitado)
                // Para obter o nome do parent, carregamos processos pai e encontramos pelo id
                if (processoInputVisible) {
                    const processos = await carregarProcessosPai();
                    const parentObj = processos.find(p => String(p.id) === String(parentIdFromServer));
                    if (parentObj) {
                        processoInputVisible.value = parentObj.nome;
                    } else {
                        processoInputVisible.value = "";
                    }
                }

                // Subprocesso: mostrar nome do registro (desabilitado)
                if (subprocessoInputVisible) {
                    subprocessoInputVisible.disabled = true;
                    subprocessoInputVisible.classList.add("bg-gray-100", "text-gray-500");
                    // se o backend colocou hiddenNomeField, usa; caso contrário vazio
                    subprocessoInputVisible.value = nomeDoRegistro || "";
                }

                if (parentField) {
                    parentField.value = parentIdFromServer;
                    parentField.disabled = true;
                }
            }

        } else {
            // É PROCESSO (parent ausente)
            if (rbProcesso) rbProcesso.checked = true;
            if (rbSubprocesso) rbSubprocesso.checked = false;

            aplicarEstadoVisualLabels(false);

            // em modo edição: manter input processo visível e editável
            if (modoEdicao) {
                if (processoSelectContainer) processoSelectContainer.classList.add("hidden");
                if (processoInputVisible) {
                    processoInputVisible.classList.remove("hidden");
                    processoInputVisible.disabled = !formIsEditable(); // true for ediçao
                    processoInputVisible.classList.toggle("bg-white", formIsEditable());
                    processoInputVisible.classList.toggle("bg-gray-100", !formIsEditable());
                    // preenche com nome vindo do servidor (hiddenNomeField) se disponível
                    if (hiddenNomeField && hiddenNomeField.value) processoInputVisible.value = hiddenNomeField.value;
                    else processoInputVisible.value = "";
                }

                // subprocesso input desabilitado
                if (subprocessoInputVisible) {
                    subprocessoInputVisible.disabled = true;
                    subprocessoInputVisible.classList.add("bg-gray-100", "text-gray-500");
                    subprocessoInputVisible.value = "";
                }

                if (parentField) {
                    parentField.value = "";
                    parentField.disabled = true;
                }
            }
            else {
                // visualização / exclusão: input processo visível e desabilitado com o nome
                if (processoSelectContainer) processoSelectContainer.classList.add("hidden");
                if (processoInputVisible) {
                    processoInputVisible.classList.remove("hidden");
                    processoInputVisible.disabled = true;
                    processoInputVisible.classList.add("bg-gray-100");
                    if (hiddenNomeField && hiddenNomeField.value) processoInputVisible.value = hiddenNomeField.value;
                    else processoInputVisible.value = "";
                }

                if (subprocessoInputVisible) {
                    subprocessoInputVisible.disabled = true;
                    subprocessoInputVisible.classList.add("bg-gray-100", "text-gray-500");
                    subprocessoInputVisible.value = "";
                }

                if (parentField) {
                    parentField.value = "";
                    parentField.disabled = true;
                }
            }
        }
    }

    // =====================================================================
    // Inicialização geral
    // =====================================================================
    (async function init() {
        // Se modo inclusão -> ativar listeners para permitir troca Processo/Subprocesso
        if (modoInclusao) {
            // Radios devem estar habilitados (template já marca, mas reforçamos)
            if (rbProcesso) rbProcesso.disabled = false;
            if (rbSubprocesso) rbSubprocesso.disabled = false;

            // event listeners para os radios
            if (rbProcesso) {
                rbProcesso.addEventListener("change", function () {
                    if (rbProcesso.checked) {
                        setModeProcesso_inclusao();
                    }
                });
            }
            if (rbSubprocesso) {
                rbSubprocesso.addEventListener("change", function () {
                    if (rbSubprocesso.checked) {
                        setModeSubprocesso_inclusao();
                    }
                });
            }

            // definir estado inicial: se radio selecionado no template, seguir
            if (rbSubprocesso && rbSubprocesso.checked) {
                await setModeSubprocesso_inclusao();
            } else {
                setModeProcesso_inclusao();
            }
        }
        else {
            // não é inclusão -> comportamento especial (edição / visualização / exclusao)
            await inicializacaoNaoInclusao();
        }
    })();

    // =====================================================================
    // MODELO / NORMA — parte mantida/inalterada (copiada da sua versão)
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
    // TRIPLE FILTER – mantido exatamente (não tocar sem necessidade)
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

        (async function initTriple() {
            addOptions(selMacro1, await loadAllMacro1());
            addOptions(selMacro2, await loadAllMacro2());
        })();

    })(); // fim tripleFilter

    // =====================================================================
    // Sincronização ANTES do SUBMIT (garante backend receba nome/parent corretos)
    // =====================================================================
    (function syncNomeBeforeSubmit() {
        const form = document.getElementById("form-processo");
        if (!form) return;

        form.addEventListener("submit", function (ev) {
            let nomeValor = "";
            let parentValor = "";

            // se estamos em modo subprocesso (radio marcado), usamos o subprocesso input + select parent
            if (rbSubprocesso && rbSubprocesso.checked) {
                if (subprocessoInputVisible) nomeValor = (subprocessoInputVisible.value || "").trim();
                if (processoSelectVisible) parentValor = processoSelectVisible.value || "";
            } else {
                // processo
                if (processoInputVisible && !processoInputVisible.classList.contains("hidden")) {
                    nomeValor = (processoInputVisible.value || "").trim();
                } else if (processoSelectVisible && !processoSelectVisible.classList.contains("hidden")) {
                    // raro: select visível no submit, pega texto selecionado
                    nomeValor = (processoSelectVisible.options[processoSelectVisible.selectedIndex]?.text || "").trim();
                } else {
                    nomeValor = "";
                }
                parentValor = "";
            }

            if (hiddenNomeField) hiddenNomeField.value = nomeValor;
            if (parentField) parentField.value = parentValor;

            // validação cliente simples
            if (!nomeValor) {
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

            return true;
        });
    })();

    // =====================================================================
    // Destaque automático de campos com erro
    // =====================================================================
    (function destaqueCamposErro() {
        document.querySelectorAll('.alert ul li strong').forEach(err => {
            const fieldName = err.textContent.replace(':', '').trim();
            const field = document.querySelector(`[name="${fieldName}"]`);

            if (field) {
                field.classList.add('border-red-500', 'ring-2', 'ring-red-300');

                if (fieldName === 'nome') {
                    if (rbSubprocesso && rbSubprocesso.checked) {
                        if (subprocessoInputVisible) subprocessoInputVisible.classList.add('border-red-500', 'ring-2', 'ring-red-300');
                    } else {
                        if (processoInputVisible) processoInputVisible.classList.add('border-red-500', 'ring-2', 'ring-red-300');
                    }
                }

                if (fieldName === 'parent') {
                    if (processoSelectVisible) processoSelectVisible.classList.add('border-red-500', 'ring-2', 'ring-red-300');
                }
            }
        });
    })();

}); // fim DOMContentLoaded
