/* =========================================================
   HERANÇA DE PROCESSO — CORE REUTILIZÁVEL (VERSÃO ESTÁVEL)
   ========================================================= */

window.HerancaProcesso = (function () {

    const CAMPOS_PADRAO = [
        "id_classificacao",
        "id_macroprocesso_nivel1",
        "id_macroprocesso_nivel2",
        "id_area_responsavel",
        "id_gestor",
        "id_telefone",
        "id_email"
    ]

    /* =========================
       SAFE jQuery (não quebra se $ não existir)
    ========================= */
    function hasJQuery() {
        return typeof window.$ !== "undefined"
    }

    /* =========================
       SET SELECT
    ========================= */
    function setSelect(id, value) {

        if (hasJQuery()) {
            const el = $('#' + id)
            if (!el.length) return

            el.val(value).trigger('change')
        } else {
            const el = document.getElementById(id)
            if (!el) return

            el.value = value
        }
    }

    /* =========================
       SET INPUT
    ========================= */
    function setInput(id, value) {
        const el = document.getElementById(id)
        if (!el) return

        el.value = value || ''
    }

    /* =========================
       BLOQUEIO (compatível com select2)
    ========================= */
    function bloquearCampo(id) {

        const el = document.getElementById(id);
        if (!el) return;

        // Inputs continuam readonly
        if (el.tagName !== "SELECT") {
            el.readOnly = true;
        }

        // Nunca desabilitar SELECTs.
        // Eles precisam continuar sendo enviados no POST.
        el.classList.add("campo-herdado");

        // Select2
        if (window.$ && $(el).hasClass("select2-hidden-accessible")) {
            $(el)
                .next(".select2-container")
                .addClass("campo-herdado")
                .css("pointer-events", "none");
        }
    }

    /* =========================
       DESBLOQUEIO
    ========================= */
    function desbloquearCampo(id) {

        const el = document.getElementById(id);
        if (!el) return;

        if (el.tagName !== "SELECT") {
            el.readOnly = false;
        }

        el.classList.remove("campo-herdado");

        if (window.$ && $(el).hasClass("select2-hidden-accessible")) {
            $(el)
                .next(".select2-container")
                .removeClass("campo-herdado")
                .css("pointer-events", "");
        }
    }

    /* =========================
       LIMPAR VALORES
    ========================= */
    function limparCampo(id) {

        if (hasJQuery()) {
            const el = $('#' + id)
            if (!el.length) return

            if (el.is("select")) {
                el.val(null).trigger('change')
            } else {
                el.val('')
            }
        } else {
            const el = document.getElementById(id)
            if (!el) return

            el.value = ''
        }
    }

    /* =========================
       APLICAR HERANÇA
    ========================= */
    function aplicar(processoId, options = {}) {

        if (!processoId) return

        const url = options.url

        const endpoint = url.replace(/\/0\//, `/${processoId}/`)

        fetch(endpoint)
            .then(r => r.json())
            .then(data => {
                setSelect("id_classificacao", data.classificacao)
                setSelect("id_macroprocesso_nivel1", data.macro1)
                setSelect("id_macroprocesso_nivel2", data.macro2)
                setSelect("id_area_responsavel", data.area)

                setInput("id_gestor", data.gestor)
                setInput("id_telefone", data.telefone)
                setInput("id_email", data.email)

                // 🔥 sincroniza hidden
                const hiddenParent = document.getElementById("id_parent")
                if (hiddenParent) {
                    hiddenParent.value = processoId
                }

                CAMPOS_PADRAO.forEach(bloquearCampo)

                if (typeof options.onApply === "function") {
                    options.onApply(data)
                }

            })
            .catch(err => console.error("Erro herança:", err))
    }

    /* =========================
       LIMPAR HERANÇA
    ========================= */
    function limpar(options = {}) {

        CAMPOS_PADRAO.forEach(id => {
            desbloquearCampo(id)
        })

        if (typeof options.onClear === "function") {
            options.onClear()
        }
    }

    return {
        aplicar,
        limpar,
        bloquearCampo,
        desbloquearCampo
    }

})();