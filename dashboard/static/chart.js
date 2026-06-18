function initChartGiornaliero(canvasId, da, a) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;

    fetch(`/api/stats/giornaliere?da=${da}&a=${a}`)
        .then(r => r.json())
        .then(data => {
            new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: data.map(d => d.giorno),
                    datasets: [{
                        label: 'Timbrature',
                        data: data.map(d => d.n),
                        backgroundColor: '#0d7377',
                        borderRadius: 4,
                    }]
                },
                options: {
                    responsive: true,
                    plugins: { legend: { display: false } },
                    scales: {
                        y: { beginAtZero: true, ticks: { stepSize: 1 } }
                    }
                }
            });
        });
}
