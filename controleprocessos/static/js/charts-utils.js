function normalizarLabel(label) {
    if (!label) return "";

    return label
        .toString()
        .toLowerCase()
        .normalize("NFD")
        .replace(/[\u0300-\u036f]/g, "")
        .replace(/^processos\s+/g, "")
        .trim();
}

const CORES_STATUS = {
    iniciado: { bg: "rgba(245,158,11,0.25)", border: "#f59e0b" },
    ativo: { bg: "rgba(34,197,94,0.25)", border: "#22c55e" },
    concluido: { bg: "rgba(239,68,68,0.25)", border: "#ef4444" }
};

const CORES_CLASS = {
    estrategico: { bg:"rgba(59,130,246,0.25)", border:"#3b82f6" },
    suporte: { bg:"rgba(139,92,246,0.25)", border:"#8b5cf6" },
    finalisticos: { bg:"rgba(249,115,22,0.25)", border:"#f97316" },
    finalistico: { bg:"rgba(249,115,22,0.25)", border:"#f97316" }
};

function gerarCores(labels, mapa) {
    return {
        bg: labels.map(l => mapa[normalizarLabel(l)]?.bg || "rgba(200,200,200,0.2)"),
        border: labels.map(l => mapa[normalizarLabel(l)]?.border || "#999")
    };
}

function pieOptions(labels, mapa) {
    return {
        responsive: true,
        maintainAspectRatio: false,

        elements: {
            arc: {
                hoverOffset: 18,
                hoverBorderWidth: 3
            }
        },

        plugins: {
            legend: { position: "top" },

            datalabels: {
                color: (ctx) => {
                    const label = ctx.chart.data.labels[ctx.dataIndex];
                    return mapa[normalizarLabel(label)]?.border || "#333";
                },

                formatter: (value, ctx) => {
                    const data = ctx.chart.data.datasets[0].data;
                    const total = data.reduce((a, b) => a + b, 0);

                    if (!total) return "0";

                    const pct = ((value / total) * 100).toFixed(1);
                    return `${value} (${pct}%)`;
                }
            }
        }
    };
}

// ============================
// PALETA GENÉRICA (BARRAS)
// ============================

const PALETA_PADRAO = [
    { bg: "rgba(59,130,246,0.25)", border: "#3b82f6" },
    { bg: "rgba(16,185,129,0.25)", border: "#10b981" },
    { bg: "rgba(245,158,11,0.25)", border: "#f59e0b" },
    { bg: "rgba(239,68,68,0.25)", border: "#ef4444" },
    { bg: "rgba(139,92,246,0.25)", border: "#8b5cf6" },
    { bg: "rgba(6,182,212,0.25)", border: "#06b6d4" },
    { bg: "rgba(132,204,22,0.25)", border: "#84cc16" }
];

function gerarCoresPadrao(qtd) {
    return {
        bg: Array.from({ length: qtd }, (_, i) => PALETA_PADRAO[i % PALETA_PADRAO.length].bg),
        border: Array.from({ length: qtd }, (_, i) => PALETA_PADRAO[i % PALETA_PADRAO.length].border)
    };
}