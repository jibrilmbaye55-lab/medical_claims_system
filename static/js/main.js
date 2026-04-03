/* ==============================
   MAIN JS - COUD MEDICAL
============================== */

document.addEventListener("DOMContentLoaded", function () {
    console.log("✅ COUD Medical Dashboard chargé");

    // Animation douce des KPI
    const cards = document.querySelectorAll(".kpi-card");
    cards.forEach((card, index) => {
        card.style.animationDelay = `${index * 0.15}s`;
    });

    // Highlight auto alertes urgentes
    const urgentBox = document.getElementById("liveUrgentClaims");
    if (urgentBox) {
        const alerts = urgentBox.querySelectorAll(".alert-danger");
        if (alerts.length > 0) {
            urgentBox.style.animation = "pulse 1.5s infinite";
        }
    }
});

/* ==============================
   PULSE ALERT
============================== */
const style = document.createElement("style");
style.innerHTML = `
@keyframes pulse {
    0% { box-shadow: 0 0 0 rgba(220,53,69,0.4); }
    50% { box-shadow: 0 0 25px rgba(220,53,69,0.4); }
    100% { box-shadow: 0 0 0 rgba(220,53,69,0.4); }
}
`;
document.head.appendChild(style);