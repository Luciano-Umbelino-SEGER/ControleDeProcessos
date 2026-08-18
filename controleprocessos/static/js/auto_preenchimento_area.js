function initAutoPreenchimentoArea(url) {

    const areaSelect =
        document.getElementById("id_area_responsavel");

    const gestorInput =
        document.getElementById("id_gestor");

    const telefoneInput =
        document.getElementById("id_telefone");

    const emailInput =
        document.getElementById("id_email");

    const parentInput =
        document.getElementById("id_parent");

    if (!areaSelect) {
        return;
    }


    /* =====================================================
       PREENCHER CAMPOS DA ÁREA
       ===================================================== */

    function preencherCampos(areaId, forcar = false) {

        /*
         * Sem Área não há o que hidratar.
         */
        if (!areaId) {
            return;
        }

        const tipo =
            document.querySelector(
                'input[name="tipo"]:checked'
            )?.value;

        /*
         * =================================================
         * REGRA DE NEGÓCIO
         *
         * Processo:
         *   Área escolhida pelo usuário.
         *
         * Subprocesso / Outro:
         *   Área normalmente vem do Processo Pai.
         *
         *   Nesse caso, a hidratação só é permitida
         *   quando forcar = true.
         * =================================================
         */
        if (
            !forcar &&
            tipo !== "processo"
        ) {
            return;
        }

        /*
         * Guarda a Área que originou esta consulta.
         *
         * Se o usuário trocar a Área antes do retorno,
         * a resposta antiga será descartada.
         */
        const areaSolicitada =
            String(areaId);

        fetch(
            `${url}?area_id=${areaSolicitada}`
        )
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
                 * =================================================
                 * PROTEÇÃO CONTRA RESPOSTA OBSOLETA
                 * =================================================
                 */
                const areaAtual =
                    areaSelect?.value || "";

                if (
                    String(areaAtual) !==
                    areaSolicitada
                ) {
                    return;
                }

                /*
                 * =================================================
                 * HIDRATAÇÃO
                 * =================================================
                 */
                if (gestorInput) {
                    gestorInput.value =
                        data.titular || "";
                }

                if (telefoneInput) {
                    telefoneInput.value =
                        data.telefone || "";
                }

                if (emailInput) {
                    emailInput.value =
                        data.email || "";
                }

                /*
                 * =================================================
                 * GESTOR / TELEFONE / E-MAIL
                 * =================================================
                 *
                 * Esses campos são sempre derivados da Área.
                 */
                [
                    "id_gestor",
                    "id_telefone",
                    "id_email"
                ].forEach(
                    id =>
                        HerancaProcesso.bloquearCampo(id)
                );
            })
            .catch(error => {

                console.error(
                    "Erro ao buscar contato da Área:",
                    error
                );
            });
    }


    /* =====================================================
       PONTE PARA A HERANÇA DO PROCESSO PAI
       ===================================================== */

    window.preencherCamposArea =
        function (areaId, forcar = false) {

            preencherCampos(
                areaId,
                forcar
            );
        };


    /* =====================================================
       EVENTO CHANGE — INPUT NATIVO
       ===================================================== */

    areaSelect.addEventListener(
        "change",
        function () {

            const tipo =
                document.querySelector(
                    'input[name="tipo"]:checked'
                )?.value;

            /*
             * Nos tipos Subprocesso/Outro, a Área não
             * é escolhida manualmente pelo usuário.
             *
             * A hidratação nesses casos acontece através
             * da ponte da herança do Processo Pai.
             */
            if (
                tipo !== "processo"
            ) {
                return;
            }

            preencherCampos(
                this.value,
                false
            );
        }
    );


    /* =====================================================
       EVENTO CHANGE — SELECT2
       ===================================================== */

    if (window.$) {

        $(areaSelect).on(
            "change.autoPreenchimentoArea",
            function () {

                const tipo =
                    document.querySelector(
                        'input[name="tipo"]:checked'
                    )?.value;

                if (
                    tipo !== "processo"
                ) {
                    return;
                }

                preencherCampos(
                    $(this).val(),
                    false
                );
            }
        );
    }


    /* =====================================================
       LOAD — EDIÇÃO
       ===================================================== */

    setTimeout(() => {

        const tipo =
            document.querySelector(
                'input[name="tipo"]:checked'
            )?.value;

        /*
         * Em Subprocesso/Outro, se houver Área,
         * ela veio do Processo Pai.
         *
         * A hidratação será feita pela herança do Pai.
         */
        if (
            tipo !== "processo"
        ) {
            return;
        }

        /*
         * No modo Processo, se já houver Área,
         * hidrata os dados existentes.
         */
        if (areaSelect.value) {

            preencherCampos(
                areaSelect.value,
                false
            );
        }

    }, 200);
}