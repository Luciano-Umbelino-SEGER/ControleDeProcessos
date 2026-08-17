/* =========================================================
   HERANÇA DE PROCESSO — CORE REUTILIZÁVEL
   ========================================================= */

window.HerancaProcesso = (function () {

    /*
     * =====================================================
     * CAMPOS DA HERANÇA DO PROCESSO PAI
     *
     * O Processo Pai fornece:
     *
     *   Classificação
     *   Macroprocesso Nível 1
     *   Macroprocesso Nível 2
     *   Área Responsável
     *
     * Gestor / Telefone / E-mail NÃO pertencem aqui.
     * =====================================================
     */
    const CAMPOS_HERANCA_PAI = [
        "id_classificacao",
        "id_macroprocesso_nivel1",
        "id_macroprocesso_nivel2",
        "id_area_responsavel"
    ];

    /*
     * =====================================================
     * CAMPOS DA HERANÇA DA ÁREA
     *
     * Estes campos pertencem exclusivamente à Área
     * Responsável.
     *
     * Este JS NÃO os hidrata.
     *
     * O responsável por isso é:
     *
     *     auto_preenchimento_area.js
     * =====================================================
     */
    const CAMPOS_HERANCA_AREA = [
        "id_gestor",
        "id_telefone",
        "id_email"
    ];

    /*
     * =====================================================
     * CONTROLE DE REQUISIÇÕES
     *
     * Impede que uma resposta antiga de um Processo Pai
     * altere a tela depois que o usuário já mudou de tipo
     * ou selecionou outro Pai.
     * =====================================================
     */
    let requisicaoAtual = 0;


    /* =====================================================
       SAFE jQuery
       ===================================================== */

    function hasJQuery() {
        return typeof window.$ !== "undefined";
    }


    /* =====================================================
       SET SELECT
       ===================================================== */

    function setSelect(id, value, dispararChange = true) {

        if (hasJQuery()) {

            const el = $("#" + id);

            if (!el.length) {
                return;
            }

            if (el.hasClass("select2-hidden-accessible")) {

                el.val(value || null);

                if (dispararChange) {
                    el.trigger("change");
                }

            } else {

                el.val(value || "");

                if (dispararChange) {
                    el.trigger("change");
                }
            }

        } else {

            const el = document.getElementById(id);

            if (!el) {
                return;
            }

            el.value = value || "";

            if (dispararChange) {

                el.dispatchEvent(
                    new Event("change", {
                        bubbles: true
                    })
                );
            }
        }
    }


    /* =====================================================
       SET INPUT
       ===================================================== */

    function setInput(id, value) {

        const el = document.getElementById(id);

        if (!el) {
            return;
        }

        el.value = value || "";
    }


    /* =====================================================
       BLOQUEIO
       ===================================================== */

    function bloquearCampo(id) {

        const el = document.getElementById(id);

        if (!el) {
            return;
        }

        /*
         * Inputs:
         * readonly
         *
         * SELECTs:
         * não usamos disabled porque precisam continuar
         * participando do POST.
         */
        if (el.tagName !== "SELECT") {
            el.readOnly = true;
        }

        el.classList.add("campo-herdado");


        /*
         * Select2
         */
        if (
            window.$ &&
            $(el).hasClass("select2-hidden-accessible")
        ) {

            $(el)
                .next(".select2-container")
                .addClass("campo-herdado")
                .css(
                    "pointer-events",
                    "none"
                );
        }
    }


    /* =====================================================
       DESBLOQUEIO
       ===================================================== */

    function desbloquearCampo(id) {

        const el = document.getElementById(id);

        if (!el) {
            return;
        }

        if (el.tagName !== "SELECT") {
            el.readOnly = false;
        }

        el.classList.remove("campo-herdado");


        /*
         * Select2
         */
        if (
            window.$ &&
            $(el).hasClass("select2-hidden-accessible")
        ) {

            $(el)
                .next(".select2-container")
                .removeClass("campo-herdado")
                .css(
                    "pointer-events",
                    ""
                );
        }
    }


    /* =====================================================
       LIMPAR CAMPO
       ===================================================== */

    function limparCampo(id) {

        if (hasJQuery()) {

            const el = $("#" + id);

            if (!el.length) {
                return;
            }

            if (el.is("select")) {

                el.val(null)
                    .trigger("change");

            } else {

                el.val("");
            }

        } else {

            const el =
                document.getElementById(id);

            if (!el) {
                return;
            }

            el.value = "";
        }
    }


    /* =====================================================
       INVALIDAR REQUISIÇÃO ATUAL
       ===================================================== */

    function invalidarRequisicao() {
        requisicaoAtual++;
    }


    /* =====================================================
       APLICAR HERANÇA DO PROCESSO PAI
       ===================================================== */

    function aplicar(
        processoId,
        options = {}
    ) {

        if (!processoId) {
            return;
        }

        const url = options.url;

        if (!url) {
            console.error(
                "URL da herança do Processo Pai não informada."
            );

            return;
        }

        /*
         * Cada chamada recebe um número próprio.
         *
         * Somente a requisição mais recente poderá
         * alterar a tela.
         */
        const numeroRequisicao =
            ++requisicaoAtual;

        const endpoint =
            url.replace(
                /\/0\//,
                `/${processoId}/`
            );

        fetch(endpoint)
            .then(response => {

                if (!response.ok) {
                    throw new Error(
                        `Erro HTTP ${response.status}`
                    );
                }

                return response.json();
            })
            .then(data => {

                /*
                 * A requisição deixou de ser válida.
                 *
                 * Isso acontece, por exemplo, quando:
                 *
                 * Subprocesso → Processo
                 *
                 * antes do retorno do fetch.
                 */
                if (
                    numeroRequisicao !==
                    requisicaoAtual
                ) {
                    return;
                }


                /*
                 * =========================================
                 * HERANÇA DO PROCESSO PAI
                 * =========================================
                 */

                setSelect(
                    "id_classificacao",
                    data.classificacao
                );

                setSelect(
                    "id_macroprocesso_nivel1",
                    data.macro1
                );

                setSelect(
                    "id_macroprocesso_nivel2",
                    data.macro2
                );

                setSelect(
                    "id_area_responsavel",
                    data.area
                );


                /*
                 * =========================================
                 * IMPORTANTE
                 *
                 * Gestor
                 * Telefone
                 * E-mail
                 *
                 * NÃO são preenchidos aqui.
                 *
                 * Esses campos pertencem à segunda
                 * herança:
                 *
                 * Área Responsável.
                 * =========================================
                 */


                /*
                 * =========================================
                 * SINCRONIZA HIDDEN PARENT
                 * =========================================
                 */
                const hiddenParent =
                    document.getElementById(
                        "id_parent"
                    );

                if (hiddenParent) {
                    hiddenParent.value =
                        processoId;
                }


                /*
                 * =========================================
                 * BLOQUEIA CAMPOS HERDADOS DO PAI
                 * =========================================
                 */
                CAMPOS_HERANCA_PAI.forEach(
                    bloquearCampo
                );


                /*
                 * =========================================
                 * CALLBACK
                 * =========================================
                 */
                if (
                    typeof options.onApply ===
                    "function"
                ) {

                    options.onApply(data);
                }

            })
            .catch(error => {

                /*
                 * Ignora erros decorrentes de uma
                 * requisição que já deixou de ser válida.
                 */
                if (
                    numeroRequisicao !==
                    requisicaoAtual
                ) {
                    return;
                }

                console.error(
                    "Erro herança do Processo Pai:",
                    error
                );
            });
    }


    /* =====================================================
       LIMPAR / ENCERRAR HERANÇA DO PROCESSO PAI
       ===================================================== */

    function limpar(options = {}) {

        /*
         * Primeiro invalidamos qualquer fetch anterior.
         *
         * Assim uma resposta atrasada não poderá
         * repovoar a tela.
         */
        invalidarRequisicao();


        /*
         * Desbloqueia somente os campos que pertencem
         * à herança do Processo Pai.
         */
        CAMPOS_HERANCA_PAI.forEach(
            desbloquearCampo
        );


        /*
         * Por padrão NÃO mexemos nos valores.
         *
         * Quem decide qual valor deve permanecer ou ser
         * restaurado é o controlador do tipo:
         *
         *     tipo_processo_mapear.js
         *
         * Isso é importante para preservar a memória
         * específica de cada tipo.
         */
        if (
            typeof options.onClear ===
            "function"
        ) {

            options.onClear();
        }
    }


    /* =====================================================
       API PÚBLICA
       ===================================================== */

    return {

        aplicar,
        limpar,
        bloquearCampo,
        desbloquearCampo
    };

})();