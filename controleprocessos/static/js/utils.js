// ============================================================
// MAPA GLOBAL DE NOMES AMIGÁVEIS DE TABELAS
// ============================================================

const MAPA_TABELAS = {

    ProcessoMapear: "Processos a Mapear",
    Processo: "Processos",
    ModelagemProcesso: "Modelagem de Processos"

}

// ============================================================
// UTILITÁRIO GLOBAL — Verificação de Similaridade de Texto
// ============================================================

async function verificarSimilaridadeTexto({ tabelas, tabela, campo, valor, id }) {

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
                tabelas: tabelas || [tabela],
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

    inputElement.addEventListener("input", function () {

        removerAvisoSimilaridade(inputElement)

        const valor = inputElement.value.trim()

        if (!valor) return

        clearTimeout(timeout)

        timeout = setTimeout(async () => {

            const valor = inputElement.value.trim()

            if (valor.length < 3) return

            const resultado = await verificarSimilaridadeTexto({
                tabelas: config.tabelas,
                campo: config.campo,
                valor: valor,
                id: inputElement.dataset.similarityId || null
            })

            if (!resultado || !resultado.similar_encontrado) return

            let html = `<strong>⚠ Encontramos registros parecidos:</strong><br>`

            // Caso 1 — resposta antiga (array)
            if (Array.isArray(resultado.resultados)) {

                const lista = resultado.resultados.slice(0, 3)

                lista.forEach(item => {
                    html += `• ${item.texto} (${Math.round(item.score * 100)}%)<br>`
                })

            }

            // Caso 2 — resposta multi-tabela
            else {

                Object.entries(resultado.resultados).forEach(([tabela, itens]) => {

                    if (!itens.length) return

                    const titulo = MAPA_TABELAS[tabela] || tabela

                    html += `<br><strong>${titulo}</strong><br>`

                    itens.slice(0,3).forEach(item => {
                        html += `• ${item.texto} (${Math.round(item.score * 100)}%)<br>`
                    })

                })

            }

            mostrarAvisoSimilaridade(inputElement, html)

        }, 350) // ← tempo do debounce

    })

}

// ============================================================
// AUTO-INICIALIZAÇÃO GLOBAL
// Detecta campos com validação de similaridade automaticamente
// ============================================================

document.addEventListener("DOMContentLoaded", function () {

    const campos = document.querySelectorAll("[data-similarity-table], [data-similarity-tables]")

    campos.forEach(campo => {

        const tabela = campo.dataset.similarityTable
        const tabelas = campo.dataset.similarityTables
        const campoNome = campo.dataset.similarityField

        let listaTabelas = []

        if (tabelas) {
            listaTabelas = tabelas.split(",").map(t => t.trim())
        } else if (tabela) {
            listaTabelas = [tabela]
        }

        ativarValidacaoSimilaridade(campo, {
            tabelas: listaTabelas,
            campo: campoNome
        })

    })

})