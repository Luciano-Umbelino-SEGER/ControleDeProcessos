function initAutoPreenchimentoArea(url) {

    const areaSelect = document.getElementById("id_area_responsavel");
    const gestorInput = document.getElementById("id_gestor");
    const telefoneInput = document.getElementById("id_telefone");
    const emailInput = document.getElementById("id_email");
    const parentInput = document.getElementById("id_parent");

    if (!areaSelect) return;


    /* =========================
       PREENCHER CAMPOS
    ========================= */
    function preencherCampos(areaId) {

        const tipo = document.querySelector('input[name="tipo"]:checked')?.value;

        // 🔥 HERANÇA MANDA
        if (tipo !== "processo" && parentInput && parentInput.value) {
            return;
        }

        if (!areaId) {
            ["id_gestor","id_telefone","id_email"].forEach(id => {
                HerancaProcesso.desbloquearCampo(id)
            })
            return;
        }

        fetch(`${url}?area_id=${areaId}`)
            .then(response => response.json())
            .then(data => {

                if (gestorInput) gestorInput.value = data.titular || "";
                if (telefoneInput) telefoneInput.value = data.telefone || "";
                if (emailInput) emailInput.value = data.email || "";

                // 🔥 REUTILIZA HERANÇA
                ["id_gestor","id_telefone","id_email"].forEach(id => {
                    HerancaProcesso.bloquearCampo(id)
                })

            })
            .catch(error => console.error("Erro ao buscar contato:", error));
    }

    /* =========================
       EVENTO CHANGE
    ========================= */
    areaSelect.addEventListener("change", function () {
        const areaId = this.value;

        preencherCampos(areaId);

        // 🔥 GARANTIA ABSOLUTA
        if (areaId) {
            bloquearContato();
        } else {
            liberarContato();
        }

    });

    if (window.$) {
        $(areaSelect).on("change", function () {
            preencherCampos(this.value);
        });
    }

    /* =========================
       LOAD (EDIÇÃO)
    ========================= */
    // 🔥 Estado inicial seguro (sem interferir na herança)
    setTimeout(() => {

        const tipo = document.querySelector('input[name="tipo"]:checked')?.value;

        // 🔵 HERANÇA tem prioridade total
        if (tipo !== "processo" && parentInput && parentInput.value) {
            return;
        }

        // 🟢 só aplica área se NÃO houver parent
        if (areaSelect.value) {
            preencherCampos(areaSelect.value);
        }

    }, 200);
}