// ===============================
// LINHA 2 - Processo / Subprocesso
// ===============================
document.addEventListener("DOMContentLoaded", function () {

    const rbProcesso = document.getElementById("rb_processo");
    const rbSubprocesso = document.getElementById("rb_subprocesso");

    const lblProcesso = document.getElementById("lbl_processo");
    const lblSubprocesso = document.getElementById("lbl_subprocesso");

    const lblCampoProcesso = document.getElementById("lbl_campo_processo");
    const lblCampoSubprocesso = document.getElementById("lbl_campo_subprocesso");

    const processoInputVisible = document.getElementById("processo_input_visible");
    const processoSelectContainer = document.getElementById("processo_select_container");
    const processoSelectVisible = document.getElementById("processo_select_visible");

    const parentField = document.getElementById("id_parent");
    const subprocessoField = document.getElementById("id_nome");


    // -----------------------------
    // FUNÇÃO: MODO PROCESSO
    // -----------------------------
    function setModeProcesso() {

        // rádio
        rbProcesso.checked = true;
        rbSubprocesso.checked = false;

        // cores dos textos
        lblProcesso.classList.replace("text-gray-400", "text-blue-700");
        lblSubprocesso.classList.replace("text-blue-700", "text-gray-400");

        lblCampoProcesso.classList.replace("text-gray-400", "text-blue-700");
        lblCampoSubprocesso.classList.replace("text-blue-700", "text-gray-400");

        // mostra INPUT / esconde SELECT
        processoInputVisible.classList.remove("hidden");
        processoSelectContainer.classList.add("hidden");

        // subprocesso fica DESABILITADO
        subprocessoField.disabled = true;
        subprocessoField.classList.add("bg-gray-200");

        // campo parent (django) é limpo e desabilitado
        parentField.value = "";
        parentField.disabled = true;
    }


    // -----------------------------
    // FUNÇÃO: MODO SUBPROCESSO
    // -----------------------------
    function setModeSubprocesso() {

        rbProcesso.checked = false;
        rbSubprocesso.checked = true;

        lblProcesso.classList.replace("text-blue-700", "text-gray-400");
        lblSubprocesso.classList.replace("text-gray-400", "text-blue-700");

        lblCampoProcesso.classList.replace("text-blue-700", "text-gray-400");
        lblCampoSubprocesso.classList.replace("text-gray-400", "text-blue-700");

        // Oculta o input e mostra o select
        processoInputVisible.classList.add("hidden");
        processoSelectContainer.classList.remove("hidden");

        // subprocesso ATIVADO
        subprocessoField.disabled = false;
        subprocessoField.classList.remove("bg-gray-200");

        // parentField agora é habilitado e receberá o processo selecionado
        parentField.disabled = false;

        // carregar processos pai via API
        fetch("/api/processos_pai/")
            .then(r => r.json())
            .then(data => {
                processoSelectVisible.innerHTML = "";
                data.processos_pai.forEach(p => {
                    const opt = document.createElement("option");
                    opt.value = p.id;
                    opt.textContent = p.nome;
                    processoSelectVisible.appendChild(opt);
                });
            });

        // sincronizar SELECT → parentField
        processoSelectVisible.addEventListener("change", function () {
            parentField.value = this.value;
        });
    }


    // ---------------------------------
    // EVENTOS DOS RÁDIOS
    // ---------------------------------
    rbProcesso.addEventListener("change", () => setModeProcesso());
    rbSubprocesso.addEventListener("change", () => setModeSubprocesso());


    // ---------------------------------
    // ESTADO INICIAL DA TELA
    // ---------------------------------
    if (parentField.value) {
        // Se existe parent → é subprocesso
        setModeSubprocesso();
    } else {
        // Senão → processo
        setModeProcesso();
    }

});
