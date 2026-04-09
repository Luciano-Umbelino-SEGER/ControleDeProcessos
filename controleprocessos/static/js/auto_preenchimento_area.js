function initAutoPreenchimentoArea(url) {

    const areaSelect = document.getElementById("id_area_responsavel");
    const gestorInput = document.querySelector("[name='gestor']");
    const telefoneInput = document.querySelector("[name='telefone']");
    const emailInput = document.querySelector("[name='email']");

    if (!areaSelect) return;

    function preencherCampos(nomeArea) {
        if (!nomeArea) return;

        fetch(`${url}?nome_area=${encodeURIComponent(nomeArea)}`)
            .then(response => {
                if (!response.ok) throw new Error("Erro HTTP " + response.status);
                return response.json();
            })
            .then(data => {
                if (gestorInput) gestorInput.value = data.titular || "";
                if (telefoneInput) telefoneInput.value = data.telefone || "";
                if (emailInput) emailInput.value = data.email || "";
            })
            .catch(error => console.error("Erro ao buscar contato:", error));
    }

    // change
    areaSelect.addEventListener("change", function () {
        preencherCampos(this.value);
    });

    // load (edição)
    if (areaSelect.value) {
        preencherCampos(areaSelect.value);
    }
}