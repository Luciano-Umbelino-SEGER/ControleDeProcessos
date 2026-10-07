document.addEventListener("DOMContentLoaded", () => {

    const funcionalidades = document.querySelectorAll(
        ".permissao-funcionalidade"
    );

    funcionalidades.forEach((funcionalidade) => {

        const checkboxFuncionalidade =
            funcionalidade.querySelector(
                ".checkbox-funcionalidade"
            );

        const checkboxesAcoes =
            funcionalidade.querySelectorAll(
                ".checkbox-acao"
            );

        /*
         * --------------------------------------------------
         * Checkbox da funcionalidade
         * --------------------------------------------------
         *
         * Marcar a funcionalidade:
         * → marca todas as ações.
         *
         * Desmarcar a funcionalidade:
         * → desmarca todas as ações.
         */
        checkboxFuncionalidade.addEventListener("change", () => {

            checkboxesAcoes.forEach((checkboxAcao) => {
                checkboxAcao.checked =
                    checkboxFuncionalidade.checked;
            });
        });

        /*
         * --------------------------------------------------
         * Checkboxes das ações
         * --------------------------------------------------
         *
         * Se qualquer ação estiver desmarcada:
         * → funcionalidade fica desmarcada.
         *
         * Se todas as ações estiverem marcadas:
         * → funcionalidade fica marcada.
         */
        checkboxesAcoes.forEach((checkboxAcao) => {

            checkboxAcao.addEventListener("change", () => {

                const todasMarcadas =
                    Array.from(checkboxesAcoes)
                        .every(
                            (checkbox) => checkbox.checked
                        );

                checkboxFuncionalidade.checked =
                    todasMarcadas;
            });
        });
    });
});