/* =========================================================
   Macro Classificação Engine v2
   ---------------------------------------------------------
   Comportamento estrutural bidirecional:

   Relação:
   Classificação
       └── Macro N1
             └── Macro N2

   Regras:
   - Pode iniciar seleção por qualquer nível
   - Reset inteligente:
        N2 = '---' → não altera N1 nem Classificação
        N1 = '---' → reseta N2 apenas
        Classificação = '---' → reseta N1 e N2
   - Não permite incoerência estrutural
   - Estado inicial mostra todos
   ========================================================= */
function initMacroClassificacao(config = {}) {

    const classificacaoSelect = document.getElementById(config.classificacaoId || "id_classificacao");
    const macro1Select        = document.getElementById(config.macro1Id || "id_macroprocesso_nivel_1");
    const macro2Select        = document.getElementById(config.macro2Id || "id_macroprocesso_nivel_2");

    if (!classificacaoSelect || !macro1Select || !macro2Select) {
        console.warn("Macro Engine: campos não encontrados.");
        return;
    }

    const modoBloqueado = config.modoBloqueado || false;

    /* =====================================================
       Helpers
    ====================================================== */

    function getSelected(select) {
        return select.value || null;
    }

    function resetSelect(select) {
        select.value = "";
    }

    function showAllOptions(select) {
        Array.from(select.options).forEach(opt => opt.hidden = false);
    }

    function filterOptions(select, predicate) {
        Array.from(select.options).forEach(opt => {
            if (!opt.value) return;
            opt.hidden = !predicate(opt);
        });
    }

    /* =====================================================
       Core Update Engine
    ====================================================== */

    function rebuildFromClassificacao() {

        const classificacaoId = getSelected(classificacaoSelect);

        if (!classificacaoId) {
            showAllOptions(macro1Select);
            showAllOptions(macro2Select);
            resetSelect(macro1Select);
            resetSelect(macro2Select);
            return;
        }

        // Filtra N1
        filterOptions(macro1Select, opt =>
            opt.dataset.classificacao === classificacaoId
        );

        resetSelect(macro1Select);
        resetSelect(macro2Select);
        showAllOptions(macro2Select);
    }

    function rebuildFromMacro1() {

        const macro1Id = getSelected(macro1Select);

        if (!macro1Id) {
            resetSelect(macro2Select);
            showAllOptions(macro2Select);
            return;
        }

        const selectedOption = macro1Select.selectedOptions[0];
        const classificacaoId = selectedOption.dataset.classificacao;

        // Sincroniza Classificação automaticamente
        classificacaoSelect.value = classificacaoId;

        // Filtra N1 coerente com Classificação
        filterOptions(macro1Select, opt =>
            opt.dataset.classificacao === classificacaoId
        );

        // Filtra N2
        filterOptions(macro2Select, opt =>
            opt.dataset.macro1 === macro1Id
        );

        resetSelect(macro2Select);
    }

    function rebuildFromMacro2() {

        const macro2Id = getSelected(macro2Select);

        if (!macro2Id) {
            return; // N2 vazio não altera esquerda
        }

        const selectedOption = macro2Select.selectedOptions[0];

        const macro1Id = selectedOption.dataset.macro1;
        const classificacaoId = selectedOption.dataset.classificacao;

        // Define coerência completa
        classificacaoSelect.value = classificacaoId;
        macro1Select.value = macro1Id;

        // Filtra N1 coerente
        filterOptions(macro1Select, opt =>
            opt.dataset.classificacao === classificacaoId
        );

        // Filtra N2 coerente
        filterOptions(macro2Select, opt =>
            opt.dataset.macro1 === macro1Id
        );
    }

    /* =====================================================
       Eventos
    ====================================================== */

    if (!modoBloqueado) {

        classificacaoSelect.addEventListener("change", () => {
            rebuildFromClassificacao();
        });

        macro1Select.addEventListener("change", () => {
            rebuildFromMacro1();
        });

        macro2Select.addEventListener("change", () => {
            rebuildFromMacro2();
        });
    }

    /* =====================================================
       Inicialização
    ===================================================== */

    showAllOptions(macro1Select);
    showAllOptions(macro2Select);

}