const MOMENTUM_KEY = "matchiq_momentum_v2";

let momentumPoints = loadMomentumPoints();
let lastHomeValue = momentumPoints.length ? momentumPoints[momentumPoints.length - 1].home : 50;
let lastAwayValue = momentumPoints.length ? momentumPoints[momentumPoints.length - 1].away : 50;

function loadMomentumPoints() {
    try {
        const saved = localStorage.getItem(MOMENTUM_KEY);
        return saved ? JSON.parse(saved) : [];
    } catch {
        return [];
    }
}

function saveMomentumPoints() {
    localStorage.setItem(MOMENTUM_KEY, JSON.stringify(momentumPoints));
}

function clamp(value, min = 5, max = 100) {
    return Math.max(min, Math.min(max, Number(value) || 0));
}

function smoothValue(previous, target, factor = 0.35) {
    return previous + (target - previous) * factor;
}

function addMomentumPoint(home, away) {
    let targetHome = clamp(home || 50);
    let targetAway = clamp(away || 50);

    const randomPulseHome = (Math.random() * 5) - 2.5;
    const randomPulseAway = (Math.random() * 5) - 2.5;

    targetHome = clamp(targetHome + randomPulseHome);
    targetAway = clamp(targetAway + randomPulseAway);

    lastHomeValue = smoothValue(lastHomeValue, targetHome);
    lastAwayValue = smoothValue(lastAwayValue, targetAway);

    const diff = Math.abs(lastHomeValue - lastAwayValue);

    if (diff < 6) {
        lastHomeValue += (Math.random() * 4) - 2;
        lastAwayValue += (Math.random() * 4) - 2;
    }

    momentumPoints.push({
        home: clamp(lastHomeValue),
        away: clamp(lastAwayValue),
        time: new Date().toLocaleTimeString()
    });

    if (momentumPoints.length > 50) {
        momentumPoints.shift();
    }

    saveMomentumPoints();
    renderMomentumChart();
}

function drawGrid(ctx, width, height) {
    ctx.strokeStyle = "rgba(255,255,255,0.06)";
    ctx.lineWidth = 1;

    for (let i = 0; i <= 5; i++) {
        const y = (height / 5) * i;
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(width, y);
        ctx.stroke();
    }

    for (let i = 0; i <= 10; i++) {
        const x = (width / 10) * i;
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, height);
        ctx.stroke();
    }
}

function drawLabels(ctx, height) {
    ctx.fillStyle = "rgba(255,255,255,0.55)";
    ctx.font = "13px Arial";

    ctx.fillText("100", 10, 18);
    ctx.fillText("75", 10, height * 0.27);
    ctx.fillText("50", 10, height * 0.52);
    ctx.fillText("25", 10, height * 0.76);
    ctx.fillText("0", 10, height - 10);
}

function drawSmoothLine(ctx, points, color, width, height, key) {
    if (points.length < 2) return;

    ctx.beginPath();
    ctx.strokeStyle = color;
    ctx.lineWidth = 4;
    ctx.shadowColor = color;
    ctx.shadowBlur = 18;

    points.forEach((point, index) => {
        const x = (index / (points.length - 1)) * width;
        const y = height - (point[key] / 100) * height;

        if (index === 0) {
            ctx.moveTo(x, y);
        } else {
            const prevX = ((index - 1) / (points.length - 1)) * width;
            const prevY = height - (points[index - 1][key] / 100) * height;
            const cpX = (prevX + x) / 2;

            ctx.bezierCurveTo(cpX, prevY, cpX, y, x, y);
        }
    });

    ctx.stroke();
    ctx.shadowBlur = 0;
}

function drawAreaFill(ctx, points, color, width, height, key) {
    if (points.length < 2) return;

    ctx.beginPath();

    points.forEach((point, index) => {
        const x = (index / (points.length - 1)) * width;
        const y = height - (point[key] / 100) * height;

        if (index === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
    });

    ctx.lineTo(width, height);
    ctx.lineTo(0, height);
    ctx.closePath();

    const gradient = ctx.createLinearGradient(0, 0, 0, height);

    if (color === "#3b82f6") {
        gradient.addColorStop(0, "rgba(59,130,246,0.30)");
        gradient.addColorStop(1, "rgba(59,130,246,0)");
    } else {
        gradient.addColorStop(0, "rgba(239,68,68,0.30)");
        gradient.addColorStop(1, "rgba(239,68,68,0)");
    }

    ctx.fillStyle = gradient;
    ctx.fill();
}

function drawLastPoint(ctx, point, width, height) {
    const homeY = height - (point.home / 100) * height;
    const awayY = height - (point.away / 100) * height;

    ctx.shadowBlur = 22;

    ctx.beginPath();
    ctx.fillStyle = "#3b82f6";
    ctx.shadowColor = "#3b82f6";
    ctx.arc(width - 10, homeY, 7, 0, Math.PI * 2);
    ctx.fill();

    ctx.beginPath();
    ctx.fillStyle = "#ef4444";
    ctx.shadowColor = "#ef4444";
    ctx.arc(width - 10, awayY, 7, 0, Math.PI * 2);
    ctx.fill();

    ctx.shadowBlur = 0;
}

function renderMomentumChart() {
    const canvas = document.getElementById("momentumChart");
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    const width = canvas.width;
    const height = canvas.height;

    ctx.clearRect(0, 0, width, height);

    ctx.fillStyle = "#071126";
    ctx.fillRect(0, 0, width, height);

    drawGrid(ctx, width, height);
    drawLabels(ctx, height);

    if (momentumPoints.length < 2) {
        addMomentumPoint(50, 50);
        addMomentumPoint(52, 48);
        return;
    }

    drawAreaFill(ctx, momentumPoints, "#3b82f6", width, height, "home");
    drawAreaFill(ctx, momentumPoints, "#ef4444", width, height, "away");

    drawSmoothLine(ctx, momentumPoints, "#3b82f6", width, height, "home");
    drawSmoothLine(ctx, momentumPoints, "#ef4444", width, height, "away");

    drawLastPoint(ctx, momentumPoints[momentumPoints.length - 1], width, height);

    ctx.fillStyle = "rgba(255,255,255,0.8)";
    ctx.font = "bold 15px Arial";
    ctx.fillText("LIVE MOMENTUM FLOW", 45, 28);
}

setInterval(() => {
    const last = momentumPoints[momentumPoints.length - 1] || { home: 50, away: 50 };

    addMomentumPoint(
        last.home + ((Math.random() * 8) - 4),
        last.away + ((Math.random() * 8) - 4)
    );
}, 3500);

setTimeout(() => {
    renderMomentumChart();
}, 500);