/*
    MatchIQ - PDF Module
    Gestione download PDF report PRO/SCOUT
*/

function getLocalAuthUser(){
    try{
        return JSON.parse(localStorage.getItem("matchiq_auth_user"));
    }catch(e){
        return null;
    }
}

function isLocalProUser(){
    const user = typeof getUser === "function"
        ? getUser()
        : getLocalAuthUser();

    const plan = String(
        user?.plan ||
        user?.piano ||
        user?.subscription ||
        user?.role ||
        "free"
    ).toLowerCase();

    const email = String(user?.email || "").toLowerCase();

    return (
        plan === "pro" ||
        plan === "scout" ||
        plan === "owner" ||
        email === "mario.costabile92@outlook.it"
    );
}

function showLocalPremiumPopup(feature="PDF Report PRO"){
    const existing=document.getElementById("premiumPopup");
    if(existing)existing.remove();

    const popup=document.createElement("div");
    popup.id="premiumPopup";
    popup.innerHTML=`
        <div class="premium-popup-overlay">
            <div class="premium-popup">
                <div class="premium-icon">🔒</div>
                <h2>${feature}</h2>
                <p>Questa funzionalità è disponibile solo per utenti <strong>PRO</strong> o <strong>SCOUT</strong>.</p>
                <div class="premium-benefits">
                    <div>✅ PDF report avanzati</div>
                    <div>✅ AI Tactical Insights</div>
                    <div>✅ Player Ratings PRO</div>
                    <div>✅ Scout Mode</div>
                </div>
                <button id="upgradeBtn">Upgrade to PRO</button>
                <button id="closePremiumPopup">Chiudi</button>
            </div>
        </div>
    `;

    document.body.appendChild(popup);

    const closeBtn=document.getElementById("closePremiumPopup");
    if(closeBtn){
        closeBtn.onclick=()=>popup.remove();
    }

    const upgradeBtn=document.getElementById("upgradeBtn");
    if(upgradeBtn){
        upgradeBtn.onclick=()=>alert("Stripe integration coming soon 🚀");
    }
}

async function downloadPDFReport(){
    if(typeof matchId === "undefined" || !matchId){
        alert("ID partita mancante");
        return;
    }

    if(!isLocalProUser()){
        showLocalPremiumPopup("PDF Report PRO");
        return;
    }

    try{
        const token =
            localStorage.getItem("matchiq_token") ||
            localStorage.getItem("token") ||
            localStorage.getItem("access_token");

        const headers = {};

        if(token){
            headers["Authorization"] = `Bearer ${token}`;
        }

        const apiBase =
            typeof API_BASE !== "undefined"
                ? API_BASE
                : `${window.location.origin}/api`;

        const response = await fetch(
            `${apiBase}/match/${matchId}/download-pdf`,
            {
                method: "GET",
                headers
            }
        );

        if(response.status === 401 || response.status === 403){
            showLocalPremiumPopup("PDF Report PRO");
            return;
        }

        if(!response.ok){
            const text = await response.text();
            alert("Errore download PDF: " + text);
            return;
        }

        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);

        const a = document.createElement("a");
        a.href = url;
        a.download = `matchiq-report-${matchId}.pdf`;

        document.body.appendChild(a);
        a.click();
        a.remove();

        window.URL.revokeObjectURL(url);

    }catch(error){
        console.error("PDF download error:", error);
        alert("Errore durante il download PDF.");
    }
}