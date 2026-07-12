let donjonState = null;
let donjonActive = false;
let donjonTickTimer = null;
let donjonEnemyTimer = null;
let donjonChoices = [];
let donjonCombatActive = false;

const NODE_COLORS = {
    combat: "#ef4444",
    camp: "#22c55e",
    evenement: "#3b82f6",
    relique: "#a855f7",
    boss: "#f59e0b",
};

const NODE_ICONS = {
    combat: "⚔️",
    camp: "🏕️",
    evenement: "❓",
    relique: "💎",
    boss: "👑",
};

const DONJON_COLS = 7;
const DONJON_ETAGES = 20;
const MAP_WIDTH = 700;
const MAP_HEIGHT = 800;
const NODE_RADIUS = 16;

function toggleDonjon() {
    const overlay = document.getElementById("donjon-overlay");
    if (overlay.classList.contains("hidden")) {
        overlay.classList.remove("hidden");
        loadDonjonState();
    } else {
        overlay.classList.add("hidden");
        stopDonjonCombat();
    }
}

async function loadDonjonState() {
    if (gameState && gameState.player.donjon_actif) {
        const res = await fetch("/api/donjon/state");
        const data = await res.json();
        if (data.success) {
            donjonState = data.donjon;
            donjonActive = true;
            renderDonjonFull();
        }
    } else {
        donjonState = null;
        donjonActive = false;
        showDonjonStart();
    }
}

function showDonjonStart() {
    document.getElementById("donjon-start-panel").classList.remove("hidden");
    document.getElementById("donjon-content").style.display = "none";
    document.getElementById("donjon-hud").style.display = "none";
    document.getElementById("btn-donjon-exit").classList.add("hidden");
    document.getElementById("donjon-chapitre").textContent = "";
    updateChapitreSelect();
}

function updateChapitreSelect() {
    const select = document.getElementById("donjon-chapitre-input");
    select.innerHTML = "";
    const maxChap = (gameState && gameState.player.boss_donjon_battus) || 0;
    const completees = (gameState && gameState.player.chapitres_completees) || [];
    for (let i = 1; i <= Math.max(1, maxChap + 1); i++) {
        const opt = document.createElement("option");
        opt.value = i;
        const done = completees.includes(i);
        opt.textContent = t("dungeon_chapter_option").replace("{n}", i).replace("{niv}", i * 10) + (done ? " ✓" : "");
        select.appendChild(opt);
    }
}

async function startDonjon() {
    const chapitre = parseInt(document.getElementById("donjon-chapitre-input").value) || 1;
    const bonus = (gameState && gameState.player.boss_donjon_battus) || 0;
    const ptsNiveau = 2 + bonus;
    const dejaFait = (gameState && gameState.player.chapitres_completees && gameState.player.chapitres_completees.includes(chapitre));

    let msg = "🏰 " + t("dj_intro_dungeon") + " " + chapitre + "\n\n"
        + t("dj_intro_during") + "\n"
        + "• " + t("dj_intro_stats_locked") + "\n"
        + "• " + t("dj_intro_death_warning") + "\n\n";

    if (dejaFait) {
        msg += "⚠️ " + t("dj_intro_already_done") + "\n"
            + t("dj_intro_items_only") + "\n\n";
    } else {
        msg += t("dj_intro_first_boss") + "\n"
            + "• " + t("dj_intro_reincarnation") + "\n"
            + "• " + t("dj_intro_stats_reset") + "\n"
            + "• " + t("dj_intro_pts_per_level") + " (" + ptsNiveau + " → " + (ptsNiveau + 1) + ")\n"
            + "• " + t("dj_intro_tokens_items") + "\n\n";
    }
    msg += t("dj_intro_continue");

    if (!confirm(msg)) return;

    const res = await fetch("/api/donjon/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ chapitre }),
    });
    const data = await res.json();
    if (data.success) {
        donjonState = data.donjon;
        donjonActive = true;
        donjonChoices = data.choix || [];
        renderDonjonFull();
    } else {
        alert(data.message);
    }
}

function renderDonjonFull() {
    document.getElementById("donjon-start-panel").classList.add("hidden");
    document.getElementById("donjon-content").style.display = "flex";
    document.getElementById("donjon-hud").style.display = "flex";
    document.getElementById("btn-donjon-exit").classList.remove("hidden");
    document.getElementById("donjon-chapitre").textContent = `Ch.${donjonState.chapitre}`;

    updateDonjonHUD();
    renderDonjonMap();
    hideAllPanels();

    if (donjonState.combat_en_cours && donjonState.ennemi) {
        donjonCombatActive = true;
        showDonjonCombat();
    } else {
        donjonCombatActive = false;
    }
}

function updateDonjonHUD() {
    if (!donjonState) return;
    const hpBar = document.getElementById("donjon-hp-bar");
    const hpText = document.getElementById("donjon-hp-text");
    const pct = donjonState.hp_max > 0 ? (donjonState.hp / donjonState.hp_max * 100) : 0;
    hpBar.style.width = Math.max(0, pct) + "%";
    hpText.textContent = `${donjonState.hp} / ${donjonState.hp_max}`;

    document.getElementById("donjon-etage").textContent = `${t("dj_floor_label")} ${donjonState.etage + 1}/${DONJON_ETAGES}`;

    const relContainer = document.getElementById("donjon-reliques");
    relContainer.innerHTML = "";
    (donjonState.reliques || []).forEach(r => {
        const badge = document.createElement("span");
        badge.className = "relique-badge";
        badge.textContent = r.nom;
        badge.title = r.description;
        relContainer.appendChild(badge);
    });
}

function renderDonjonMap() {
    const svg = document.getElementById("donjon-map");
    svg.innerHTML = "";

    const map = donjonState.map;
    const pos = donjonState.position;
    const colSpacing = MAP_WIDTH / (DONJON_COLS + 1);
    const rowSpacing = MAP_HEIGHT / (DONJON_ETAGES + 1);

    function nodeX(col) { return (col + 1) * colSpacing; }
    function nodeY(etage) { return MAP_HEIGHT - (etage + 1) * rowSpacing; }

    const drawnPaths = new Set();
    for (const [key, node] of Object.entries(map)) {
        for (const [tc, te] of node.connections) {
            const teKey = `${tc},${te}`;
            if (map[teKey]) {
                const pathKey = `${key}->${teKey}`;
                if (!drawnPaths.has(pathKey)) {
                    drawnPaths.add(pathKey);
                    const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
                    line.setAttribute("x1", nodeX(node.col));
                    line.setAttribute("y1", nodeY(node.etage));
                    line.setAttribute("x2", nodeX(tc));
                    line.setAttribute("y2", nodeY(te));
                    line.setAttribute("class", "donjon-path");
                    svg.appendChild(line);
                }
            }
        }
    }

    const availableSet = new Set();
    if (pos) {
        const currentNode = map[`${pos[0]},${pos[1]}`];
        if (currentNode) {
            for (const [tc, te] of currentNode.connections) {
                availableSet.add(`${tc},${te}`);
            }
        }
    } else {
        for (const [key, node] of Object.entries(map)) {
            if (node.etage === 0) availableSet.add(key);
        }
    }

    if (donjonChoices.length > 0) {
        availableSet.clear();
        for (const ch of donjonChoices) {
            availableSet.add(`${ch.col},${ch.etage}`);
        }
    }

    for (const [key, node] of Object.entries(map)) {
        const cx = nodeX(node.col);
        const cy = nodeY(node.etage);
        const color = NODE_COLORS[node.type] || "#666";
        const isAvailable = availableSet.has(key) && !donjonCombatActive;
        const isCurrent = pos && pos[0] === node.col && pos[1] === node.etage;
        const isVisited = node.visite;

        const g = document.createElementNS("http://www.w3.org/2000/svg", "g");
        g.setAttribute("class", "donjon-node"
            + (isAvailable ? " available" : "")
            + (isVisited ? " visited" : "")
            + (isCurrent ? " current" : ""));

        const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
        circle.setAttribute("cx", cx);
        circle.setAttribute("cy", cy);
        circle.setAttribute("r", NODE_RADIUS);
        circle.setAttribute("fill", isAvailable ? color : (isVisited ? "#333" : "#222"));
        circle.setAttribute("stroke", isCurrent ? "#fff" : color);
        circle.setAttribute("stroke-width", isCurrent ? 3 : 1.5);

        if (isAvailable) {
            circle.style.cursor = "pointer";
            circle.addEventListener("click", () => selectNode(node.col, node.etage));
        }

        g.appendChild(circle);

        const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
        text.setAttribute("x", cx);
        text.setAttribute("y", cy + 5);
        text.setAttribute("text-anchor", "middle");
        text.setAttribute("font-size", "12");
        text.setAttribute("pointer-events", "none");
        text.textContent = NODE_ICONS[node.type] || "?";
        g.appendChild(text);

        svg.appendChild(g);
    }
}

function hideAllPanels() {
    document.getElementById("donjon-room-panel").classList.add("hidden");
    document.getElementById("donjon-combat-panel").classList.add("hidden");
}

async function selectNode(col, etage) {
    if (donjonCombatActive) return;

    const res = await fetch("/api/donjon/select_node", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ col, etage }),
    });
    const data = await res.json();
    if (!data.success) {
        alert(data.message || "Erreur");
        return;
    }

    donjonState = data.donjon;
    const result = data.resultat;
    donjonChoices = result.choix_next || [];

    updateDonjonHUD();
    renderDonjonMap();
    handleRoomResult(result);
}

function handleRoomResult(result) {
    hideAllPanels();

    if (result.type === "combat" || result.type === "boss") {
        donjonCombatActive = true;
        showDonjonCombat(result.ennemi, result.message);
        startDonjonCombatTimers();
    } else if (result.type === "camp") {
        showRoomPanel("🏕️ " + t("dj_camp_title"), result.message, []);
    } else if (result.type === "evenement") {
        handleEvenement(result);
    } else if (result.type === "relique") {
        showRelicChoice(result.choix_reliques);
    }
}

function showRoomPanel(title, content, actions) {
    const panel = document.getElementById("donjon-room-panel");
    panel.classList.remove("hidden");
    document.getElementById("donjon-room-header").textContent = title;
    document.getElementById("donjon-room-content").innerHTML = `<p>${content}</p>`;

    const actionsDiv = document.getElementById("donjon-room-actions");
    actionsDiv.innerHTML = "";
    actions.forEach(a => {
        const btn = document.createElement("button");
        btn.textContent = a.label;
        if (a.className) btn.className = a.className;
        btn.addEventListener("click", a.action);
        actionsDiv.appendChild(btn);
    });
}

function handleEvenement(result) {
    const evt = result.evenement;
    let actions = [];

    if (evt.type === "relique" && result.choix_reliques) {
        showRelicChoice(result.choix_reliques.map(k => typeof k === "string" ? { key: k, nom: k, description: "" } : k));
        return;
    }

    if (result.choix_next && result.choix_next.length > 0) {
        donjonChoices = result.choix_next;
        renderDonjonMap();
    }

    showRoomPanel("❓ " + t("dj_event_title"), result.message, actions);
}

function showRelicChoice(choices) {
    if (!choices || choices.length === 0) return;

    const panel = document.getElementById("donjon-room-panel");
    panel.classList.remove("hidden");
    document.getElementById("donjon-room-header").textContent = "💎 " + t("dj_choose_relic");
    document.getElementById("donjon-room-content").innerHTML = "<p>" + t("dj_choose_relic") + "</p>";

    const actionsDiv = document.getElementById("donjon-room-actions");
    actionsDiv.innerHTML = "";

    choices.forEach(rel => {
        const relKey = typeof rel === "string" ? rel : rel.key;
        const relName = typeof rel === "string" ? rel : rel.nom;
        const relDesc = typeof rel === "string" ? "" : rel.description;

        const btn = document.createElement("button");
        btn.className = "relique-choice";
        btn.innerHTML = `<strong>${relName}</strong><br><span style="color:#aaa;font-size:0.75rem">${relDesc}</span>`;
        btn.addEventListener("click", () => choisirRelique(relKey));
        actionsDiv.appendChild(btn);
    });
}

async function choisirRelique(relKey) {
    const res = await fetch("/api/donjon/action", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "choisir_relique", relique: relKey }),
    });
    const data = await res.json();
    if (data.success) {
        donjonState = data.donjon;
        updateDonjonHUD();
        renderDonjonMap();
        showRoomPanel("💎 " + t("dj_relic_acquired_title"), data.message, []);
    }
}

function showDonjonCombat(ennemi, message) {
    const panel = document.getElementById("donjon-combat-panel");
    panel.classList.remove("hidden");
    document.getElementById("donjon-room-panel").classList.add("hidden");

    const enemy = ennemi || (donjonState && donjonState.ennemi);
    if (!enemy) return;

    const infoDiv = document.getElementById("donjon-enemy-info");
    const bossClass = enemy.boss ? ' class="boss-name"' : '';
    infoDiv.innerHTML = `
        <h3${bossClass}>${enemy.boss ? "👑 " : ""}${enemy.nom} (${t("ui_level_short")}${enemy.niveau})</h3>
        <div class="hp-bar-container">
            <div id="donjon-enemy-hp-bar" class="hp-bar enemy-hp" style="width:${(enemy.hp / enemy.hp_max * 100)}%"></div>
            <span class="hp-text">${enemy.hp} / ${enemy.hp_max}</span>
        </div>
    `;

    const logDiv = document.getElementById("donjon-combat-log");
    if (message) {
        logDiv.innerHTML = `<div class="log-line">${message}</div>`;
    }
}

function startDonjonCombatTimers() {
    stopDonjonCombat();

    const enemy = donjonState && donjonState.ennemi;
    if (!enemy) return;

    const statsJ = gameState.player.stats_effectives;
    const vitJ = statsJ.vitesse_attaque || 100;
    const intervalJ = Math.max(200, Math.round(100000 / vitJ));

    const vitE = enemy.stats.vitesse_attaque || 100;
    const intervalE = Math.max(200, Math.round(100000 / vitE));

    donjonTickTimer = setInterval(donjonPlayerTick, intervalJ);
    donjonEnemyTimer = setInterval(donjonEnemyTick, intervalE);
}

function stopDonjonCombat() {
    if (donjonTickTimer) { clearInterval(donjonTickTimer); donjonTickTimer = null; }
    if (donjonEnemyTimer) { clearInterval(donjonEnemyTimer); donjonEnemyTimer = null; }
}

async function donjonPlayerTick() {
    if (!donjonCombatActive) return;
    try {
        const res = await fetch("/api/donjon/combat_tick", { method: "POST" });
        const data = await res.json();
        processDonjonTickResult(data);
    } catch (e) { /* ignore */ }
}

async function donjonEnemyTick() {
    if (!donjonCombatActive) return;
    try {
        const res = await fetch("/api/donjon/enemy_tick", { method: "POST" });
        const data = await res.json();
        processDonjonTickResult(data);
    } catch (e) { /* ignore */ }
}

function processDonjonTickResult(data) {
    if (!data) return;

    if (data.log) {
        const logDiv = document.getElementById("donjon-combat-log");
        data.log.forEach(line => {
            const div = document.createElement("div");
            div.className = "log-line";
            div.textContent = line;
            logDiv.appendChild(div);
            logDiv.scrollTop = logDiv.scrollHeight;
        });
    }

    if (data.donjon) {
        donjonState = data.donjon;
        updateDonjonHUD();
    }

    if (data.enemy_hp !== undefined && data.enemy_hp_max) {
        const bar = document.getElementById("donjon-enemy-hp-bar");
        if (bar) bar.style.width = Math.max(0, (data.enemy_hp / data.enemy_hp_max) * 100) + "%";
        const text = bar ? bar.nextElementSibling : null;
        if (text) text.textContent = `${Math.max(0, data.enemy_hp)} / ${data.enemy_hp_max}`;
    }

    if (data.resultat === "victoire") {
        stopDonjonCombat();
        donjonCombatActive = false;

        if (donjonState.etage === 19) {
            showBossVictory();
        } else {
            donjonChoices = data.choix_next || [];
            renderDonjonMap();
            showRoomPanel("⚔️ " + t("dj_victory_title"), `${data.log ? data.log[data.log.length - 1] : ""}`, []);
        }
    } else if (data.resultat === "defaite" || data.donjon_termine) {
        stopDonjonCombat();
        donjonCombatActive = false;
        donjonActive = false;
        showDonjonDefeat(data.message_defaite || t("dj_died"));
    }
}

function playReincarnationAnimation(chapitre, ptsParNiveau) {
    const overlay = document.getElementById("reincarnation-overlay");
    overlay.classList.remove("hidden");
    overlay.innerHTML = "";

    const flash = document.createElement("div");
    flash.className = "reinc-flash";
    overlay.appendChild(flash);

    const ring1 = document.createElement("div");
    ring1.className = "reinc-ring";
    overlay.appendChild(ring1);
    setTimeout(() => {
        const ring2 = document.createElement("div");
        ring2.className = "reinc-ring";
        ring2.style.animationDelay = "0.3s";
        overlay.appendChild(ring2);
    }, 300);

    const title = document.createElement("div");
    title.className = "reinc-title";
    title.textContent = t("dj_reincarnation_title");
    overlay.appendChild(title);

    const sub = document.createElement("div");
    sub.className = "reinc-subtitle";
    sub.textContent = t("dj_chapter_defeated").replace("{chap}", chapitre).replace("{pts}", ptsParNiveau);
    overlay.appendChild(sub);

    const colors = ["#ffd700", "#ff8c00", "#ff4500", "#fff", "#fbbf24", "#ef4444", "#a855f7"];
    for (let i = 0; i < 50; i++) {
        const p = document.createElement("div");
        p.className = "reinc-particle";
        const angle = Math.random() * Math.PI * 2;
        const dist = 150 + Math.random() * 400;
        const tx = Math.cos(angle) * dist;
        const ty = Math.sin(angle) * dist;
        const dur = 1.5 + Math.random() * 2;
        p.style.cssText = `
            left: 50%; top: 50%;
            background: ${colors[Math.floor(Math.random() * colors.length)]};
            width: ${4 + Math.random() * 8}px;
            height: ${4 + Math.random() * 8}px;
            --tx: ${tx}px; --ty: ${ty}px; --dur: ${dur}s;
            animation-delay: ${Math.random() * 0.5}s;
        `;
        overlay.appendChild(p);
    }

    for (let i = 0; i < 30; i++) {
        const s = document.createElement("div");
        s.className = "reinc-sparkle";
        s.style.cssText = `
            left: ${10 + Math.random() * 80}%;
            top: ${10 + Math.random() * 80}%;
            --dur: ${0.8 + Math.random() * 1.2}s;
            --delay: ${Math.random() * 2}s;
        `;
        overlay.appendChild(s);
    }

    setTimeout(() => {
        overlay.classList.add("hidden");
        overlay.innerHTML = "";
    }, 4000);
}

async function showBossVictory() {
    const res = await fetch("/api/donjon/action", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "boss_vaincu" }),
    });
    const data = await res.json();
    if (data.success) {
        donjonActive = false;
        donjonCombatActive = false;

        if (data.reincarnation) {
            playReincarnationAnimation(donjonState ? donjonState.chapitre : "?", data.pts_par_niveau);
        }

        setTimeout(() => {
            const panel = document.getElementById("donjon-room-panel");
            panel.classList.remove("hidden");
            document.getElementById("donjon-combat-panel").classList.remove("hidden");

            const itemsHTML = (data.items || []).map(it =>
                `<span class="rarity-${it.rarete}">• ${it.nom} (${it.rarete})</span>`
            ).join("<br>");

            let content;
            if (data.reincarnation) {
                const reincResult = t("dj_reincarnation_result")
                    .replace("{jetons}", data.jetons)
                    .replace("{total}", data.boss_battus_total)
                    .replace("{pts}", data.pts_par_niveau);
                content = `<div class="donjon-result-msg donjon-victory">
                    <strong>🔄 ${t("dj_reincarnation_title")} !</strong><br><br>
                    ${reincResult}
                    <br>${itemsHTML}
                </div>`;
                document.getElementById("donjon-room-header").textContent = "🏆 " + t("dj_boss_defeated_title") + " — " + t("dj_reincarnation_title") + " !";
            } else {
                content = `<div class="donjon-result-msg donjon-victory">
                    <strong>${t("dj_boss_defeated_title").toUpperCase()} !</strong><br><br>
                    ${data.message}<br>
                    ${itemsHTML}
                </div>`;
                document.getElementById("donjon-room-header").textContent = "🏆 " + t("dj_boss_defeated_title") + " !";
            }

            document.getElementById("donjon-room-content").innerHTML = content;
            document.getElementById("donjon-room-actions").innerHTML = `<button onclick="fermerDonjonVictoire()">${t("dj_return_game")}</button>`;
        }, data.reincarnation ? 3500 : 0);

        await fetchState();
    }
}

function showDonjonDefeat(message) {
    const combatPanel = document.getElementById("donjon-combat-panel");
    const roomPanel = document.getElementById("donjon-room-panel");

    const logDiv = document.getElementById("donjon-combat-log");
    const deathLine = document.createElement("div");
    deathLine.className = "log-line donjon-defeat";
    deathLine.textContent = "💀 " + message;
    logDiv.appendChild(deathLine);
    logDiv.scrollTop = logDiv.scrollHeight;

    combatPanel.classList.remove("hidden");

    roomPanel.classList.remove("hidden");
    document.getElementById("donjon-room-header").textContent = "💀 " + t("dj_defeat_title");
    document.getElementById("donjon-room-content").innerHTML = `<div class="donjon-result-msg donjon-defeat">${message}</div>`;
    document.getElementById("donjon-room-actions").innerHTML = `<button onclick="fermerDonjonVictoire()">${t("dj_return_game")}</button>`;
}

function fermerDonjonVictoire() {
    toggleDonjon();
    fetchState();
}

async function quitterDonjon() {
    if (!confirm(t("dj_abandon_confirm"))) return;
    const res = await fetch("/api/donjon/exit", { method: "POST" });
    const data = await res.json();
    donjonActive = false;
    donjonCombatActive = false;
    stopDonjonCombat();
    toggleDonjon();
    await fetchState();
}
