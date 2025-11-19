document.addEventListener("DOMContentLoaded", function () {

    const classificacaoSelect = document.getElementById("id_classificacao");
    const macro1Select = document.getElementById("id_macroprocesso_nivel1");
    const macro2Select = document.getElementById("id_macroprocesso_nivel2");

    // Utilitário: preencher select
    function populateSelect(selectElement, items, placeholder = "---------") {
        selectElement.innerHTML = `<option value="">${placeholder}</option>`;
        items.forEach(item => {
            selectElement.innerHTML += `<option value="${item.id}">${item.nome}</option>`;
        });
    }

    // Carrega todos Macro 2 (usado quando o usuário limpa Macro 1)
    function loadAllMacro2() {
        fetch(`/api/macro2_todos/`)
            .then(r => r.json())
            .then(data => {
                populateSelect(macro2Select, data.macro2);
            });
    }

    // ------------------------------------------------------------
    // 1. Seleção de Classificação
    // ------------------------------------------------------------
    if (classificacaoSelect) {
        classificacaoSelect.addEventListener("change", function () {
            const classificacaoId = this.value;

            if (!classificacaoId) {
                // reset Macro 1 e Macro 2
                fetch(`/api/macro1_todos/`).then(r => r.json()).then(data => {
                    populateSelect(macro1Select, data.macro1);
                });
                loadAllMacro2();
                return;
            }

            // Carregar Macroprocesso Nivel 1 da Classificação
            fetch(`/api/macroprocessos_por_classificacao/${classificacaoId}/`)
                .then(r => r.json())
                .then(data => {
                    populateSelect(macro1Select, data.macroprocessos);
                    macro2Select.innerHTML = `<option value="">---------</option>`;
                });
        });
    }

    // ------------------------------------------------------------
    // 2. Seleção de Macroprocesso Nível 1
    // ------------------------------------------------------------
    if (macro1Select) {
        macro1Select.addEventListener("change", function () {
            const macro1Id = this.value;

            // Se Macro 1 foi limpo
            if (!macro1Id) {
                loadAllMacro2();
                classificacaoSelect.value = "";
                return;
            }

            // Buscar Classificação associada ao Macro 1
            fetch(`/api/classificacao_por_macro1/${macro1Id}/`)
                .then(r => r.json())
                .then(data => {

                    // Agora a API devolve classificacao_id ✔
                    if (data.classificacao_id) {
                        classificacaoSelect.value = data.classificacao_id;
                    }
                });

            // Buscar Macroprocessos de Nível 2 para esse Macro 1
            fetch(`/api/macro2_por_macro1/${macro1Id}/`)
                .then(r => r.json())
                .then(data => {
                    populateSelect(macro2Select, data.macro2);
                });
        });
    }

    // ------------------------------------------------------------
    // 3. Seleção de Macroprocesso Nível 2
    // ------------------------------------------------------------
    if (macro2Select) {
        macro2Select.addEventListener("change", function () {
            const macro2Id = this.value;

            if (!macro2Id) return;

            // Buscar Macro 1 + Classificação associados ao Macro 2
            fetch(`/api/macro1_e_classificacao_por_macro2/${macro2Id}/`)
                .then(r => r.json())
                .then(data => {

                    // Atualizar Macro 1
                    if (data.macroprocesso_nivel1) {
                        macro1Select.value = data.macroprocesso_nivel1.id;
                    }

                    // Atualizar Classificação
                    if (data.classificacao) {
                        classificacaoSelect.value = data.classificacao.id;
                    }
                });
        });
    }

});
