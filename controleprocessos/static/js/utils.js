// ============================================================
// UTILITÁRIO GLOBAL — Verificação de Similaridade de Texto
// ============================================================

async function verificarSimilaridadeTexto({ tabela, campo, valor, id }) {

    if (!valor || valor.trim().length < 3) {
        return null
    }

    try {

        const response = await fetch("/utils/text-similarity/", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": getCSRFToken()
            },
            body: JSON.stringify({
                tabela: tabela,
                campo: campo,
                valor: valor,
                id: id || null
            })
        })

        if (!response.ok) {
            console.error("Erro ao verificar similaridade")
            return null
        }

        const data = await response.json()

        return data

    } catch (error) {

        console.error("Erro na verificação de similaridade:", error)
        return null

    }
}


// ============================================================
// CSRF helper
// ============================================================

function getCSRFToken() {

    const name = "csrftoken"

    const cookies = document.cookie.split(";")

    for (let cookie of cookies) {

        cookie = cookie.trim()

        if (cookie.startsWith(name + "=")) {
            return cookie.substring(name.length + 1)
        }
    }

    return ""
}


// ============================================================
// AVISO VISUAL DE SIMILARIDADE
// ============================================================

function mostrarAvisoSimilaridade(inputElement, texto) {

    removerAvisoSimilaridade(inputElement)

    const aviso = document.createElement("div")

    aviso.className =
        "text-sm text-orange-700 bg-orange-50 border border-orange-300 rounded px-3 py-2 mt-1"

    aviso.innerHTML = texto

    aviso.dataset.similarityWarning = "true"

    inputElement.parentNode.appendChild(aviso)
}

function removerAvisoSimilaridade(inputElement) {

    const parent = inputElement.parentNode

    const aviso = parent.querySelector("[data-similarity-warning]")

    if (aviso) {
        aviso.remove()
    }
}


// ============================================================
// FUNÇÃO GLOBAL PARA CAMPOS DE TEXTO
// ============================================================

function ativarValidacaoSimilaridade(inputElement, config) {

    if (!inputElement) return

    let timeout = null

    inputElement.addEventListener("keyup", function () {

        removerAvisoSimilaridade(inputElement)

        const valor = inputElement.value.trim()

        if (!valor) return

        clearTimeout(timeout)

        timeout = setTimeout(async () => {

            const valor = inputElement.value.trim()

            if (valor.length < 3) return

            const resultado = await verificarSimilaridadeTexto({
                tabela: config.tabela,
                campo: config.campo,
                valor: valor,
                id: inputElement.dataset.similarityId || null
            })

            if (!resultado || !resultado.similar_encontrado) return

            const lista = resultado.resultados.slice(0, 3)

            let html = `<strong>⚠ Encontramos registros parecidos:</strong><br>`

            lista.forEach(item => {
                html += `• ${item.texto} (${Math.round(item.score * 100)}%)<br>`
            })

            mostrarAvisoSimilaridade(inputElement, html)

        }, 600)

    })

}


// ============================================================
// AUTO-INICIALIZAÇÃO GLOBAL
// Detecta campos com validação de similaridade automaticamente
// ============================================================

document.addEventListener("DOMContentLoaded", function () {

    const campos = document.querySelectorAll("[data-similarity-table]")

    campos.forEach(campo => {

        const tabela = campo.dataset.similarityTable
        const campoNome = campo.dataset.similarityField

        ativarValidacaoSimilaridade(campo, {
            tabela: tabela,
            campo: campoNome
        })

    })

})