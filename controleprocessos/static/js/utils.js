async function verificarSimilaridade(tabela, campo, valor, inputId){

    if(!valor || valor.length < 3){
        return
    }

    const response = await fetch(
        `/utils/verificar-similaridade/?tabela=${tabela}&campo=${campo}&valor=${encodeURIComponent(valor)}`
    )

    const data = await response.json()

    if(data.encontrado){

        const confirmar = confirm(
            `Já existe um registro parecido (${data.percentual}%):\n\n"${data.valor}"\n\nDeseja manter o nome informado?`
        )

        if(!confirmar){
            document.getElementById(inputId).value = ""
            document.getElementById(inputId).focus()
        }
    }
}