document.addEventListener('DOMContentLoaded', function () {
    const classificacaoSelect = document.getElementById('id_classificacao');
    const macro1Select = document.getElementById('id_macroprocesso_nivel1');
    const macro2Select = document.getElementById('id_macroprocesso_nivel2');
    const modelagemSelect = document.getElementById('id_modelagem_processo');

    // Filtro dinâmico: Classificação -> Macroprocesso Nível 1
    classificacaoSelect.addEventListener('change', function () {
        const classificacaoId = this.value;
        fetch(`/api/macroprocessos_por_classificacao/${classificacaoId}/`)
            .then(response => response.json())
            .then(data => {
                macro1Select.innerHTML = '<option value="">Selecione...</option>';
                data.macroprocessos.forEach(m => {
                    macro1Select.innerHTML += `<option value="${m.id}">${m.nome}</option>`;
                });
            });
    });

    // Filtro dinâmico: Macroprocesso Nível 1 -> Macroprocesso Nível 2
    macro1Select.addEventListener('change', function () {
        const macro1Id = this.value;
        fetch(`/api/macroprocessos_por_classificacao/${macro1Id}/`) // Ajustar endpoint se necessário
            .then(response => response.json())
            .then(data => {
                macro2Select.innerHTML = '<option value="">Selecione...</option>';
                data.macroprocessos.forEach(m => {
                    macro2Select.innerHTML += `<option value="${m.id}">${m.nome}</option>`;
                });
            });
    });

    // Preenchimento automático ao selecionar Modelagem de Processo
    modelagemSelect.addEventListener('change', function () {
        const selectedOption = this.options[this.selectedIndex];
        document.getElementById('tema_modelo').value = selectedOption.dataset.tema || '';
        document.getElementById('versao_modelo').value = selectedOption.dataset.versao || '';
        document.getElementById('emitente_modelo').value = selectedOption.dataset.emitente || '';
        document.getElementById('sistema_modelo').value = selectedOption.dataset.sistema || '';
        document.getElementById('vigencia_modelo').value = selectedOption.dataset.vigencia || '';
    });

    // Preenchimento automático ao selecionar Norma de Procedimento
    const normaSelect = document.getElementById('norma_procedimento');
    normaSelect.addEventListener('change', function () {
        const selectedOption = this.options[this.selectedIndex];
        document.getElementById('tema_norma').value = selectedOption.dataset.tema || '';
        document.getElementById('versao_norma').value = selectedOption.dataset.versao || '';
        document.getElementById('emitente_norma').value = selectedOption.dataset.emitente || '';
        document.getElementById('sistema_norma').value = selectedOption.dataset.sistema || '';
        document.getElementById('vigencia_norma').value = selectedOption.dataset.vigencia || '';
    });
});