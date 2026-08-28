/* ============================================================
   CLASSIFICAÇÃO DE MACROPROCESSOS
   Controle da imagem da Classificação
   ============================================================ */
function initClassificacaoMacroprocessoImagem() {

    const dropzone = document.getElementById('imagem-dropzone');
    const input = document.getElementById('imagem');
    const preview = document.getElementById('imagem-preview');
    const placeholder = document.getElementById('imagem-placeholder');
    const error = document.getElementById('imagem-error');

    if (!dropzone || !input) {
        return;
    }

    /* ========================================================
       CONFIGURAÇÕES
       ======================================================== */
    const tiposPermitidos = ['image/jpeg', 'image/png', 'image/webp'];
    const extensoesPermitidas = ['.jpg', '.jpeg', '.png', '.webp'];
    const tamanhoMaximo = 2 * 1024 * 1024;
    const larguraMaxima = 2000;
    const alturaMaxima = 2000;

    /* ========================================================
       MENSAGEM DE ERRO
       ======================================================== */
    function mostrarErro(mensagem) {

        if (error) {
            error.textContent = mensagem;
            error.classList.remove('hidden');
        }

        if (preview) {
            preview.classList.add('hidden');

            const imagemPreview = preview.querySelector('img');

            if (imagemPreview) {
                imagemPreview.src = '';
            }
        }

        if (placeholder) {
            placeholder.classList.remove('hidden');
        }
    }

    /* ========================================================
       LIMPAR ERRO
       ======================================================== */
    function limparErro() {

        if (!error) {
            return;
        }

        error.textContent = '';
        error.classList.add('hidden');
    }

    /* ========================================================
       LIMPAR ARQUIVO SELECIONADO
       ======================================================== */
    function limparArquivo() {

        input.value = '';

        if (preview) {
            preview.classList.add('hidden');

            const imagemPreview = preview.querySelector('img');

            if (imagemPreview) {
                imagemPreview.src = '';
            }
        }

        if (placeholder) {
            placeholder.classList.remove('hidden');
        }
    }

    /* ========================================================
       VALIDAR EXTENSÃO
       ======================================================== */
    function validarExtensao(nomeArquivo) {

        const nome = nomeArquivo.toLowerCase();

        return extensoesPermitidas.some(function (extensao) {
            return nome.endsWith(extensao);
        });
    }

    /* ========================================================
       MOSTRAR PREVIEW
       ======================================================== */
    function mostrarPreview(arquivo) {

        const url = URL.createObjectURL(arquivo);
        const imagemPreview = preview
            ? preview.querySelector('img')
            : null;

        if (!imagemPreview) {
            URL.revokeObjectURL(url);
            return;
        }

        imagemPreview.src = url;

        imagemPreview.onload = function () {
            URL.revokeObjectURL(url);
        };

        preview.classList.remove('hidden');

        if (placeholder) {
            placeholder.classList.add('hidden');
        }
    }

    /* ========================================================
       VALIDAR IMAGEM
       ======================================================== */
    function validarImagem(arquivo) {

        limparErro();

        /* ----------------------------------------------------
           TIPO / EXTENSÃO
           ---------------------------------------------------- */
        if (
            !tiposPermitidos.includes(arquivo.type) ||
            !validarExtensao(arquivo.name)
        ) {

            limparArquivo();

            mostrarErro(
                'Tipo de arquivo não permitido. ' +
                'Selecione uma imagem JPG, JPEG, PNG ou WEBP.'
            );

            return false;
        }

        /* ----------------------------------------------------
           TAMANHO
           ---------------------------------------------------- */
        if (arquivo.size > tamanhoMaximo) {

            limparArquivo();

            mostrarErro(
                'A imagem excede o tamanho máximo permitido de 2 MB.'
            );

            return false;
        }

        /* ----------------------------------------------------
           DIMENSÕES
           ---------------------------------------------------- */
        const imagem = new Image();

        imagem.onload = function () {

            if (
                imagem.width > larguraMaxima ||
                imagem.height > alturaMaxima
            ) {

                limparArquivo();

                mostrarErro(
                    'A imagem excede as dimensões máximas permitidas ' +
                    'de 2000 × 2000 pixels.'
                );

                return;
            }

            /* ------------------------------------------------
               IMAGEM APROVADA
               ------------------------------------------------ */
            mostrarPreview(arquivo);
        };


        imagem.onerror = function () {
            limparArquivo();
            mostrarErro(
                'Não foi possível carregar a imagem selecionada.'
            );
        };

        const url = URL.createObjectURL(arquivo);
        imagem.src = url;
        imagem.onloadend = function () {
            URL.revokeObjectURL(url);
        };

        return true;
    }

    /* ========================================================
       PROCESSAR ARQUIVO
       ======================================================== */
    function processarArquivo(arquivo) {
        if (!arquivo) {
            return;
        }

        validarImagem(arquivo);
    }

    /* ========================================================
       CLIQUE NA MOLDURA
       ======================================================== */
    dropzone.addEventListener('click', function (event) {
        if (input.disabled) {
            return;
        }

        /*
         * O input está oculto.
         * O clique na moldura abre o Explorer.
         */
        if (event.target !== input) {
            input.click();
        }
    });

    /* ========================================================
       SELEÇÃO PELO EXPLORER
       ======================================================== */
    input.addEventListener('change', function () {
        if (this.files && this.files.length > 0) {
            processarArquivo(this.files[0]);
        }
    });

    /* ========================================================
       DRAG & DROP — ARRASTAR
       ======================================================== */
    dropzone.addEventListener('dragover', function (event) {
        if (input.disabled) {
            return;
        }

        event.preventDefault();

        dropzone.classList.add(
            'border-blue-600',
            'bg-blue-100'
        );
    });

    /* ========================================================
       DRAG & DROP — SAIR
       ======================================================== */
    dropzone.addEventListener('dragleave', function () {
        dropzone.classList.remove(
            'border-blue-600',
            'bg-blue-100'
        );
    });

    /* ========================================================
       DRAG & DROP — SOLTAR
       ======================================================== */
    dropzone.addEventListener('drop', function (event) {
        if (input.disabled) {
            return;
        }

        event.preventDefault();

        dropzone.classList.remove(
            'border-blue-600',
            'bg-blue-100'
        );

        const arquivos = event.dataTransfer.files;

        if (!arquivos || arquivos.length === 0) {
            return;
        }


        const arquivo = arquivos[0];

        /*
         * Coloca o arquivo no input para que o Django
         * possa recebê-lo no POST.
         */
        const dataTransfer = new DataTransfer();
        dataTransfer.items.add(arquivo);
        input.files = dataTransfer.files;

        /*
         * Processa e valida.
         */
        processarArquivo(arquivo);
    });
}