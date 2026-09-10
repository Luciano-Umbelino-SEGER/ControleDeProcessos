document.addEventListener("DOMContentLoaded", () => {

    const cards = document.querySelectorAll(".macroprocesso-card");

    if (!cards.length) {
        return;
    }


    // =========================================================
    // CONVERTE RGB PARA HSL
    // =========================================================

    function rgbToHsl(r, g, b) {

        r /= 255;
        g /= 255;
        b /= 255;

        const max = Math.max(r, g, b);
        const min = Math.min(r, g, b);

        let h;
        let s;
        const l = (max + min) / 2;

        if (max === min) {

            h = 0;
            s = 0;

        } else {

            const d = max - min;

            s = l > 0.5
                ? d / (2 - max - min)
                : d / (max + min);

            switch (max) {

                case r:
                    h = ((g - b) / d) + (g < b ? 6 : 0);
                    break;

                case g:
                    h = ((b - r) / d) + 2;
                    break;

                default:
                    h = ((r - g) / d) + 4;
                    break;
            }

            h /= 6;
        }

        return [h * 360, s * 100, l * 100];
    }


    // =========================================================
    // CONVERTE HSL PARA RGB
    // =========================================================

    function hslToRgb(h, s, l) {

        h /= 360;
        s /= 100;
        l /= 100;

        let r;
        let g;
        let b;

        if (s === 0) {

            r = g = b = l;

        } else {

            const hue2rgb = (p, q, t) => {

                if (t < 0) t += 1;
                if (t > 1) t -= 1;

                if (t < 1 / 6) {
                    return p + (q - p) * 6 * t;
                }

                if (t < 1 / 2) {
                    return q;
                }

                if (t < 2 / 3) {
                    return p + (q - p) * (2 / 3 - t) * 6;
                }

                return p;
            };

            const q =
                l < 0.5
                    ? l * (1 + s)
                    : l + s - l * s;

            const p = 2 * l - q;

            r = hue2rgb(p, q, h + 1 / 3);
            g = hue2rgb(p, q, h);
            b = hue2rgb(p, q, h - 1 / 3);
        }

        return [
            Math.round(r * 255),
            Math.round(g * 255),
            Math.round(b * 255)
        ];
    }


    // =========================================================
    // RGB PARA CSS
    // =========================================================

    function rgbCss(rgb) {
        return `rgb(${rgb[0]}, ${rgb[1]}, ${rgb[2]})`;
    }


    // =========================================================
    // PALETA CINZA – CARD SEM IMAGEM
    // =========================================================

    function aplicarPaletaCinza(card) {

        card.style.setProperty(
            "--color-strong",
            "rgb(75, 85, 99)"
        );

        card.style.setProperty(
            "--color-soft",
            "rgb(209, 213, 219)"
        );

        card.style.setProperty(
            "--color-mid",
            "rgb(229, 231, 235)"
        );

        card.style.setProperty(
            "--card-bg",
            "rgb(249, 250, 251)"
        );
    }


    // =========================================================
    // CALCULA A PALETA A PARTIR DA IMAGEM
    // =========================================================

    function aplicarPaletaDaImagem(card, imagem) {

        const canvas = document.createElement("canvas");
        const contexto = canvas.getContext("2d", {
            willReadFrequently: true
        });

        const largura =
            Math.min(imagem.naturalWidth, 120);

        const altura =
            Math.min(imagem.naturalHeight, 120);

        canvas.width = largura;
        canvas.height = altura;

        contexto.drawImage(
            imagem,
            0,
            0,
            largura,
            altura
        );

        const dados = contexto.getImageData(
            0,
            0,
            largura,
            altura
        ).data;


        // =====================================================
        // IDENTIFICA A COR MAIS REPRESENTATIVA
        // =====================================================

        const cores = [];

        for (let i = 0; i < dados.length; i += 4) {

            const r = dados[i];
            const g = dados[i + 1];
            const b = dados[i + 2];
            const a = dados[i + 3];

            if (a < 180) {
                continue;
            }

            const [h, s, l] = rgbToHsl(r, g, b);

            // Ignora cores muito apagadas ou muito escuras.
            if (s < 20 || l < 10 || l > 92) {
                continue;
            }

            cores.push({
                r,
                g,
                b,
                h,
                s,
                l
            });
        }


        // =====================================================
        // FALLBACK
        // =====================================================

        if (!cores.length) {

            aplicarPaletaCinza(card);
            return;
        }


        // =====================================================
        // ESCOLHE A COR MAIS SATURADA/REPRESENTATIVA
        // =====================================================

        cores.sort((a, b) => {

            const pesoA =
                a.s * 0.65 +
                (100 - Math.abs(a.l - 50)) * 0.35;

            const pesoB =
                b.s * 0.65 +
                (100 - Math.abs(b.l - 50)) * 0.35;

            return pesoB - pesoA;
        });


        const predominante = cores[0];


        // =====================================================
        // PALETA DERIVADA DA COR PREDOMINANTE
        // =====================================================

        const h = predominante.h;

        // Cor forte – título
        const corForte = hslToRgb(
            h,
            Math.max(55, predominante.s),
            42
        );

        // Faixa principal – cor mais forte
        const corSoft = hslToRgb(
            h,
            Math.min(55, Math.max(25, predominante.s * 0.75)),
            78
        );

        // Faixa intermediária – entre a faixa principal e o fundo
        const corMid = hslToRgb(
            h,
            Math.min(48, Math.max(20, predominante.s * 0.60)),
            87
        );

        // Fundo geral do card
        const corFundo = hslToRgb(
            h,
            Math.min(28, Math.max(8, predominante.s * 0.30)),
            96
        );


        // =====================================================
        // APLICA AS CORES AO CARD
        // =====================================================

        card.style.setProperty(
            "--color-strong",
            rgbCss(corForte)
        );

        card.style.setProperty(
            "--color-soft",
            rgbCss(corSoft)
        );

        card.style.setProperty(
            "--color-mid",
            rgbCss(corMid)
        );

        card.style.setProperty(
            "--card-bg",
            rgbCss(corFundo)
        );
    }


    // =========================================================
    // PROCESSA TODOS OS CARDS
    // =========================================================

    cards.forEach(card => {

        const caminhoImagem =
            card.dataset.imagem;

        // -----------------------------------------------------
        // SEM IMAGEM
        // -----------------------------------------------------

        if (!caminhoImagem) {

            aplicarPaletaCinza(card);
            return;
        }


        // -----------------------------------------------------
        // COM IMAGEM
        // -----------------------------------------------------

        const imagem = new Image();

        imagem.onload = () => {

            try {

                aplicarPaletaDaImagem(
                    card,
                    imagem
                );

            } catch (erro) {

                console.warn(
                    "Não foi possível obter a cor predominante:",
                    erro
                );

                aplicarPaletaCinza(card);
            }
        };


        imagem.onerror = () => {

            aplicarPaletaCinza(card);
        };


        imagem.src = caminhoImagem;
    });

});