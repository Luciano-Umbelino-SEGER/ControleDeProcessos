function initAutoPreenchimentoArea(url) {

    const areaSelect = document.getElementById("id_area_responsavel");
    const gestorInput = document.getElementById("id_gestor");
    const telefoneInput = document.getElementById("id_telefone");
    const emailInput = document.getElementById("id_email");

    if (!areaSelect) return;

    function preencherCampos(areaId) {
        if (!areaId) {
            if (gestorInput) gestorInput.value = "";
            if (telefoneInput) telefoneInput.value = "";
            if (emailInput) emailInput.value = "";
            return;
        }

        fetch(`${url}?area_id=${areaId}`)
            .then(response => response.json())
            .then(data => {
                if (gestorInput) gestorInput.value = data.titular || "";
                if (telefoneInput) telefoneInput.value = data.telefone || "";
                if (emailInput) emailInput.value = data.email || "";
            })
            .catch(error => console.error("Erro ao buscar contato:", error));
    }

    // ✅ EVENTO UNIVERSAL (FUNCIONA COM SELECT2)
    areaSelect.addEventListener("change", function () {
        preencherCampos(this.value);
    });

    // ✅ GARANTE DISPARO APÓS SELECT2
    if (window.$) {
        $(areaSelect).on("change", function () {
            preencherCampos(this.value);
        });
    }

    // ✅ LOAD (EDIÇÃO) — COM DELAY PRA GARANTIR SELECT2
    setTimeout(() => {
        if (areaSelect.value) {
            preencherCampos(areaSelect.value);
        }
    }, 200);
}