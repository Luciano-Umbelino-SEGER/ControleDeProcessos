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

    const tiposPermitidos = [
        'image/jpeg',
        'image/png',
        'image/webp'
    ];

    const extensoesPermitidas = [
        '.jpg',
        '.jpeg',
        '.png',
        '.webp'
    ];

    const tamanhoMaximo = 2 * 1024 * 1024;

    const larguraMaxima = 2000;
    const alturaMaxima = 2000;


    /* ========================================================
       MENSAGENS DE ERRO
       ======================================================== */

    function mostrarErro(mensagem) {

        if (error) {
            error.textContent = mensagem;
            error.classList.remove('hidden');
        }

        if (preview) {
            preview.src = '';
            preview.classList.add('hidden');
        }

        if (placeholder) {
            placeholder.classList.remove('hidden');
        }
    }


    function limparErro() {

        if (!error) {
            return;
        }

        error.textContent = '';
        error.classList.add('hidden');
    }


    /* ========================================================
       VALIDAÇÃO DA EXTENSÃO
       ======================================================== */

    function validarExtensao(nomeArquivo) {

        const nome = nomeArquivo.toLowerCase();

        return extensoesPermitidas.some(function (extensao) {
            return nome.endsWith(extensao);
        });
    }


    /* ========================================================
       VALIDAÇÃO DA IMAGEM
       ======================================================== */

    function validarImagem(arquivo) {

        limparErro();

        /*
         * Validação do tipo MIME e da extensão.
         */
        if (
            !tiposPermitidos.includes(arquivo.type) ||
            !validarExtensao(arquivo.name)
        ) {

            mostrarErro(
                'Tipo de arquivo não permitido. ' +
                'Selecione uma imagem JPG, JPEG, PNG ou WEBP.'
            );

            return;
        }


        /*
         * Validação do tamanho.
         */
        if (arquivo.size > tamanhoMaximo) {

            mostrarErro(
                'A imagem excede o tamanho máximo permitido de 2 MB.'
            );

            return;
        }


        /*
         * Validação das dimensões.
         */
        const imagem = new Image();

        imagem.onload = function () {

            if (
                imagem.width > larguraMaxima ||
                imagem.height > alturaMaxima
            ) {

                mostrarErro(
                    'A imagem excede as dimensões máximas permitidas ' +
                    'de 2000 × 2000 pixels.'
                );

                return;
            }


            /*
             * Imagem aprovada.
             *
             * Criamos uma URL temporária para o preview.
             */
            const url = URL.createObjectURL(arquivo);

            if (preview) {
                preview.src = url;
                preview.classList.remove('hidden');
            }

            if (placeholder) {
                placeholder.classList.add('hidden');
            }
        };


        imagem.onerror = function () {

            mostrarErro(
                'Não foi possível carregar a imagem selecionada.'
            );
        };


        imagem.src = URL.createObjectURL(arquivo);
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
         * O próprio input é oculto.
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
       DRAG & DROP — SAIR DA MOLDURA
       ======================================================== */

    dropzone.addEventListener('dragleave', function () {

        dropzone.classList.remove(
            'border-blue-600',
            'bg-blue-100'
        );
    });


    /* ========================================================
       DRAG & DROP — SOLTAR ARQUIVO
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
         * Mantemos o arquivo no input.
         *
         * Dessa forma, quando o formulário for enviado,
         * o Django receberá normalmente:
         *
         * request.FILES["imagem"]
         */
        const dataTransfer = new DataTransfer();

        dataTransfer.items.add(arquivo);

        input.files = dataTransfer.files;


        /*
         * Processa e valida o arquivo.
         */
        processarArquivo(arquivo);
    });
}