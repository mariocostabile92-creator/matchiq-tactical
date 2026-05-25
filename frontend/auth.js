const AUTH_API_BASE = "http://127.0.0.1:8000/api";

const TOKEN_KEY = "matchiq_auth_token";
const USER_KEY = "matchiq_auth_user";

function saveSession(token, user) {
    localStorage.setItem(TOKEN_KEY, token);
    localStorage.setItem(USER_KEY, JSON.stringify(user));
}

function getToken() {
    return localStorage.getItem(TOKEN_KEY);
}

function getUser() {
    try {
        return JSON.parse(localStorage.getItem(USER_KEY));
    } catch {
        return null;
    }
}

function isLoggedIn() {
    return Boolean(getToken());
}

function logout() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    window.location.href = "login.html";
}

async function registerUser(email, password) {
    const response = await fetch(`${AUTH_API_BASE}/auth/register`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ email, password })
    });

    const data = await response.json();

    if (!response.ok) {
        throw new Error(data.detail || "Errore registrazione");
    }

    saveSession(data.token, data.user);
    return data;
}

async function loginUser(email, password) {
    const response = await fetch(`${AUTH_API_BASE}/auth/login`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ email, password })
    });

    const data = await response.json();

    if (!response.ok) {
        throw new Error(data.detail || "Errore login");
    }

    saveSession(data.token, data.user);
    return data;
}

async function fetchMe() {
    const token = getToken();

    if (!token) {
        return null;
    }

    const response = await fetch(`${AUTH_API_BASE}/auth/me`, {
        headers: {
            "Authorization": `Bearer ${token}`
        }
    });

    if (!response.ok) {
        logout();
        return null;
    }

    const data = await response.json();

    if (data.user) {
        localStorage.setItem(USER_KEY, JSON.stringify(data.user));
    }

    return data.user;
}

function requireAuth() {
    if (!isLoggedIn()) {
        window.location.href = "login.html";
    }
}

function redirectIfLoggedIn() {
    if (isLoggedIn()) {
        window.location.href = "index.html";
    }
}

function isProUser() {
    const user = getUser();

    if (!user) return false;

    return (
        user.plan === "pro" ||
        user.plan === "scout"
    );
}

function getUserPlan() {
    const user = getUser();
    return user?.plan || "free";
}

function showPremiumPopup(feature = "Funzione PRO") {
    const existing = document.getElementById("premiumPopup");

    if (existing) {
        existing.remove();
    }

    const popup = document.createElement("div");
    popup.id = "premiumPopup";

    popup.innerHTML = `
        <div class="premium-popup-overlay">
            <div class="premium-popup">
                <div class="premium-icon">🔒</div>

                <h2>${feature}</h2>

                <p>
                    Questa funzionalità è disponibile solo per utenti
                    <strong>PRO</strong> o <strong>SCOUT</strong>.
                </p>

                <div class="premium-benefits">
                    <div>✅ PDF report avanzati</div>
                    <div>✅ AI Tactical Insights</div>
                    <div>✅ Player Ratings PRO</div>
                    <div>✅ Scout Mode</div>
                </div>

                <button id="upgradeBtn">
                    Upgrade to PRO
                </button>

                <button id="closePremiumPopup">
                    Chiudi
                </button>
            </div>
        </div>
    `;

    document.body.appendChild(popup);

    document.getElementById("closePremiumPopup").onclick = () => {
        popup.remove();
    };

    document.getElementById("upgradeBtn").onclick = () => {
        alert("Stripe integration coming soon 🚀");
    };
}

function renderUserBadge(containerId = "userBadge") {
    const container = document.getElementById(containerId);
    if (!container) return;

    const user = getUser();

    if (!user) {
        container.innerHTML = `
            <button class="auth-btn" onclick="window.location.href='login.html'">
                Login
            </button>
        `;
        return;
    }

    const plan = String(user.plan || "free").toLowerCase();

    container.innerHTML = `
        <div class="user-badge user-plan-${plan}">
            <div>
                <strong>${user.email}</strong>
                <span>${plan.toUpperCase()}</span>
            </div>
            <button onclick="logout()">Logout</button>
        </div>
    `;
}

function requirePro(feature = "Funzione PRO") {
    if (!isProUser()) {
        showPremiumPopup(feature);
        return false;
    }

    return true;
}