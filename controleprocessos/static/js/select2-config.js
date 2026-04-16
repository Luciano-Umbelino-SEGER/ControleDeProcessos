function initSelect2(selector, customOptions = {}) {

    const defaultOptions = {
        width: '100%',
        allowClear: false,
        minimumInputLength: 0,

        language: {
            inputTooShort: () => "Digite pelo menos 2 caracteres",
            noResults: () => "Nenhum resultado encontrado",
            searching: () => "Buscando..."
        }
    };

    const config = {
        ...defaultOptions,
        ...customOptions
    };

    const el = $(selector);

    if (el.length) {
        el.select2(config);

        // 🔥 Trata valor inicial (edição)
        const valorInicial = el.val();
        const textoInicial = el.find("option:selected").text();

        if (valorInicial && textoInicial) {
            const option = new Option(textoInicial, valorInicial, true, true);
            el.append(option).trigger('change');
        }
    }
}