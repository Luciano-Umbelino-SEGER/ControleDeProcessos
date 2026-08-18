function initTipoProcessoMapear(config = {}) {

    // =========================================
    // CONFIG
    // =========================================
    const urlHeranca = config.urlHeranca;

    window.isTrocandoTipo = false;

    // =========================================
    // ELEMENTOS — BLOCO 1
    // =========================================
    const processoInput =
        document.getElementById("processo_input_visible");

    const subprocessoInput =
        document.getElementById("subprocesso_input_visible");

    const hiddenNome =
        document.getElementById("id_nome");

    const rbProcesso =
        document.getElementById("rb_processo");

    const rbSubprocesso =
        document.getElementById("rb_subprocesso");

    const rbOutro =
        document.getElementById("rb_outro");

    const btnAdicionar =
        document.getElementById("btn_adicionar");

    const lblProcesso =
        document.getElementById("lbl_processo");

    const lblSubprocesso =
        document.getElementById("lbl_subprocesso");

    const lblOutro =
        document.getElementById("lbl_outro");

    const lblCampoProcesso =
        document.getElementById("lbl_campo_processo");

    const lblCampoSubprocesso =
        document.getElementById("lbl_campo_subprocesso");

    const containerSelect =
        document.getElementById("processo_select_container");

    // =========================================
    // ELEMENTOS — PROCESSO PAI
    // =========================================
    const parentHidden =
        document.getElementById("id_parent");

    const parentSelect =
        document.getElementById("id_parent_select");

    // =========================================
    // ELEMENTOS — ÁREA
    // =========================================
    const areaSelect =
        document.getElementById("id_area_responsavel");

    // =========================================
    // ESTADO
    // =========================================
    let tipoAtual = "processo";

    /*
     * =====================================================
     * MEMÓRIA INDEPENDENTE POR TIPO
     *
     * PROCESSO
     *   nome
     *   parent = sempre vazio
     *   classificacao
     *   macro1
     *   macro2
     *   area
     *
     * SUBPROCESSO
     *   nome
     *   parent
     *   classificacao herdada do Pai
     *   macro1 herdado do Pai
     *   macro2 herdado do Pai
     *
     * OUTRO
     *   nome
     *   parent
     *   classificacao herdada do Pai
     *   macro1 herdado do Pai
     *   macro2 herdado do Pai
     *
     * IMPORTANTE:
     * Área não é armazenada em Subprocesso/Outro.
     * Ela continua sendo atributo derivado do Processo Pai.
     * =====================================================
     */
    const cacheEstados = {

        processo: {
            nome: "",
            parent: "",
            classificacao: "",
            macro1: "",
            macro2: "",
            area: ""
        },

        subprocesso: {
            nome: "",
            parent: "",
            classificacao: "",
            macro1: "",
            macro2: ""
        },

        outro: {
            nome: "",
            parent: "",
            classificacao: "",
            macro1: "",
            macro2: ""
        }
    };

    // =========================================
    // UTILITÁRIOS
    // =========================================

    function getTipoSelecionado() {

        if (rbProcesso?.checked) {
            return "processo";
        }

        if (rbSubprocesso?.checked) {
            return "subprocesso";
        }

        return "outro";
    }

    function obterParentAtual() {

        if (!parentSelect) {
            return parentHidden?.value || "";
        }

        if (window.$) {
            return $(parentSelect).val() || "";
        }

        return parentSelect.value || "";
    }

    function obterAreaAtual() {

        if (!areaSelect) {
            return "";
        }

        if (window.$) {
            return $(areaSelect).val() || "";
        }

        return areaSelect.value || "";
    }

    function obterCaracteristicasAtuais() {

        return {
            classificacao:
                document.getElementById(
                    "id_classificacao"
                )?.value || "",

            macro1:
                document.getElementById(
                    "id_macroprocesso_nivel1"
                )?.value || "",

            macro2:
                document.getElementById(
                    "id_macroprocesso_nivel2"
                )?.value || ""
        };
    }

    function definirParent(parentId,dispararChange = false) {

        const valor = parentId || "";

        // =========================================
        // HIDDEN DJANGO
        // =========================================
        if (parentHidden) {
            parentHidden.value = valor;
        }

        // =========================================
        // SELECT VISUAL / SELECT2
        // =========================================
        if (!parentSelect) {
            return;
        }

        if (
            window.$ &&
            $(parentSelect).hasClass(
                "select2-hidden-accessible"
            )
        ) {

            /*
             * Atualiza o valor interno.
             */
            $(parentSelect).val(
                valor || null
            );

            /*
             * Atualiza somente a interface do Select2.
             *
             * NÃO usamos "change", pois isso poderia
             * disparar novamente a lógica de seleção
             * do Processo Pai.
             */
            $(parentSelect).trigger(
                "change.select2"
            );

            /*
             * Só dispara o change completo quando
             * explicitamente solicitado.
             */
            if (dispararChange) {
                $(parentSelect).trigger(
                    "change"
                );
            }

        } else {

            parentSelect.value = valor;
        }
    }

    function definirArea(areaId) {

        if (!areaSelect) {
            return;
        }

        const valor = areaId || "";

        if (window.$) {

            if (
                $(areaSelect).hasClass(
                    "select2-hidden-accessible"
                )
            ) {

                /*
                 * Atualiza somente a interface do Select2.
                 * Não dispara a herança da Área.
                 */
                $(areaSelect)
                    .val(valor || null)
                    .trigger("change.select2");

            } else {

                $(areaSelect).val(valor);
            }

        } else {

            areaSelect.value = valor;
        }
    }

    // =========================================
    // SINCRONIZAÇÃO DO NOME
    // =========================================
    function sincronizarNome() {

        if (!hiddenNome) {
            return;
        }

        if (tipoAtual === "processo") {

            hiddenNome.value =
                processoInput?.value?.trim() || "";

        } else {

            hiddenNome.value =
                subprocessoInput?.value?.trim() || "";
        }
    }

    // =========================================
    // SALVA ESTADO DO TIPO ATUAL
    // =========================================
    function salvarEstado(tipo) {

        if (!cacheEstados[tipo]) {
            return;
        }

        // =========================================
        // PROCESSO
        // =========================================
        if (tipo === "processo") {

            cacheEstados.processo.nome =
                processoInput?.value || "";

            cacheEstados.processo.parent =
                "";

            const caracteristicas =
                obterCaracteristicasAtuais();

            cacheEstados.processo.classificacao =
                caracteristicas.classificacao;

            cacheEstados.processo.macro1 =
                caracteristicas.macro1;

            cacheEstados.processo.macro2 =
                caracteristicas.macro2;

            cacheEstados.processo.area =
                obterAreaAtual();

            return;
        }

        // =========================================
        // SUBPROCESSO
        // =========================================
        if (tipo === "subprocesso") {

            cacheEstados.subprocesso.nome =
                subprocessoInput?.value || "";

            cacheEstados.subprocesso.parent =
                obterParentAtual();

            const caracteristicas =
                obterCaracteristicasAtuais();

            cacheEstados.subprocesso.classificacao =
                caracteristicas.classificacao;

            cacheEstados.subprocesso.macro1 =
                caracteristicas.macro1;

            cacheEstados.subprocesso.macro2 =
                caracteristicas.macro2;

            return;
        }

        // =========================================
        // OUTRO
        // =========================================
        if (tipo === "outro") {

            cacheEstados.outro.nome =
                subprocessoInput?.value || "";

            cacheEstados.outro.parent =
                obterParentAtual();

            const caracteristicas =
                obterCaracteristicasAtuais();

            cacheEstados.outro.classificacao =
                caracteristicas.classificacao;

            cacheEstados.outro.macro1 =
                caracteristicas.macro1;

            cacheEstados.outro.macro2 =
                caracteristicas.macro2;
        }
    }

    // =========================================
    // PREPARA ESTADO DO TIPO DE DESTINO
    //
    // Regra:
    //
    // 1. Processo não possui Parent.
    //
    // 2. Subprocesso e Outro possuem memória
    //    independente.
    //
    // 3. Se o tipo destino já possui Parent,
    //    mantém seu próprio estado.
    //
    // 4. Se o destino está vazio e o outro tipo
    //    não-Processo possui Parent, herda:
    //
    //      Parent
    //      Classificação
    //      Macro N1
    //      Macro N2
    //
    // 5. A transferência só ocorre quando o
    //    destino estiver vazio.
    // =========================================
    function prepararEstadoDestino(
        tipoAnterior,
        novoTipo
    ) {

        // =========================================
        // PROCESSO
        // =========================================
        if (novoTipo === "processo") {

            cacheEstados.processo.parent = "";

            return;
        }

        const estadoDestino =
            cacheEstados[novoTipo];

        if (!estadoDestino) {
            return;
        }

        // =========================================
        // DESTINO JÁ POSSUI PAI
        // =========================================
        if (estadoDestino.parent) {

            /*
             * O tipo já possui sua própria associação.
             *
             * Não recebe nada do outro tipo.
             */
            return;
        }

        // =========================================
        // IDENTIFICA O OUTRO TIPO NÃO-PROCESSO
        // =========================================
        const outroTipo =
            novoTipo === "subprocesso"
                ? "outro"
                : "subprocesso";

        const estadoOutro =
            cacheEstados[outroTipo];

        if (!estadoOutro) {
            return;
        }

        // =========================================
        // OUTRO TIPO NÃO POSSUI PAI
        // =========================================
        if (!estadoOutro.parent) {
            return;
        }

        // =========================================
        // HERDA O ESTADO DO OUTRO TIPO
        // =========================================

        estadoDestino.parent =
            estadoOutro.parent;

        estadoDestino.classificacao =
            estadoOutro.classificacao || "";

        estadoDestino.macro1 =
            estadoOutro.macro1 || "";

        estadoDestino.macro2 =
            estadoOutro.macro2 || "";
    }

    // =========================================
    // LIMPA CARACTERÍSTICAS VISUAIS
    // =========================================
    function limparCaracteristicasDaTela() {

        const selects = [
            "id_classificacao",
            "id_macroprocesso_nivel1",
            "id_macroprocesso_nivel2",
            "id_area_responsavel"
        ];

        const contatos = [
            "id_gestor",
            "id_telefone",
            "id_email"
        ];

        // =========================================
        // SELECTS
        // =========================================
        selects.forEach(id => {

            const el =
                document.getElementById(id);

            if (!el) {
                return;
            }

            if (
                window.$ &&
                $(el).hasClass(
                    "select2-hidden-accessible"
                )
            ) {

                /*
                 * Atualiza somente o Select2.
                 *
                 * Não dispara a herança de Área.
                 */
                $(el)
                    .val(null)
                    .trigger("change.select2");

            } else {

                el.value = "";
            }
        });

        // =========================================
        // CONTATOS
        // =========================================
        contatos.forEach(id => {

            const el =
                document.getElementById(id);

            if (el) {
                el.value = "";
            }
        });
    }

    // =========================================
    // RESTAURA CARACTERÍSTICAS DO CACHE
    // =========================================
    function restaurarCaracteristicasDoCache(
        estado
    ) {

        if (!estado) {
            return;
        }

        const classificacao =
            document.getElementById(
                "id_classificacao"
            );

        const macro1 =
            document.getElementById(
                "id_macroprocesso_nivel1"
            );

        const macro2 =
            document.getElementById(
                "id_macroprocesso_nivel2"
            );

        if (classificacao) {

            if (
                window.$ &&
                $(classificacao).hasClass(
                    "select2-hidden-accessible"
                )
            ) {

                $(classificacao)
                    .val(
                        estado.classificacao || null
                    )
                    .trigger("change.select2");

            } else {

                classificacao.value =
                    estado.classificacao || "";
            }
        }

        if (macro1) {

            if (
                window.$ &&
                $(macro1).hasClass(
                    "select2-hidden-accessible"
                )
            ) {

                $(macro1)
                    .val(
                        estado.macro1 || null
                    )
                    .trigger("change.select2");

            } else {

                macro1.value =
                    estado.macro1 || "";
            }
        }

        if (macro2) {

            if (
                window.$ &&
                $(macro2).hasClass(
                    "select2-hidden-accessible"
                )
            ) {

                $(macro2)
                    .val(
                        estado.macro2 || null
                    )
                    .trigger("change.select2");

            } else {

                macro2.value =
                    estado.macro2 || "";
            }
        }
    }

    // =========================================
    // RESTAURA ESTADO DO TIPO
    // =========================================
    function restaurarEstado(tipo) {

        const estado =
            cacheEstados[tipo];

        if (!estado) {
            return;
        }

        // =========================================
        // PROCESSO
        // =========================================
        if (tipo === "processo") {

            if (processoInput) {

                processoInput.value =
                    estado.nome || "";
            }

            definirParent(
                "",
                false
            );

            restaurarCaracteristicasDoCache(
                estado
            );

            definirArea(
                estado.area || ""
            );

            if (subprocessoInput) {

                subprocessoInput.value =
                    "";
            }

            return;
        }

        // =========================================
        // SUBPROCESSO
        // =========================================
        if (tipo === "subprocesso") {

            if (subprocessoInput) {

                subprocessoInput.value =
                    estado.nome || "";
            }

            definirParent(
                estado.parent || "",
                false
            );

            restaurarCaracteristicasDoCache(
                estado
            );

            return;
        }

        // =========================================
        // OUTRO
        // =========================================
        if (tipo === "outro") {

            if (subprocessoInput) {

                subprocessoInput.value =
                    estado.nome || "";
            }

            definirParent(
                estado.parent || "",
                false
            );

            restaurarCaracteristicasDoCache(
                estado
            );
        }
    }

    // =========================================
    // LABELS
    // =========================================
    function atualizarLabels() {

        lblProcesso?.classList.remove(
            "text-blue-700",
            "text-gray-400"
        );

        lblSubprocesso?.classList.remove(
            "text-blue-700",
            "text-gray-400"
        );

        lblOutro?.classList.remove(
            "text-blue-700",
            "text-gray-400"
        );

        lblCampoSubprocesso?.classList.remove(
            "text-blue-700",
            "text-gray-400"
        );

        // =========================================
        // PROCESSO
        // =========================================
        if (tipoAtual === "processo") {

            lblProcesso?.classList.add(
                "text-blue-700"
            );

            lblSubprocesso?.classList.add(
                "text-gray-400"
            );

            lblOutro?.classList.add(
                "text-gray-400"
            );

            if (lblCampoProcesso) {
                lblCampoProcesso.textContent =
                    "Nome";
            }

            if (lblCampoSubprocesso) {

                lblCampoSubprocesso.textContent =
                    "Nome do Subprocesso";

                lblCampoSubprocesso.classList.add(
                    "text-gray-400"
                );
            }

            return;
        }

        // =========================================
        // SUBPROCESSO
        // =========================================
        if (tipoAtual === "subprocesso") {

            lblSubprocesso?.classList.add(
                "text-blue-700"
            );

            lblProcesso?.classList.add(
                "text-gray-400"
            );

            lblOutro?.classList.add(
                "text-gray-400"
            );

            if (lblCampoProcesso) {
                lblCampoProcesso.textContent =
                    "Selecionar Processo para associar";
            }

            if (lblCampoSubprocesso) {

                lblCampoSubprocesso.textContent =
                    "Nome do Subprocesso";

                lblCampoSubprocesso.classList.add(
                    "text-blue-700"
                );
            }

            return;
        }

        // =========================================
        // OUTRO
        // =========================================
        lblOutro?.classList.add(
            "text-blue-700"
        );

        lblProcesso?.classList.add(
            "text-gray-400"
        );

        lblSubprocesso?.classList.add(
            "text-gray-400"
        );

        if (lblCampoProcesso) {

            lblCampoProcesso.textContent =
                "Selecionar Processo para associar";
        }

        if (lblCampoSubprocesso) {

            lblCampoSubprocesso.textContent =
                "Nome";

            lblCampoSubprocesso.classList.add(
                "text-blue-700"
            );
        }
    }

    // =========================================
    // BOTÕES
    // =========================================
    function atualizarBotoes() {

        if (!btnAdicionar) {
            return;
        }

        btnAdicionar.textContent =
            tipoAtual === "outro"
                ? "Adicionar Elemento"
                : "Adicionar Processo a Mapear";
    }

    // =========================================
    // VISIBILIDADE DOS CAMPOS
    // =========================================
    function atualizarVisibilidadeCampos() {

        if (tipoAtual === "processo") {

            processoInput?.classList.remove(
                "hidden"
            );

            containerSelect?.classList.add(
                "hidden"
            );

            if (subprocessoInput) {

                subprocessoInput.disabled = true;

                subprocessoInput.classList.add(
                    "bg-gray-100"
                );
            }

            return;
        }

        processoInput?.classList.add(
            "hidden"
        );

        containerSelect?.classList.remove(
            "hidden"
        );

        if (subprocessoInput) {

            subprocessoInput.disabled = false;

            subprocessoInput.classList.remove(
                "bg-gray-100"
            );
        }
    }

    // =========================================
    // ESTADO DOS CAMPOS POR TIPO
    // =========================================
    function atualizarEstadoCamposPorTipo() {

        const camposEstruturais = [
            "id_classificacao",
            "id_macroprocesso_nivel1",
            "id_macroprocesso_nivel2",
            "id_area_responsavel"
        ];

        const camposContato = [
            "id_gestor",
            "id_telefone",
            "id_email"
        ];

        if (tipoAtual === "processo") {

            camposEstruturais.forEach(
                HerancaProcesso.desbloquearCampo
            );

            camposContato.forEach(
                HerancaProcesso.bloquearCampo
            );

            return;
        }

        [
            ...camposEstruturais,
            ...camposContato
        ].forEach(
            HerancaProcesso.bloquearCampo
        );
    }

    // =========================================
    // HERANÇA DO PROCESSO PAI
    // =========================================
    window.aplicarRegraHeranca = function () {

        // =========================================
        // PROCESSO
        // =========================================
        if (tipoAtual === "processo") {

            HerancaProcesso.limpar();

            atualizarEstadoCamposPorTipo();

            return;
        }

        // =========================================
        // SUBPROCESSO / OUTRO
        // =========================================
        const processoId =
            obterParentAtual();

        // =========================================
        // SEM PROCESSO PAI
        // =========================================
        if (!processoId) {

            HerancaProcesso.limpar();

            atualizarEstadoCamposPorTipo();

            return;
        }

        // =========================================
        // CAPTURA O ESTADO DA CONSULTA
        //
        // IMPORTANTE:
        // Essas variáveis precisam ser capturadas
        // ANTES do fetch.
        // =========================================
        const tipoDaConsulta =
            tipoAtual;

        const parentDaConsulta =
            processoId;

        // =========================================
        // EXISTE PROCESSO PAI
        // =========================================
        HerancaProcesso.aplicar(
            processoId,
            {
                url: urlHeranca,

                onApply: (data) => {

                    // =====================================
                    // SEGURANÇA — TIPO NÃO É MAIS O MESMO
                    // =====================================
                    if (
                        tipoAtual !== tipoDaConsulta
                    ) {
                        return;
                    }

                    // =====================================
                    // SEGURANÇA — PAI NÃO É MAIS O MESMO
                    // =====================================
                    if (
                        cacheEstados[tipoDaConsulta].parent !==
                        parentDaConsulta
                    ) {
                        return;
                    }

                    // =====================================
                    // GUARDA A HERANÇA NO TIPO CORRETO
                    // =====================================
                    cacheEstados[tipoDaConsulta].parent =
                        parentDaConsulta;

                    cacheEstados[tipoDaConsulta].classificacao =
                        data.classificacao || "";

                    cacheEstados[tipoDaConsulta].macro1 =
                        data.macro1 || "";

                    cacheEstados[tipoDaConsulta].macro2 =
                        data.macro2 || "";

                    // =====================================
                    // RESTAURA O ESTADO DO TIPO
                    // =====================================
                    restaurarEstado(
                        tipoDaConsulta
                    );

                    // =====================================
                    // HERANÇA DA ÁREA RESPONSÁVEL
                    //
                    // A Área já veio do Processo Pai.
                    // Agora usamos essa Área para hidratar:
                    // - Gestor
                    // - Telefone / Ramal
                    // - E-mail
                    //
                    // O "true" informa que a hidratação foi
                    // solicitada pela herança do Processo Pai,
                    // não por uma seleção manual da Área.
                    // =====================================
                    if (
                        data.area &&
                        typeof window.preencherCamposArea === "function"
                    ) {
                        window.preencherCamposArea(
                            data.area,
                            true
                        );
                    }

                    // =====================================
                    // MANTÉM OS CAMPOS BLOQUEADOS
                    // =====================================
                    atualizarEstadoCamposPorTipo();
                }
            }
        );
    };

    // =========================================
    // TROCA DE TIPO
    // =========================================
    function trocarTipo(event = null) {

        window.isTrocandoTipo = true;

        const novoTipo =
            event
                ? event.target.value
                : getTipoSelecionado();

        const tipoAnterior =
            tipoAtual;

        // =========================================
        // 1. GUARDA ESTADO ANTERIOR
        // =========================================
        salvarEstado(
            tipoAnterior
        );

        // =========================================
        // 2. PREPARA ESTADO DESTINO
        // =========================================
        prepararEstadoDestino(
            tipoAnterior,
            novoTipo
        );

        // =========================================
        // 3. ATUALIZA TIPO
        // =========================================
        tipoAtual =
            novoTipo;

        // =========================================
        // 4. ATUALIZA INTERFACE
        // =========================================
        atualizarLabels();

        atualizarVisibilidadeCampos();

        atualizarEstadoCamposPorTipo();

        atualizarBotoes();

        // =========================================
        // 5. LIMPA CARACTERÍSTICAS VISUAIS
        //
        // Somente Subprocesso/Outro.
        // =========================================
        if (
            tipoAtual === "subprocesso" ||
            tipoAtual === "outro"
        ) {

            limparCaracteristicasDaTela();
        }

        // =========================================
        // 6. RESTAURA ESTADO DO DESTINO
        // =========================================
        restaurarEstado(
            tipoAtual
        );

        // =========================================
        // 7. APLICA HERANÇA DO PAI
        // =========================================
        aplicarRegraHeranca();

        // =========================================
        // 8. SINCRONIZA NOME
        // =========================================
        sincronizarNome();

        setTimeout(() => {

            window.isTrocandoTipo =
                false;

        }, 0);
    }

    // =========================================
    // EVENTOS DOS RADIOS
    // =========================================
    rbProcesso?.addEventListener(
        "click",
        trocarTipo
    );

    rbSubprocesso?.addEventListener(
        "click",
        trocarTipo
    );

    rbOutro?.addEventListener(
        "click",
        trocarTipo
    );

    // =========================================
    // EVENTOS DOS NOMES
    // =========================================
    processoInput?.addEventListener(
        "input",
        function () {

            if (
                tipoAtual !== "processo"
            ) {
                return;
            }

            cacheEstados.processo.nome =
                processoInput.value || "";

            sincronizarNome();
        }
    );

    subprocessoInput?.addEventListener(
        "input",
        function () {

            if (
                tipoAtual !== "subprocesso" &&
                tipoAtual !== "outro"
            ) {
                return;
            }

            cacheEstados[tipoAtual].nome =
                subprocessoInput.value || "";

            sincronizarNome();
        }
    );

    // =========================================
    // EVENTO DA ÁREA — SOMENTE PROCESSO
    // =========================================
    if (areaSelect) {

        $(areaSelect).on(
            "change.tipoProcessoMapear",
            function () {

                if (window.isTrocandoTipo) {
                    return;
                }

                if (
                    tipoAtual !== "processo"
                ) {
                    return;
                }

                cacheEstados.processo.area =
                    $(this).val() || "";
            }
        );
    }

    // =========================================
    // EVENTO DO PROCESSO PAI
    // =========================================
    if (parentSelect) {

        $(parentSelect).on(
            "change.tipoProcessoMapear",
            function () {

                if (window.isTrocandoTipo) {
                    return;
                }

                if (
                    tipoAtual !== "subprocesso" &&
                    tipoAtual !== "outro"
                ) {
                    return;
                }

                const processoId =
                    $(this).val() || "";

                const tipoDoEvento =
                    tipoAtual;

                /*
                 * A associação pertence EXCLUSIVAMENTE
                 * ao tipo atualmente selecionado.
                 */
                cacheEstados[tipoDoEvento].parent =
                    processoId;

                /*
                 * O Pai mudou.
                 *
                 * Portanto as características herdadas
                 * anteriormente deixam de ser válidas.
                 */
                cacheEstados[tipoDoEvento].classificacao =
                    "";

                cacheEstados[tipoDoEvento].macro1 =
                    "";

                cacheEstados[tipoDoEvento].macro2 =
                    "";

                /*
                 * Limpa somente a representação visual.
                 */
                limparCaracteristicasDaTela();

                if (parentHidden) {

                    parentHidden.value =
                        processoId;
                }

                /*
                 * IMPORTANTE:
                 *
                 * O template já possui um listener de change
                 * responsável por chamar aplicarRegraHeranca().
                 *
                 * Portanto NÃO chamamos novamente aqui.
                 *
                 * Este listener fica responsável somente por
                 * atualizar a memória do tipo atual.
                 */
            }
        );
    }

    // =========================================
    // INIT
    // =========================================
    tipoAtual =
        getTipoSelecionado();

    if (tipoAtual === "processo") {

        cacheEstados.processo.nome =
            processoInput?.value || "";

        cacheEstados.processo.parent =
            "";

        const caracteristicas =
            obterCaracteristicasAtuais();

        cacheEstados.processo.classificacao =
            caracteristicas.classificacao;

        cacheEstados.processo.macro1 =
            caracteristicas.macro1;

        cacheEstados.processo.macro2 =
            caracteristicas.macro2;

        cacheEstados.processo.area =
            obterAreaAtual();

    } else if (
        tipoAtual === "subprocesso"
    ) {

        cacheEstados.subprocesso.nome =
            subprocessoInput?.value || "";

        cacheEstados.subprocesso.parent =
            obterParentAtual();

        const caracteristicas =
            obterCaracteristicasAtuais();

        cacheEstados.subprocesso.classificacao =
            caracteristicas.classificacao;

        cacheEstados.subprocesso.macro1 =
            caracteristicas.macro1;

        cacheEstados.subprocesso.macro2 =
            caracteristicas.macro2;

    } else {

        cacheEstados.outro.nome =
            subprocessoInput?.value || "";

        cacheEstados.outro.parent =
            obterParentAtual();

        const caracteristicas =
            obterCaracteristicasAtuais();

        cacheEstados.outro.classificacao =
            caracteristicas.classificacao;

        cacheEstados.outro.macro1 =
            caracteristicas.macro1;

        cacheEstados.outro.macro2 =
            caracteristicas.macro2;
    }

    // =========================================
    // INICIALIZAÇÃO
    // =========================================
    atualizarLabels();

    atualizarVisibilidadeCampos();

    atualizarEstadoCamposPorTipo();

    atualizarBotoes();

    restaurarEstado(
        tipoAtual
    );

    aplicarRegraHeranca();

    sincronizarNome();
}