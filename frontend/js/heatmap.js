let heatmapState = {
    homePressure: 50,
    awayPressure: 50,
    homeDanger: 50,
    awayDanger: 50,
    homeTeam: "Home",
    awayTeam: "Away"
};

function updateHeatmapData(data) {
    heatmapState = {
        homePressure: Number(data.homePressure) || 0,
        awayPressure: Number(data.awayPressure) || 0,
        homeDanger: Number(data.homeDanger) || 0,
        awayDanger: Number(data.awayDanger) || 0,
        homeTeam: data.homeTeam || "Home",
        awayTeam: data.awayTeam || "Away"
    };

    renderHeatmap();
}

function drawPitch(ctx, width, height) {
    ctx.clearRect(0, 0, width, height);

    ctx.fillStyle = "#071f16";
    ctx.fillRect(0, 0, width, height);

    ctx.strokeStyle = "rgba(255,255,255,0.35)";
    ctx.lineWidth = 2;

    ctx.strokeRect(25, 25, width - 50, height - 50);

    ctx.beginPath();
    ctx.moveTo(width / 2, 25);
    ctx.lineTo(width / 2, height - 25);
    ctx.stroke();

    ctx.beginPath();
    ctx.arc(width / 2, height / 2, 55, 0, Math.PI * 2);
    ctx.stroke();

    ctx.strokeRect(25, height / 2 - 80, 90, 160);
    ctx.strokeRect(width - 115, height / 2 - 80, 90, 160);

    ctx.strokeRect(25, height / 2 - 40, 35, 80);
    ctx.strokeRect(width - 60, height / 2 - 40, 35, 80);

    ctx.fillStyle = "rgba(255,255,255,0.8)";
    ctx.beginPath();
    ctx.arc(width / 2, height / 2, 4, 0, Math.PI * 2);
    ctx.fill();
}

function drawZone(ctx, x, y, radius, color, intensity) {
    const gradient = ctx.createRadialGradient(x, y, 5, x, y, radius);

    gradient.addColorStop(0, color.replace("0.0", intensity));
    gradient.addColorStop(1, color.replace("0.0", "0"));

    ctx.fillStyle = gradient;
    ctx.beginPath();
    ctx.arc(x, y, radius, 0, Math.PI * 2);
    ctx.fill();
}

function renderHeatmap() {
    const canvas = document.getElementById("heatmapCanvas");
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    const width = canvas.width;
    const height = canvas.height;

    drawPitch(ctx, width, height);

    const homeAttackIntensity = Math.min(0.85, (heatmapState.homePressure + heatmapState.homeDanger) / 180);
    const awayAttackIntensity = Math.min(0.85, (heatmapState.awayPressure + heatmapState.awayDanger) / 180);

    drawZone(
        ctx,
        width * 0.72,
        height * 0.32,
        135,
        "rgba(59,130,246,0.0)",
        homeAttackIntensity
    );

    drawZone(
        ctx,
        width * 0.72,
        height * 0.68,
        120,
        "rgba(59,130,246,0.0)",
        homeAttackIntensity * 0.75
    );

    drawZone(
        ctx,
        width * 0.28,
        height * 0.35,
        135,
        "rgba(239,68,68,0.0)",
        awayAttackIntensity
    );

    drawZone(
        ctx,
        width * 0.28,
        height * 0.67,
        120,
        "rgba(239,68,68,0.0)",
        awayAttackIntensity * 0.75
    );

    ctx.fillStyle = "rgba(255,255,255,0.85)";
    ctx.font = "bold 16px Arial";
    ctx.fillText(`${heatmapState.homeTeam} pressure`, 35, 35);
    ctx.fillText(`${heatmapState.awayTeam} pressure`, width - 210, 35);

    ctx.fillStyle = "#3b82f6";
    ctx.fillText(`Home: ${Math.round(heatmapState.homePressure)} / Danger ${Math.round(heatmapState.homeDanger)}`, 35, height - 25);

    ctx.fillStyle = "#ef4444";
    ctx.fillText(`Away: ${Math.round(heatmapState.awayPressure)} / Danger ${Math.round(heatmapState.awayDanger)}`, width - 285, height - 25);
}

setInterval(() => {
    renderHeatmap();
}, 2500);