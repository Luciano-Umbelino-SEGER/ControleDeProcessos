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
    //
    // IMPORTANTE:
    // A Área pertence ao Processo.
    //
    // A hidratação de Gestor / Telefone / E-mail
    // NÃO pertence a este JS.
    // =========================================
    const areaSelect =
        document.getElementById("id_area_responsavel");

    // =========================================
    // ESTADO
    // =========================================
    let tipoAtual = "processo";

    /*
     * Memória independente por tipo.
     *
     * PROCESSO:
     *   nome
     *   parent = sempre vazio
     *   area = escolhida pelo usuário
     *
     * SUBPROCESSO:
     *   nome
     *   parent próprio
     *
     * OUTRO:
     *   nome
     *   parent próprio
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
            parent: ""
        },

        outro: {
            nome: "",
            parent: ""
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

    function definirParent(parentId, dispararChange = false) {

        const valor = parentId || "";

        if (parentHidden) {
            parentHidden.value = valor;
        }

        if (!parentSelect) {
            return;
        }

        if (
            window.$ &&
            $(parentSelect).hasClass("select2-hidden-accessible")
        ) {

            $(parentSelect).val(valor || null);

            if (dispararChange) {
                $(parentSelect).trigger("change");
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
                 * Atualiza o valor e somente o Select2.
                 *
                 * IMPORTANTE:
                 * não usamos .trigger("change"), pois isso
                 * poderia disparar a herança da Área.
                 *
                 * change.select2 atualiza apenas a interface
                 * do Select2.
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
    // SALVA ESTADO
    // =========================================
    function salvarEstado(tipo) {

        if (!cacheEstados[tipo]) {
            return;
        }

        if (tipo === "processo") {

            cacheEstados.processo.nome =
                processoInput?.value || "";

            cacheEstados.processo.parent = "";

            cacheEstados.processo.classificacao =
                document.getElementById(
                    "id_classificacao"
                )?.value || "";

            cacheEstados.processo.macro1 =
                document.getElementById(
                    "id_macroprocesso_nivel1"
                )?.value || "";

            cacheEstados.processo.macro2 =
                document.getElementById(
                    "id_macroprocesso_nivel2"
                )?.value || "";

            cacheEstados.processo.area =
                obterAreaAtual();

            return;
        }

        if (tipo === "subprocesso") {

            cacheEstados.subprocesso.nome =
                subprocessoInput?.value || "";

            cacheEstados.subprocesso.parent =
                obterParentAtual();

            return;
        }

        if (tipo === "outro") {

            cacheEstados.outro.nome =
                subprocessoInput?.value || "";

            cacheEstados.outro.parent =
                obterParentAtual();
        }
    }

    // =========================================
    // PREPARA ESTADO DO DESTINO
    // =========================================
    function prepararEstadoDestino(
        tipoAnterior,
        novoTipo
    ) {

        // Processo nunca possui Pai.
        if (novoTipo === "processo") {

            cacheEstados.processo.parent = "";

            return;
        }

        /*
         * Se o destino já possui Pai próprio,
         * preserva sua associação.
         */
        if (cacheEstados[novoTipo].parent) {
            return;
        }

        /*
         * Se ainda não possui Pai, herdamos apenas
         * a associação inicial do outro tipo de
         * rascunho.
         */
        if (
            tipoAnterior !== "processo" &&
            cacheEstados[tipoAnterior]?.parent
        ) {

            cacheEstados[novoTipo].parent =
                cacheEstados[tipoAnterior].parent;
        }
    }

    // =========================================
    // LIMPA CARACTERÍSTICAS HERDADAS NA TELA
    //
    // Usada ao entrar em Subprocesso/Outro.
    //
    // IMPORTANTE:
    // Não altera o cache do Processo.
    // Apenas limpa os valores visíveis.
    //
    // A partir do momento em que houver um Processo Pai,
    // HerancaProcesso.aplicar() preencherá novamente esses
    // campos.
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
                 * Atualiza o Select2 sem disparar o
                 * evento change da Área Responsável.
                 *
                 * Isso evita chamar a segunda herança
                 * durante a troca de Tipo.
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
    // RESTAURA ESTADO
    // =========================================
    function restaurarEstado(tipo) {

        const estado = cacheEstados[tipo];

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

            /*
             * Processo não possui Pai.
             */
            definirParent("", false);

            /*
             * Restaura as características próprias
             * que o usuário havia escolhido para o Processo.
             */
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
                classificacao.value =
                    estado.classificacao || "";
            }

            if (macro1) {
                macro1.value =
                    estado.macro1 || "";
            }

            if (macro2) {
                macro2.value =
                    estado.macro2 || "";
            }

            /*
             * Restaura a Área própria do Processo.
             *
             * Não dispara a herança da Área aqui.
             */
            definirArea(
                estado.area || ""
            );

            /*
             * O campo de Subprocesso/Outro permanece
             * visualmente vazio.
             *
             * A memória continua preservada.
             */
            if (subprocessoInput) {
                subprocessoInput.value = "";
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
                lblCampoProcesso.textContent = "Nome";
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

            processoInput?.classList.remove("hidden");

            containerSelect?.classList.add("hidden");

            if (subprocessoInput) {

                subprocessoInput.disabled = true;

                subprocessoInput.classList.add(
                    "bg-gray-100"
                );
            }

            return;
        }

        processoInput?.classList.add("hidden");

        containerSelect?.classList.remove("hidden");

        if (subprocessoInput) {

            subprocessoInput.disabled = false;

            subprocessoInput.classList.remove(
                "bg-gray-100"
            );
        }
    }

    // =========================================
    // ESTADO VISUAL DA ÁREA
    // =========================================
    // =========================================
// ESTADO DOS CAMPOS POR TIPO
//
// PROCESSO
//   Habilitados:
//     Classificação
//     Macro N1
//     Macro N2
//     Área Responsável
//
//   Sempre bloqueados:
//     Gestor
//     Telefone
//     E-mail
//
// SUBPROCESSO / OUTRO
//   Todos os campos ficam bloqueados.
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

    // =========================================
    // PROCESSO
    // =========================================
    if (tipoAtual === "processo") {

        /*
         * O usuário pode definir as características
         * próprias do Processo.
         */
        camposEstruturais.forEach(
            HerancaProcesso.desbloquearCampo
        );

        /*
         * Os dados de contato são sempre derivados
         * da Área Responsável.
         */
        camposContato.forEach(
            HerancaProcesso.bloquearCampo
        );

        return;
    }

    // =========================================
    // SUBPROCESSO / OUTRO
    // =========================================
    /*
     * Esses tipos nunca definem diretamente suas
     * características estruturais ou de contato.
     *
     * Tudo vem do Processo Pai quando houver.
     */
    [
        ...camposEstruturais,
        ...camposContato
    ].forEach(
        HerancaProcesso.bloquearCampo
    );
}

    // =========================================
// HERANÇA DO PROCESSO PAI
//
// SOMENTE:
// - Classificação
// - Macroprocesso Nível 1
// - Macroprocesso Nível 2
// - Área Responsável
//
// Gestor / Telefone / E-mail pertencem
// exclusivamente à herança da Área.
// =========================================
window.aplicarRegraHeranca = function () {

    // =========================================
    // PROCESSO
    // =========================================
    if (tipoAtual === "processo") {

        /*
         * Processo não possui Processo Pai.
         *
         * Encerramos qualquer herança anterior.
         *
         * O método limpar() não apaga os valores.
         * A memória do Processo será restaurada
         * por restaurarEstado().
         */
        HerancaProcesso.limpar();

        /*
         * Processo pode editar:
         * - Classificação
         * - Macro N1
         * - Macro N2
         * - Área Responsável
         *
         * Gestor / Telefone / E-mail permanecem
         * bloqueados.
         */
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

        /*
         * Não existe herança do Processo Pai.
         *
         * Encerramos qualquer herança anterior.
         */
        HerancaProcesso.limpar();

        /*
         * Mesmo sem Pai, Subprocesso e Outro não
         * podem editar as características do Processo.
         */
        atualizarEstadoCamposPorTipo();

        return;
    }

    // =========================================
    // COM PROCESSO PAI
    // =========================================
    HerancaProcesso.aplicar(
        processoId,
        {
            url: urlHeranca,

            onApply: () => {

                /*
                 * A herança preenche:
                 * - Classificação
                 * - Macro N1
                 * - Macro N2
                 * - Área Responsável
                 *
                 * O retorno da herança NÃO altera:
                 * - Nome
                 * - Parent
                 * - memória do tipo.
                 */
                restaurarEstado(
                    tipoAtual
                );

                /*
                 * Garante que os campos continuem
                 * bloqueados para Subprocesso/Outro.
                 */
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

        // 1. Guarda estado anterior
        salvarEstado(tipoAnterior);

        // 2. Prepara estado destino
        prepararEstadoDestino(
            tipoAnterior,
            novoTipo
        );

        // 3. Atualiza tipo
        tipoAtual = novoTipo;

        // 4. Atualiza interface
        atualizarLabels();
        atualizarVisibilidadeCampos();
        atualizarEstadoCamposPorTipo();
        atualizarBotoes();

        // -----------------------------------------
        // LIMPA CARACTERÍSTICAS PRÓPRIAS DO PROCESSO
        //
        // Subprocesso/Outro não possuem características
        // estruturais próprias enquanto não houver Processo Pai.
        // -----------------------------------------
        if (
            tipoAtual === "subprocesso" ||
            tipoAtual === "outro"
        ) {

            limparCaracteristicasDaTela();
        }

        // 5. Restaura estado
        restaurarEstado(tipoAtual);

        // 6. Herança do Pai
        aplicarRegraHeranca();

        // 7. Nome oculto
        sincronizarNome();

        setTimeout(() => {
            window.isTrocandoTipo = false;
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

            if (tipoAtual !== "processo") {
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
    // EVENTO DA ÁREA
    //
    // SOMENTE PROCESSO
    //
    // A seleção da Área é feita pelo usuário.
    // O JS da Área será responsável por:
    //
    // Gestor
    // Telefone
    // E-mail
    // =========================================
    if (areaSelect) {

        $(areaSelect).on(
            "change.tipoProcessoMapear",
            function () {

                if (window.isTrocandoTipo) {
                    return;
                }

                if (tipoAtual !== "processo") {
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

                cacheEstados[tipoAtual].parent =
                    processoId;

                if (parentHidden) {
                    parentHidden.value =
                        processoId;
                }

                aplicarRegraHeranca();
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

        cacheEstados.processo.parent = "";

        cacheEstados.processo.area =
            obterAreaAtual();

    } else if (tipoAtual === "subprocesso") {

        cacheEstados.subprocesso.nome =
            subprocessoInput?.value || "";

        cacheEstados.subprocesso.parent =
            obterParentAtual();

    } else {

        cacheEstados.outro.nome =
            subprocessoInput?.value || "";

        cacheEstados.outro.parent =
            obterParentAtual();
    }

    atualizarLabels();
    atualizarVisibilidadeCampos();
    atualizarEstadoCamposPorTipo();
    atualizarBotoes();

    restaurarEstado(tipoAtual);
    aplicarRegraHeranca();
    sincronizarNome();
}