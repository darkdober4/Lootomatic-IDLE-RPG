const TICK_INTERVAL = 1000;
let currentTab = 0;
let logExpanded = true;
let gameState = null;
let tickTimer = null;
let enemyTimer = null;
let selectedOrbe = null;

const STAT_LABELS = {
    hp_max: "PV Max", atk: "ATQ", def: "DÉF", vit: "VIT",
    crit_chance: "Critique %", crit_mult: "Dégâts Crit. %",
    esquive: "Esquive %", chance_loot: "Chance Loot %",
    contre: "Contre-attaque %", vitesse_attaque: "Vit. Attaque",
    niveau_sorts: "Niveau Sorts",
};

const STAT_COSTS = {
    hp_max: 1, atk: 1, def: 1, vit: 1,
    crit_chance: 1, crit_mult: 5, esquive: 1,
    chance_loot: 1, contre: 1, vitesse_attaque: 1, niveau_sorts: 1,
};

const SLOT_LABELS = {
    arme: "⚔️ Arme", armure: "🦺 Armure", casque: "👑 Casque",
    bouclier: "🛡️ Bouclier", anneau: "💍 Anneau", amulette: "📿 Amulette",
    ceinture: "🎗️ Ceinture", bottes: "👢 Bottes", artefact: "✨ Artéfact",
    orbe: "🔮 Orbe",
};

const SLOT_ICONS = {
    arme: "⚔️", armure: "🦺", casque: "👑",
    bouclier: "🛡️", anneau: "💍", amulette: "📿",
    ceinture: "🎗️", bottes: "👢", artefact: "✨",
    orbe: "🔮",
};

const SORTS_INFO = {
    poison: { nom: "Poison", desc: "L'ennemi perd des PV a chaque seconde pendant 5 secondes." },
    surge_flammes: { nom: "Surge de Flammes", desc: "Frappe 3 fois, puis BOUM : une explosion de feu !" },
    hemorragie: { nom: "Hemorragie", desc: "Frappe 4 fois, puis l'ennemi saigne et perd des PV pendant 3 secondes." },
    gel_accumule: { nom: "Gel Accumule", desc: "Quand tu te fais taper 3 fois, l'ennemi est gele et rate sa prochaine attaque." },
    vengeance: { nom: "Vengeance", desc: "Encaisse 5 coups, puis renvoie tous les degats recus d'un seul coup !" },
    chaine_eclairs: { nom: "Chaine d'Eclairs", desc: "Se charge tout seul. Quand c'est plein, ZAP : un eclair frappe l'ennemi !" },
    vol_ame: { nom: "Vol d'Ame", desc: "Frappe 6 fois, puis tu voles la vie de l'ennemi a chaque coup pour le reste du combat." },
    lame_spectrale: { nom: "Lame Spectrale", desc: "Frappe 2 fois, puis ton prochain coup fait beaucoup plus mal !" },
    marque_maudite: { nom: "Marque Maudite", desc: "Frappe 3 fois, puis tes prochains coups font beaucoup plus mal !" },
    peau_fer: { nom: "Peau de Fer", desc: "Quand tu te fais taper 4 fois, un bouclier magique te protege du prochain coup." },
    distorsion: { nom: "Distorsion", desc: "Se charge tout seul. Quand c'est plein, tu attaques 2 fois plus vite pendant quelques secondes !" },
    execution: { nom: "Execution", desc: "Frappe 6 fois. Si l'ennemi est presque mort, TU LE FINIS avec un coup gigantesque !" },
};

const ORBE_DESCRIPTIONS = {
    amelioration: "Choisit une stat aléatoire sur l'objet et lui ajoute +1. Risque de 10% de corrompre l'objet.",
    alteration: "Ajoute un nouveau modificateur aléatoire à l'objet. 25% de chance de monter en rareté. 40% de corruption. Si l'objet atteint Mythique, il est automatiquement corrompu.",
};

async function fetchState() {
    const res = await fetch("/api/state");
    gameState = await res.json();
    renderAll();
}

async function combatTick() {
    const res = await fetch("/api/combat_tick", { method: "POST" });
    const data = await res.json();
    if (data.log) {
        data.log.forEach(line => addLogLine(line));
    }
    if (data.resultat) {
        await fetchState();
    } else {
        updateHP(data);
    }
}

async function enemyTick() {
    const res = await fetch("/api/enemy_tick", { method: "POST" });
    const data = await res.json();
    if (data.log) {
        data.log.forEach(line => addLogLine(line));
    }
    if (data.resultat) {
        await fetchState();
    } else {
        updateHP(data);
    }
}

function updateHP(data) {
    const pBar = document.getElementById("player-hp-bar");
    const pText = document.getElementById("player-hp-text");
    const eBar = document.getElementById("enemy-hp-bar");
    const eText = document.getElementById("enemy-hp-text");
    const pHpMax = data.player_hp_max || gameState.player.hp_max;
    const eHpMax = data.enemy_hp_max || gameState.enemy.hp_max;
    pBar.style.width = Math.max(0, (data.player_hp / pHpMax) * 100) + "%";
    pText.textContent = `${data.player_hp} / ${pHpMax}`;
    eBar.style.width = Math.max(0, (data.enemy_hp / eHpMax) * 100) + "%";
    eText.textContent = `${Math.max(0, data.enemy_hp)} / ${eHpMax}`;

    if (data.spell_stacks) {
        const ss = data.spell_stacks;
        const fill = document.querySelector(".stack-bar-fill");
        const text = document.querySelector(".stack-bar-text");
        if (fill && text && ss.max > 0) {
            fill.style.width = (ss.current / ss.max * 100) + "%";
            text.textContent = `${ss.current}/${ss.max}`;
        }
    }
}

function renderAll() {
    if (!gameState) return;
    renderPlayerStats();
    renderEnemy();
    renderEquipment();
    renderInventory();
    renderHeader();
    renderSpellDisplay();
    updateTickSpeed();
}

function renderHeader() {
    document.getElementById("or-display").textContent = "💰 " + gameState.player.or;
    document.getElementById("kill-display").textContent = "☠️ " + gameState.player.kill_count;
    const jetonEl = document.getElementById("jeton-display");
    if (jetonEl) jetonEl.textContent = "🪙 " + (gameState.player.jetons || 0);
}

function renderSpellDisplay() {
    const container = document.getElementById("spell-display");
    const spell = gameState.spell_info;
    if (!spell) {
        container.innerHTML = '<div class="spell-none">Aucun sort actif</div>';
        return;
    }
    let stackHtml = "";
    if (spell.stacks_max > 0) {
        const pct = (spell.stacks_current / spell.stacks_max * 100);
        stackHtml = `<div class="stack-bar-container">
            <div class="stack-bar-fill" style="width:${pct}%"></div>
            <span class="stack-bar-text">${spell.stacks_current}/${spell.stacks_max}</span>
        </div>`;
    }
    container.innerHTML = `<div class="spell-active">
        <span class="spell-name">${spell.nom}</span>
        <span class="spell-level">Niv.${spell.niveau}</span>
        ${stackHtml}
    </div>`;
}

function renderPlayerStats() {
    const p = gameState.player;
    document.getElementById("player-niveau").textContent = "Niv. " + p.niveau;

    const hpBar = document.getElementById("player-hp-bar");
    const hpText = document.getElementById("player-hp-text");
    hpBar.style.width = (p.hp / p.hp_max * 100) + "%";
    hpText.textContent = p.hp + " / " + p.hp_max;

    const xpBar = document.getElementById("player-xp-bar");
    const xpText = document.getElementById("player-xp-text");
    xpBar.style.width = (p.xp / p.xp_max * 100) + "%";
    xpText.textContent = p.xp + " / " + p.xp_max + " XP";

    const list = document.getElementById("stats-list");
    list.innerHTML = "";
    const eff = p.stats_effectives;
    for (const [key, label] of Object.entries(STAT_LABELS)) {
        const total = eff[key] || 0;
        const row = document.createElement("div");
        row.className = "stat-row";
        row.innerHTML = `<span class="stat-label">${label}</span><span class="stat-value">${total}</span>`;
        list.appendChild(row);
    }

    const ptsDisplay = document.getElementById("points-stats-display");
    const btnAlloc = document.getElementById("btn-alloc");
    if (p.donjon_actif) {
        ptsDisplay.textContent = "⚠️ Stats verrouillées (donjon en cours)";
        ptsDisplay.style.color = "#ef4444";
        btnAlloc.style.display = "none";
    } else {
        ptsDisplay.textContent = p.points_stats > 0 ? `${p.points_stats} points disponibles` : "Aucun point disponible";
        ptsDisplay.style.color = "#fbbf24";
        btnAlloc.style.display = "block";
    }
}

function renderEnemy() {
    const e = gameState.enemy;
    const nameEl = document.getElementById("enemy-name");
    nameEl.textContent = (e.boss ? "👑 " : "") + e.nom + " (Niv. " + e.niveau + ")";
    if (e.boss) nameEl.classList.add("boss-name");
    else nameEl.classList.remove("boss-name");

    const hpBar = document.getElementById("enemy-hp-bar");
    const hpText = document.getElementById("enemy-hp-text");
    hpBar.style.width = (e.hp / e.hp_max * 100) + "%";
    hpText.textContent = e.hp + " / " + e.hp_max;

    const list = document.getElementById("enemy-stats-list");
    list.innerHTML = "";
    for (const [key, label] of Object.entries(STAT_LABELS)) {
        if (key === "chance_loot" || key === "niveau_sorts") continue;
        const val = e.stats[key] || 0;
        if (val === 0) continue;
        const row = document.createElement("div");
        row.className = "stat-row";
        row.innerHTML = `<span class="stat-label">${label}</span><span class="stat-value">${val}</span>`;
        list.appendChild(row);
    }
}

function renderEquipment() {
    const container = document.getElementById("equip-slots");
    container.innerHTML = "";
    for (const [slot, item] of Object.entries(gameState.player.equipement)) {
        const div = document.createElement("div");
        div.className = "equip-slot";
        if (item) {
            const enchantLabel = item.enchant_level > 0 ? ` <span class="enchant-badge">+${item.enchant_level}</span>` : "";
            const canEnchant = item.slot !== "artefact" && item.slot !== "orbe" && item.enchant_level < 10;
            const enchantBtn = canEnchant ? `<button class="btn-enchant" onclick="event.stopPropagation();enchantEquipped('${slot}')" title="Enchanter">+</button>` : "";
            div.innerHTML = `<span class="slot-label">${SLOT_LABELS[slot] || slot}</span><span class="item-name rarity-${item.rarete}">${item.nom}${enchantLabel}</span>${enchantBtn}`;
            div.addEventListener("mouseenter", (ev) => showTooltip(ev, item));
            div.addEventListener("mouseleave", hideTooltip);
            div.addEventListener("click", () => desequiper(slot));
        } else {
            div.innerHTML = `<span class="slot-label">${SLOT_LABELS[slot] || slot}</span><span style="color:#555">Vide</span>`;
        }
        container.appendChild(div);
    }
}

function getItemStatValue(item, stat) {
    for (const mod of item.mods) {
        if (mod.stat === stat) return mod.valeur;
    }
    return 0;
}

function renderInventory() {
    const inv = gameState.player.inventaire;
    const tabsContainer = document.getElementById("inv-tabs");
    tabsContainer.innerHTML = "";
    inv.forEach((coffre, i) => {
        const btn = document.createElement("button");
        btn.textContent = "Coffre " + (i + 1);
        if (i === currentTab) btn.classList.add("active");
        btn.addEventListener("click", () => { currentTab = i; renderInventory(); });
        tabsContainer.appendChild(btn);
    });

    renderBatchDelete();

    const filterStat = document.getElementById("inv-filter-stat").value;
    const sortMode = document.getElementById("inv-sort-mode").value;

    tabsContainer.style.display = filterStat ? "none" : "flex";

    let entries = [];
    if (filterStat) {
        inv.forEach((coffre, ci) => {
            coffre.forEach((item, ii) => {
                if (getItemStatValue(item, filterStat) > 0) {
                    entries.push({ item, coffreIdx: ci, origIdx: ii });
                }
            });
        });
    } else {
        const rawCoffre = inv[currentTab] || [];
        rawCoffre.forEach((item, i) => {
            entries.push({ item, coffreIdx: currentTab, origIdx: i });
        });
    }

    if (sortMode === "rarete") {
        const rareteOrder = { "Commun": 0, "Rare": 1, "Épique": 2, "Légendaire": 3, "Mythique": 4 };
        entries.sort((a, b) => (rareteOrder[b.item.rarete] || 0) - (rareteOrder[a.item.rarete] || 0));
    } else if (sortMode === "stat" && filterStat) {
        entries.sort((a, b) => getItemStatValue(b.item, filterStat) - getItemStatValue(a.item, filterStat));
    } else if (sortMode === "niveau") {
        entries.sort((a, b) => b.item.niveau - a.item.niveau);
    }

    const grid = document.getElementById("inv-grid");
    grid.innerHTML = "";
    entries.forEach(({ item, coffreIdx, origIdx }) => {
        const div = document.createElement("div");
        const isOrbe = item.slot === "orbe";
        const isSelectedOrbe = selectedOrbe && selectedOrbe.coffre === coffreIdx && selectedOrbe.idx === origIdx;
        const isArtefact = item.slot === "artefact";
        div.className = "inv-slot"
            + (item.corrompu ? " corrupted" : "")
            + (item.locked ? " locked-item" : "")
            + (isOrbe ? " orbe-item" : "")
            + (isArtefact ? " item-artefact" : "")
            + (isSelectedOrbe ? " orbe-selected" : "");
        const icon = SLOT_ICONS[item.slot] || "📦";
        let label = icon + " " + item.nom;
        if (isOrbe && item.quantite > 1) label += ` x${item.quantite}`;
        const nameClass = item.locked ? "item-name rainbow-name" : `item-name rarity-${item.rarete}`;
        const lockIcon = item.locked ? "🔒" : "🔓";
        const lockTitle = item.locked ? "Deverrouiller" : "Verrouiller";
        const enchantLabel = item.enchant_level > 0 ? ` <span class="enchant-badge">+${item.enchant_level}</span>` : "";
        const canEnchant = !isOrbe && !isArtefact && !item.corrompu && item.enchant_level < 10;
        const enchantBtn = canEnchant ? `<button class="btn-enchant-inv" onclick="event.stopPropagation();enchantItem(${coffreIdx},${origIdx})" title="Enchanter">+</button>` : "";
        div.innerHTML = `<span class="${nameClass}">${label}${enchantLabel}</span>`
            + (item.corrompu ? '<span class="corrupt-badge">CORROMPU</span>' : '')
            + enchantBtn
            + `<button class="btn-lock" onclick="event.stopPropagation();toggleLock(${coffreIdx},${origIdx})" title="${lockTitle}">${lockIcon}</button>`
            + `<button class="btn-delete" onclick="event.stopPropagation();deleteItem(${coffreIdx},${origIdx})" title="Supprimer">✕</button>`;
        div.addEventListener("mouseenter", (ev) => showTooltip(ev, item));
        div.addEventListener("mouseleave", hideTooltip);
        div.addEventListener("click", () => {
            if (isOrbe) {
                if (isSelectedOrbe) {
                    selectedOrbe = null;
                } else {
                    selectedOrbe = { coffre: coffreIdx, idx: origIdx };
                }
                renderInventory();
            } else if (selectedOrbe) {
                utiliserOrbe(coffreIdx, origIdx);
            } else {
                equiper(coffreIdx, origIdx);
            }
        });
        grid.appendChild(div);
    });
    const displayed = entries.length;
    for (let i = displayed; i < 20; i++) {
        const div = document.createElement("div");
        div.className = "inv-slot";
        div.innerHTML = `<span style="color:#333">—</span>`;
        grid.appendChild(div);
    }
}

function buildItemTooltipHTML(item) {
    let html = `<div class="tooltip-name rarity-${item.rarete}">${item.slot === 'orbe' ? '🔮 ' : ''}${item.nom}</div>`;
    if (item.slot === "orbe") {
        const desc = ORBE_DESCRIPTIONS[item.orbe_type] || "";
        html += `<div class="tooltip-slot">🔮 Orbe</div>`;
        html += `<div class="tooltip-mod">${desc}</div>`;
    } else if (item.slot === "artefact" && item.spell_type) {
        const sort = SORTS_INFO[item.spell_type];
        html += `<div class="tooltip-slot">✨ Artéfact • ${item.rarete}</div>`;
        if (item.corrompu) html += `<div style="color:#f59e0b">⚠️ CORROMPU</div>`;
        if (sort) {
            html += `<div class="tooltip-mod" style="color:#c084fc">Sort : ${sort.nom}</div>`;
            html += `<div style="color:#aaa;font-size:0.72rem">${sort.desc}</div>`;
        }
    } else {
        const enchantStr = item.enchant_level > 0 ? ` • <span style="color:#f59e0b">+${item.enchant_level}</span>` : "";
        html += `<div class="tooltip-slot">${SLOT_LABELS[item.slot] || item.slot} • ${item.rarete} • Niv.${item.niveau}${enchantStr}</div>`;
        if (item.corrompu) html += `<div style="color:#f59e0b">CORROMPU</div>`;
        item.mods.forEach(mod => {
            const bonus = item.enchant_level > 0 ? Math.floor(mod.valeur * (1 + item.enchant_level * 0.1)) : mod.valeur;
            const bonusStr = bonus !== mod.valeur ? ` <span style="color:#f59e0b">(${bonus})</span>` : "";
            html += `<div class="tooltip-mod">+${mod.valeur} ${STAT_LABELS[mod.stat] || mod.stat}${bonusStr}</div>`;
        });
    }
    return html;
}

function buildComparisonHTML(item, equipped) {
    if (!equipped || !item || item.slot === "orbe" || item.slot === "artefact") return "";
    const itemMods = {};
    item.mods.forEach(m => { itemMods[m.stat] = m.valeur; });
    const equipMods = {};
    equipped.mods.forEach(m => { equipMods[m.stat] = m.valeur; });
    const allStats = new Set([...Object.keys(itemMods), ...Object.keys(equipMods)]);
    let html = `<div class="compare-header rarity-${equipped.rarete}">Équipé : ${equipped.nom}</div>`;
    allStats.forEach(stat => {
        const newVal = itemMods[stat] || 0;
        const oldVal = equipMods[stat] || 0;
        const diff = newVal - oldVal;
        const label = STAT_LABELS[stat] || stat;
        const diffStr = diff > 0 ? `<span class="compare-better">+${diff}</span>` : diff < 0 ? `<span class="compare-worse">${diff}</span>` : `<span class="compare-same">=</span>`;
        html += `<div class="compare-row"><span>${label}</span><span>${newVal} vs ${oldVal} ${diffStr}</span></div>`;
    });
    return html;
}

function showTooltip(ev, item) {
    hideTooltip();
    const tip = document.createElement("div");
    tip.className = "item-tooltip";
    tip.id = "active-tooltip";
    let html = buildItemTooltipHTML(item);

    if (item.slot !== "orbe" && item.slot !== "artefact" && gameState) {
        const equipped = gameState.player.equipement[item.slot];
        if (equipped) {
            html += '<div class="compare-separator"></div>';
            html += buildComparisonHTML(item, equipped);
        }
    }

    tip.innerHTML = html;
    document.body.appendChild(tip);
    tip.style.left = (ev.clientX + 15) + "px";
    tip.style.top = (ev.clientY + 10) + "px";
}

function hideTooltip() {
    const tip = document.getElementById("active-tooltip");
    if (tip) tip.remove();
}

async function equiper(coffreIdx, itemIdx) {
    await fetch("/api/equiper", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ coffre_idx: coffreIdx, item_idx: itemIdx }),
    });
    await fetchState();
}

async function desequiper(slot) {
    await fetch("/api/desequiper", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ slot }),
    });
    await fetchState();
}

function toggleAlloc() {
    const panel = document.getElementById("alloc-panel");
    if (panel.classList.contains("hidden")) {
        panel.classList.remove("hidden");
        renderAllocPanel();
    } else {
        panel.classList.add("hidden");
    }
}

function renderAllocPanel() {
    const panel = document.getElementById("alloc-panel");
    panel.innerHTML = "";
    for (const [key, label] of Object.entries(STAT_LABELS)) {
        const cout = STAT_COSTS[key] || 1;
        const row = document.createElement("div");
        row.className = "alloc-row";
        row.innerHTML = `<span>${label}</span><span style="color:#888;font-size:0.75rem">${cout}pt</span><button onclick="allouerStat('${key}')">+1</button><button onclick="allouerStat5('${key}')" style="margin-left:3px">+5</button>`;
        panel.appendChild(row);
    }
}

async function allouerStat5(stat) {
    for (let i = 0; i < 5; i++) {
        const res = await fetch("/api/alloquer_stat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ stat }),
        });
        const data = await res.json();
        if (!data.success) break;
    }
    await fetchState();
    renderAllocPanel();
}

async function allouerStat(stat) {
    await fetch("/api/alloquer_stat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ stat }),
    });
    await fetchState();
    renderAllocPanel();
}

function addLogLine(text) {
    const content = document.getElementById("log-content");
    const line = document.createElement("div");
    line.className = "log-line";
    line.textContent = text;
    content.appendChild(line);
    content.scrollTop = content.scrollHeight;
    if (content.children.length > 200) {
        content.removeChild(content.children[0]);
    }
}

function toggleLog() {
    const content = document.getElementById("log-content");
    const toggle = document.getElementById("log-toggle");
    logExpanded = !logExpanded;
    content.classList.toggle("collapsed");
    toggle.textContent = logExpanded ? "▼" : "▶";
}

function toggleOptions() {
    document.getElementById("options-panel").classList.toggle("hidden");
    loadSaveList();
    renderAutoSupprimer();
}

function toggleInfo() {
    document.getElementById("info-panel").classList.toggle("hidden");
}

async function loadSaveList() {
    const res = await fetch("/api/sauvegardes");
    const data = await res.json();
    const list = document.getElementById("save-list");
    if (data.fichiers.length === 0) {
        list.innerHTML = '<span style="color:#555">Aucune sauvegarde</span>';
        return;
    }
    list.innerHTML = "Sauvegardes : " + data.fichiers.map(f =>
        `<span class="save-item" onclick="document.getElementById('save-filename').value='${f}'">${f}</span>`
    ).join(", ");
}

async function openSavesFolder() {
    await fetch("/api/open_saves_folder", { method: "POST" });
}

async function sauvegarder(confirm_overwrite) {
    const filename = document.getElementById("save-filename").value || "sauvegarde.json";
    const res = await fetch("/api/sauvegarder", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ filename, confirm_overwrite }),
    });
    const data = await res.json();
    if (data.exists) {
        if (confirm(data.message)) {
            await sauvegarder(true);
        } else {
            document.getElementById("options-message").textContent = "Sauvegarde annulee.";
        }
        return;
    }
    document.getElementById("options-message").textContent = data.message;
    loadSaveList();
}

async function charger() {
    const filename = document.getElementById("save-filename").value || "sauvegarde.json";
    const res = await fetch("/api/charger", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ filename }),
    });
    const data = await res.json();
    document.getElementById("options-message").textContent = data.message;
    if (data.success) {
        await fetchState();
    }
}

async function newGame() {
    if (!confirm("Commencer une nouvelle partie ?\n\nToute progression non sauvegardée sera perdue.")) return;
    const res = await fetch("/api/new_game", { method: "POST" });
    const data = await res.json();
    document.getElementById("options-message").textContent = data.message;
    document.getElementById("log-content").innerHTML = "";
    await fetchState();
    addLogLine("🎮 Nouvelle partie !");
    addLogLine("⚔️ Le combat commence...");
}

async function skipEnemy() {
    const res = await fetch("/api/skip_enemy", { method: "POST" });
    const data = await res.json();
    addLogLine("⏭️ " + data.message);
    await fetchState();
}

async function prevEnemy() {
    const res = await fetch("/api/prev_enemy", { method: "POST" });
    const data = await res.json();
    addLogLine("◀ " + data.message);
    await fetchState();
}

async function enchantItem(coffreIdx, itemIdx) {
    const res = await fetch("/api/enchant", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ coffre_idx: coffreIdx, item_idx: itemIdx }),
    });
    const data = await res.json();
    addLogLine(data.message);
    await fetchState();
}

async function enchantEquipped(slot) {
    const res = await fetch("/api/enchant", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ slot }),
    });
    const data = await res.json();
    addLogLine(data.message);
    await fetchState();
}

async function toggleLock(coffreIdx, itemIdx) {
    const res = await fetch("/api/toggle_lock", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ coffre_idx: coffreIdx, item_idx: itemIdx }),
    });
    const data = await res.json();
    addLogLine(data.message);
    await fetchState();
}

async function deleteItem(coffreIdx, itemIdx) {
    if (!confirm("Supprimer cet objet ?")) return;
    const res = await fetch("/api/delete_item", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ coffre_idx: coffreIdx, item_idx: itemIdx }),
    });
    const data = await res.json();
    addLogLine(data.message);
    await fetchState();
}

async function deleteBatch(rarete) {
    if (!confirm(`Supprimer tous les objets ${rarete} ?`)) return;
    const res = await fetch("/api/delete_batch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ rarete }),
    });
    const data = await res.json();
    addLogLine("🗑️ " + data.message);
    await fetchState();
}

function renderBatchDelete() {
    let container = document.getElementById("batch-delete-panel");
    if (!container) {
        container = document.createElement("div");
        container.id = "batch-delete-panel";
        document.getElementById("inv-tabs").after(container);
    }
    container.innerHTML = '<span class="batch-label">Supprimer par rareté :</span>';
    const raretes = ["Commun", "Rare", "Épique", "Légendaire", "Mythique"];
    raretes.forEach(r => {
        const btn = document.createElement("button");
        btn.className = `btn-batch rarity-${r}`;
        btn.textContent = r;
        btn.addEventListener("click", () => deleteBatch(r));
        container.appendChild(btn);
    });
}

async function utiliserOrbe(cibleCoffreIdx, cibleItemIdx) {
    if (!selectedOrbe) return;
    const res = await fetch("/api/utiliser_orbe", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            orbe_coffre_idx: selectedOrbe.coffre,
            orbe_item_idx: selectedOrbe.idx,
            cible_coffre_idx: cibleCoffreIdx,
            cible_item_idx: cibleItemIdx,
        }),
    });
    const data = await res.json();
    addLogLine(data.message);
    selectedOrbe = null;
    await fetchState();
}

function updateTickSpeed() {
    if (!gameState) return;
    const vitesseJ = gameState.player.stats_effectives.vitesse_attaque || 100;
    const intervalJ = Math.max(200, Math.round(100000 / vitesseJ));
    if (tickTimer) clearInterval(tickTimer);
    tickTimer = setInterval(combatTick, intervalJ);

    const vitesseE = gameState.enemy.stats.vitesse_attaque || 100;
    const intervalE = Math.max(200, Math.round(100000 / vitesseE));
    if (enemyTimer) clearInterval(enemyTimer);
    enemyTimer = setInterval(enemyTick, intervalE);
}

// ─── MACHINE À SOUS ──────────────────────────────────────────────────────────

let slotMachineSpinning = false;
let pendingSlotGain = null;

const SLOT_MACHINE_SYMBOLES = [
    { id: "epee",     icone: "EPE" },
    { id: "bouclier", icone: "BOU" },
    { id: "potion",   icone: "POT" },
    { id: "gemme",    icone: "GEM" },
    { id: "couronne", icone: "CRN" },
    { id: "etoile",   icone: "ETO" },
    { id: "tresor",   icone: "TRE" },
];

const SLOT_MACHINE_SLOTS_CHOIX = {
    arme: "Arme", armure: "Armure", casque: "Casque",
    bouclier: "Bouclier", anneau: "Anneau", amulette: "Amulette",
    ceinture: "Ceinture", bottes: "Bottes",
};

async function spinSlotMachine() {
    if (slotMachineSpinning) return;

    if (!gameState || !gameState.player.jetons || gameState.player.jetons < 1) {
        document.getElementById("slot-result").textContent = "Pas assez de jetons !";
        document.getElementById("slot-result").className = "lose";
        return;
    }

    slotMachineSpinning = true;

    const btn = document.getElementById("btn-spin");
    const resultDiv = document.getElementById("slot-result");
    const chooser = document.getElementById("slot-chooser");
    btn.disabled = true;
    resultDiv.textContent = "";
    resultDiv.className = "";
    chooser.classList.add("hidden");

    const reels = [
        document.getElementById("reel-1"),
        document.getElementById("reel-2"),
        document.getElementById("reel-3"),
    ];

    reels.forEach(r => {
        r.classList.add("spinning");
        r.classList.remove("winner");
    });

    const spinIntervals = [];
    for (let i = 0; i < 3; i++) {
        spinIntervals.push(setInterval(() => {
            const sym = SLOT_MACHINE_SYMBOLES[Math.floor(Math.random() * SLOT_MACHINE_SYMBOLES.length)];
            reels[i].querySelector("span").textContent = sym.icone;
        }, 80));
    }

    function stopAllReels() {
        spinIntervals.forEach(id => clearInterval(id));
        reels.forEach(r => r.classList.remove("spinning"));
    }

    try {
        const res = await fetch("/api/slot_machine/spin", { method: "POST" });
        const data = await res.json();

        if (!data.success) {
            stopAllReels();
            resultDiv.textContent = data.message;
            resultDiv.className = "lose";
            btn.disabled = false;
            slotMachineSpinning = false;
            await fetchState();
            return;
        }

        const spinDurations = [500, 800, 1100];
        for (let i = 0; i < 3; i++) {
            setTimeout(() => {
                clearInterval(spinIntervals[i]);
                reels[i].classList.remove("spinning");
                reels[i].querySelector("span").textContent = data.resultats[i].icone;
            }, spinDurations[i]);
        }

        await new Promise(r => setTimeout(r, 1200));

        stopAllReels();
        reels.forEach((r, i) => {
            r.querySelector("span").textContent = data.resultats[i].icone;
        });

        resultDiv.textContent = data.message;

        if (data.gain) {
            resultDiv.className = "win";
            reels.forEach(r => r.classList.add("winner"));
            pendingSlotGain = data.gain;
            showSlotChooser(data.rarete);
        } else {
            resultDiv.className = "lose";
        }

        renderHeader();
    } catch (err) {
        stopAllReels();
        resultDiv.textContent = "Erreur de connexion !";
        resultDiv.className = "lose";
    }

    btn.disabled = false;
    slotMachineSpinning = false;
}

function showSlotChooser(rarete) {
    const chooser = document.getElementById("slot-chooser");
    const buttons = document.getElementById("slot-chooser-buttons");
    buttons.innerHTML = "";

    for (const [slot, label] of Object.entries(SLOT_MACHINE_SLOTS_CHOIX)) {
        const btn = document.createElement("button");
        btn.textContent = label;
        btn.addEventListener("click", () => claimSlotReward(slot));
        buttons.appendChild(btn);
    }

    chooser.classList.remove("hidden");
}

async function claimSlotReward(slot) {
    if (!pendingSlotGain) return;

    const chooser = document.getElementById("slot-chooser");
    const resultDiv = document.getElementById("slot-result");

    try {
        const res = await fetch("/api/slot_machine/claim", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ gain_type: pendingSlotGain, slot }),
        });
        const data = await res.json();

        if (data.success) {
            resultDiv.textContent = data.message;
            resultDiv.className = "win";
            chooser.classList.add("hidden");
            pendingSlotGain = null;
            addLogLine("[Slots] " + data.message);
            await fetchState();
        } else {
            resultDiv.textContent = data.message;
            resultDiv.className = "lose";
        }
    } catch (err) {
        resultDiv.textContent = "Erreur de connexion !";
    }
}

// ─── STATS OVERLAY ──────────────────────────────────────────────────────────

function toggleStatsOverlay() {
    const overlay = document.getElementById("stats-overlay");
    const wasHidden = overlay.classList.contains("hidden");
    overlay.classList.toggle("hidden");
    if (wasHidden) refreshStatsOverlay();
}

async function refreshStatsOverlay() {
    try {
        const res = await fetch("/api/session_stats");
        const data = await res.json();
        const container = document.getElementById("stats-overlay-content");

        const rariteColors = {
            "Commun": "#b0b0b0", "Rare": "#4a90d9", "Epique": "#a855f7",
            "Épique": "#a855f7", "Legendaire": "#f59e0b", "Légendaire": "#f59e0b",
            "Mythique": "#ef4444"
        };

        function line(key, val, highlight) {
            return '<div class="stat-line"><span class="stat-key">' + key
                + '</span><span class="stat-val' + (highlight ? ' highlight' : '')
                + '">' + val + '</span></div>';
        }

        let html = '';

        // Combat
        const c = data.combat;
        html += '<div class="stats-category"><h3>Combat</h3>';
        html += line("Kills", c.kills, true);
        html += line("Degats/coup moy.", c.degats_moyen);
        html += '</div>';

        // Loot
        const l = data.loot;
        html += '<div class="stats-category"><h3>Loot</h3>';
        html += line("Or gagne", l.or_gagne, true);
        html += line("Orbes obtenues", l.orbes_obtenues);
        for (const [r, count] of Object.entries(l.par_rarete)) {
            const col = rariteColors[r] || "#e0e0e0";
            html += '<div class="stat-line"><span class="stat-key" style="color:' + col + '">'
                + r + '</span><span class="stat-val">' + count + '</span></div>';
        }
        if (l.meilleur_loot) {
            const col = rariteColors[l.meilleur_loot.rarete] || "#e0e0e0";
            html += '<div class="stat-line"><span class="stat-key">Meilleur</span>'
                + '<span class="stat-val highlight" style="color:' + col + '">'
                + l.meilleur_loot.nom + '</span></div>';
        }
        html += '</div>';

        // Records
        const r = data.records;
        html += '<div class="stats-category"><h3>Records</h3>';
        html += line("Record kills sans mourir", r.record_kills_sans_mourir, true);
        html += line("Plus haut ennemi", "Niv." + r.plus_haut_ennemi);
        html += line("Plus gros coup", r.plus_gros_coup);
        html += line("Morts", r.morts);
        html += '</div>';

        container.innerHTML = html;
    } catch (e) {}
}

// ─── AUTO-SUPPRESSION ────────────────────────────────────────────────────────

const AUTO_SUPPR_RARETES = ["Commun", "Rare", "Épique", "Légendaire", "Mythique"];

function renderAutoSupprimer() {
    const grid = document.getElementById("auto-supprimer-grid");
    if (!grid) return;
    grid.innerHTML = "";
    const active = (gameState && gameState.player.auto_supprimer) || [];
    AUTO_SUPPR_RARETES.forEach(r => {
        const label = document.createElement("label");
        label.className = "auto-suppr-item";
        const cb = document.createElement("input");
        cb.type = "checkbox";
        cb.checked = active.includes(r);
        cb.addEventListener("change", () => toggleAutoSupprimer(r, cb.checked));
        label.appendChild(cb);
        label.appendChild(document.createTextNode(r));
        grid.appendChild(label);
    });
}

async function toggleAutoSupprimer(rarete, checked) {
    const active = (gameState && gameState.player.auto_supprimer) || [];
    let newSet;
    if (checked) {
        newSet = [...active, rarete];
    } else {
        newSet = active.filter(r => r !== rarete);
    }
    const res = await fetch("/api/auto_supprimer", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ raretes: newSet }),
    });
    const data = await res.json();
    if (gameState) gameState.player.auto_supprimer = data.auto_supprimer;
}

// ─── PRO-TIPS ────────────────────────────────────────────────────────────────

async function fetchProTip() {
    try {
        const res = await fetch("/api/pro_tip");
        const data = await res.json();
        const el = document.getElementById("pro-tip");
        if (el) {
            el.style.opacity = "0";
            setTimeout(() => {
                el.innerHTML = '<span class="tip-label">TIP :</span> ' + data.tip;
                el.style.opacity = "1";
            }, 300);
        }
    } catch (e) {}
}

// ─── ENCHANTEMENT ────────────────────────────────────────────────────────

let enchantSelectedItem = null;
const ENCHANT_COUT = { 0:100, 1:200, 2:400, 3:800, 4:1500, 5:3000, 6:5000, 7:8000, 8:12000, 9:20000 };
const ENCHANT_CHANCE = { 0:100, 1:90, 2:80, 3:70, 4:55, 5:40, 6:30, 7:20, 8:15, 9:10 };

function toggleEnchant() {
    const overlay = document.getElementById("enchant-overlay");
    overlay.classList.toggle("hidden");
    if (!overlay.classList.contains("hidden")) {
        enchantSelectedItem = null;
        renderEnchant();
    }
}

function renderEnchant() {
    document.getElementById("enchant-result").innerHTML = "";
    const selDiv = document.getElementById("enchant-selected-item");
    const infoDiv = document.getElementById("enchant-info");
    const btn = document.getElementById("enchant-btn");

    if (!enchantSelectedItem) {
        selDiv.innerHTML = '<span style="color:#555">Clique sur un objet ci-dessous</span>';
        infoDiv.innerHTML = "";
        btn.disabled = true;
    } else {
        const item = enchantSelectedItem.item;
        const icon = SLOT_ICONS[item.slot] || "";
        const enchStr = item.enchant_level > 0 ? ` <span class="enchant-badge">+${item.enchant_level}</span>` : "";
        selDiv.innerHTML = `<span class="item-name rarity-${item.rarete}">${icon} ${item.nom}${enchStr}</span>`;
        const cout = ENCHANT_COUT[item.enchant_level] || 0;
        const chance = ENCHANT_CHANCE[item.enchant_level] || 0;
        const nextLevel = item.enchant_level + 1;
        infoDiv.innerHTML = `
            <div class="enchant-stat">+${item.enchant_level} vers +${nextLevel}</div>
            <div class="enchant-stat">Cout : <span style="color:#f59e0b">${cout} or</span></div>
            <div class="enchant-stat">Chance : <span style="color:${chance >= 50 ? '#22c55e' : '#ef4444'}">${chance}%</span></div>
            <div class="enchant-stat" style="color:#ef4444;font-size:0.75rem">Echec = corruption de l'objet !</div>`;
        btn.disabled = false;
    }

    const inv = document.getElementById("enchant-inventory");
    inv.innerHTML = "";
    const p = gameState.player;
    p.inventaire.forEach((coffre, ci) => {
        coffre.forEach((item, ii) => {
            if (item.slot === "orbe" || item.slot === "artefact") return;
            if (item.corrompu) return;
            if (item.enchant_level >= 10) return;
            const isSelected = enchantSelectedItem && enchantSelectedItem.coffre === ci && enchantSelectedItem.idx === ii;
            const div = document.createElement("div");
            div.className = "enchant-inv-item" + (isSelected ? " enchant-item-selected" : "");
            const icon = SLOT_ICONS[item.slot] || "";
            const enchStr = item.enchant_level > 0 ? ` +${item.enchant_level}` : "";
            div.innerHTML = `<span class="item-name rarity-${item.rarete}">${icon} ${item.nom}${enchStr}</span>`;
            div.onclick = () => {
                enchantSelectedItem = { coffre: ci, idx: ii, item };
                renderEnchant();
            };
            inv.appendChild(div);
        });
    });
}

async function enchantSelected() {
    if (!enchantSelectedItem) return;
    const res = await fetch("/api/enchant", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ coffre_idx: enchantSelectedItem.coffre, item_idx: enchantSelectedItem.idx }),
    });
    const data = await res.json();
    const resultDiv = document.getElementById("enchant-result");
    if (data.success && data.reussi) {
        resultDiv.innerHTML = `<div class="chaudron-success">${data.message}</div>`;
    } else if (data.success) {
        resultDiv.innerHTML = `<div class="chaudron-error">${data.message}</div>`;
    } else {
        resultDiv.innerHTML = `<div class="chaudron-error">${data.message}</div>`;
    }
    addLogLine(data.message);
    enchantSelectedItem = null;
    await fetchState();
    renderEnchant();
}

// ─── CHAUDRON MAGIQUE ────────────────────────────────────────────────────

let chaudronSelected = [];
const CHAUDRON_COUT_BASE = 50;
const CHAUDRON_COUT_RARETE = { "Commun": 0, "Rare": 25, "Épique": 75, "Légendaire": 200, "Mythique": 500 };

function toggleChaudron() {
    const overlay = document.getElementById("chaudron-overlay");
    overlay.classList.toggle("hidden");
    if (!overlay.classList.contains("hidden")) {
        chaudronSelected = [];
        renderChaudron();
    }
}

function renderChaudron() {
    for (let i = 0; i < 3; i++) {
        const slot = document.getElementById(`chaudron-slot-${i}`);
        const sel = chaudronSelected[i];
        if (sel) {
            const item = sel.item;
            const icon = SLOT_ICONS[item.slot] || "";
            slot.innerHTML = `<span class="item-name rarity-${item.rarete}">${icon} ${item.nom}</span>
                <button class="chaudron-remove" onclick="chaudronRemove(${i})">Retirer</button>`;
            slot.classList.add("filled");
        } else {
            slot.innerHTML = `<span class="chaudron-slot-label">Objet ${i + 1}</span>`;
            slot.classList.remove("filled");
        }
    }

    let cout = CHAUDRON_COUT_BASE;
    chaudronSelected.forEach(s => {
        if (s) cout += (CHAUDRON_COUT_RARETE[s.item.rarete] || 0);
    });
    document.getElementById("chaudron-cost").textContent = `Cout : ${cout} or`;
    document.getElementById("chaudron-fondre-btn").disabled = chaudronSelected.filter(Boolean).length < 3;
    document.getElementById("chaudron-result").innerHTML = "";

    const filterRarete = document.getElementById("chaudron-filter-rarete").value;
    const inv = document.getElementById("chaudron-inventory");
    inv.innerHTML = "";
    const p = gameState.player;
    p.inventaire.forEach((coffre, ci) => {
        coffre.forEach((item, ii) => {
            if (item.slot === "orbe" || item.slot === "artefact") return;
            if (item.locked) return;
            if (filterRarete && item.rarete !== filterRarete) return;
            const isUsed = chaudronSelected.some(s => s && s.coffre === ci && s.idx === ii);
            if (isUsed) return;
            const div = document.createElement("div");
            div.className = "chaudron-inv-item";
            const icon = SLOT_ICONS[item.slot] || "";
            div.innerHTML = `<span class="item-name rarity-${item.rarete}">${icon} ${item.nom}</span>`;
            div.onclick = () => chaudronAdd(ci, ii, item);
            inv.appendChild(div);
        });
    });
}

function chaudronAdd(coffre, idx, item) {
    if (chaudronSelected.filter(Boolean).length >= 3) return;
    const slot = chaudronSelected.indexOf(undefined);
    const emptySlot = chaudronSelected.length < 3 ? chaudronSelected.length : slot;
    if (emptySlot < 0 || emptySlot >= 3) {
        for (let i = 0; i < 3; i++) {
            if (!chaudronSelected[i]) { chaudronSelected[i] = { coffre, idx, item }; break; }
        }
    } else {
        chaudronSelected[emptySlot] = { coffre, idx, item };
    }
    while (chaudronSelected.length < 3) chaudronSelected.push(undefined);
    renderChaudron();
}

function chaudronRemove(slotIdx) {
    chaudronSelected[slotIdx] = undefined;
    renderChaudron();
}

async function chaudronFondre() {
    const items = chaudronSelected.filter(Boolean).map(s => ({
        coffre_idx: s.coffre,
        item_idx: s.idx,
    }));
    const res = await fetch("/api/chaudron/fondre", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ items }),
    });
    const data = await res.json();
    const resultDiv = document.getElementById("chaudron-result");
    if (data.success) {
        const item = data.item;
        const icon = SLOT_ICONS[item.slot] || "";
        const modsHtml = item.mods.map(m =>
            `<div class="chaudron-mod">+${m.valeur} ${m.nom}</div>`
        ).join("");
        addLogLine(data.message);
        chaudronSelected = [];
        await fetchState();
        renderChaudron();
        document.getElementById("chaudron-result").innerHTML = `
            <div class="chaudron-popup">
                <div class="chaudron-popup-title">Objet obtenu !</div>
                <div class="item-name rarity-${item.rarete}" style="font-size:1.1rem">${icon} ${item.nom}</div>
                <div class="chaudron-rarete">${item.rarete}</div>
                ${modsHtml}
            </div>`;
    } else {
        resultDiv.innerHTML = `<div class="chaudron-error">${data.message}</div>`;
    }
}

document.addEventListener("keydown", (e) => {
    if (e.code === "Space") {
        const overlay = document.getElementById("chaudron-overlay");
        if (overlay && !overlay.classList.contains("hidden")) {
            const btn = document.getElementById("chaudron-fondre-btn");
            if (btn && !btn.disabled) {
                e.preventDefault();
                chaudronFondre();
            }
        }
    }
});

document.addEventListener("DOMContentLoaded", async () => {
    await fetchState();
    addLogLine("Bienvenue dans Lootomatic !");
    addLogLine("Le combat commence...");
    updateTickSpeed();
    fetchProTip();
    setInterval(fetchProTip, 10000);

    const filterSelect = document.getElementById("inv-filter-stat");
    const sortSelect = document.getElementById("inv-sort-mode");
    if (filterSelect) filterSelect.addEventListener("change", () => renderInventory());
    if (sortSelect) sortSelect.addEventListener("change", () => renderInventory());
});
