import sys
import os
import webbrowser
import threading
sys.path.insert(0, os.path.dirname(__file__))

from flask import Flask, render_template, jsonify, request
from game.models import Player, Enemy, Item
from game.combat import tick_player_attack, tick_enemy_attack
from game.save import sauvegarder, charger, liste_sauvegardes
from game.translations import tr

app = Flask(__name__)

player = None
enemy = None
max_niveau_debloque = 1
donjon_enemy = None


def _spawn_enemy(niveau, player, force_non_boss=False):
    if force_non_boss:
        return Enemy(niveau=niveau, boss=False)
    if getattr(player, 'force_boss', False) and len(getattr(player, 'chapitres_completees', [])) >= 5:
        return Enemy(niveau=niveau, boss=True)
    return Enemy(niveau=niveau)


def get_or_init_game():
    global player, enemy, max_niveau_debloque
    if player is None:
        player = Player()
        enemy = Enemy(niveau=1)
        max_niveau_debloque = 1
        import time
        player.session_stats["debut_session"] = time.time()
    return player, enemy


def _track_equipment_charges(player):
    import random as _r
    from config import EVOLUTION_PALIERS, EVOLUTION_PALIERS_RARETE, EVOLUTION_SUFFIXES, MODIFICATEURS, RARITE_MULT
    messages = []
    for slot, item in player.equipement.items():
        if item is None or item.slot in ("orbe", "artefact") or item.corrompu:
            continue
        if not getattr(item, 'vivant', False):
            continue
        if item.evolution_tier >= 3:
            continue
        item.charges += 1
        base_palier = EVOLUTION_PALIERS.get(item.evolution_tier + 1, 999999)
        rarete_mult = EVOLUTION_PALIERS_RARETE.get(item.rarete, 1.0)
        palier = int(base_palier * rarete_mult)
        if item.charges >= palier:
            item.evolution_tier += 1
            item.charges = 0
            mods_disponibles = [m for m in MODIFICATEURS if m["stat"] not in [mod["stat"] for mod in item.mods]]
            if mods_disponibles:
                mod_choisi = _r.choice(mods_disponibles)
                mult = RARITE_MULT.get(item.rarete, 1.0)
                val_min = max(1, int(mod_choisi["min"] * mult * (1 + item.niveau * 0.1)))
                val_max = max(val_min + 1, int(mod_choisi["max"] * mult * (1 + item.niveau * 0.1)))
                valeur = _r.randint(val_min, val_max)
                item.mods.append({"nom": mod_choisi["nom"], "stat": mod_choisi["stat"], "valeur": valeur})
            suffix = EVOLUTION_SUFFIXES.get(item.evolution_tier, "")
            base_nom = item.nom.split(" (")[0] if " (" in item.nom else item.nom
            item.nom = f"{base_nom} ({suffix})"
            messages.append(f"{item.nom} evolue ! Nouveau mod : +{valeur if mods_disponibles else 0} {mod_choisi['nom'] if mods_disponibles else 'rien'}")
    return messages


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/state")
def api_state():
    p, e = get_or_init_game()
    from game.spells import get_active_spells, spell_state
    from config import SORTS, RARITE_SORT_NIVEAU
    active_spells = get_active_spells(p)
    spell_info = None
    if active_spells:
        s = active_spells[0]
        trigger = s["data"]["trigger"]
        stacks_current = spell_state.get_stacks(s["key"])
        stacks_max = s["data"].get("stack_threshold", 0)
        spell_info = {
            "nom": s["data"]["nom"],
            "categorie": s["data"]["categorie"],
            "description": s["data"]["description"],
            "niveau": s["niveau"],
            "value": s["value"],
            "trigger": trigger,
            "stacks_current": stacks_current,
            "stacks_max": stacks_max,
        }
    return jsonify({
        "player": {
            "niveau": p.niveau,
            "xp": p.xp,
            "xp_max": p.xp_max,
            "points_stats": p.points_stats,
            "stats": p.stats,
            "stats_effectives": p.get_stats_effectives(),
            "hp": p.hp,
            "hp_max": p.get_stats_effectives()["hp_max"],
            "or": p.or_,
            "equipement": {
                slot: item.to_dict() if item else None
                for slot, item in p.equipement.items()
            },
            "inventaire": [
                [item.to_dict() for item in coffre]
                for coffre in p.inventaire
            ],
            "kill_count": p.kill_count,
            "orbes": p.orbes,
            "jetons": p.jetons,
            "boss_donjon_battus": p.boss_donjon_battus,
            "chapitres_completees": p.chapitres_completees,
            "donjon_actif": p.donjon_actif is not None,
            "auto_supprimer": p.auto_supprimer,
            "force_boss": p.force_boss,
            "lang": p.lang,
        },
        "enemy": {
            "nom": e.nom,
            "niveau": e.niveau,
            "boss": e.boss,
            "stats": e.stats,
            "hp": e.hp,
            "hp_max": e.stats["hp_max"],
        },
        "max_niveau_debloque": max_niveau_debloque,
        "spell_info": spell_info,
    })


@app.route("/api/combat_tick", methods=["POST"])
def api_combat_tick():
    global enemy, max_niveau_debloque
    from game.spells import spell_state
    p, e = get_or_init_game()
    resultat = tick_player_attack(p, e)
    if resultat["resultat"] in ("victoire", "defaite"):
        spell_state.reset()
        if resultat["resultat"] == "victoire":
            p.hp = p.get_stats_effectives()["hp_max"]
            evo_msgs = _track_equipment_charges(p)
            resultat["log"].extend(evo_msgs)
            if e.niveau >= max_niveau_debloque:
                max_niveau_debloque = e.niveau + 1
                enemy = _spawn_enemy(max_niveau_debloque, p)
            else:
                enemy = _spawn_enemy(e.niveau, p)
        else:
            enemy = _spawn_enemy(e.niveau, p)
    return jsonify(resultat)


@app.route("/api/enemy_tick", methods=["POST"])
def api_enemy_tick():
    global enemy, max_niveau_debloque
    from game.spells import spell_state
    p, e = get_or_init_game()
    if e.hp <= 0 or p.hp <= 0:
        return jsonify({"log": [], "resultat": None, "recompenses": {},
                        "player_hp": p.hp, "player_hp_max": p.get_stats_effectives()["hp_max"],
                        "enemy_hp": max(0, e.hp), "enemy_hp_max": e.stats["hp_max"]})
    resultat = tick_enemy_attack(p, e)
    if resultat["resultat"] in ("victoire", "defaite"):
        spell_state.reset()
        if resultat["resultat"] == "victoire":
            p.hp = p.get_stats_effectives()["hp_max"]
            evo_msgs = _track_equipment_charges(p)
            resultat["log"].extend(evo_msgs)
            if e.niveau >= max_niveau_debloque:
                max_niveau_debloque = e.niveau + 1
                enemy = _spawn_enemy(max_niveau_debloque, p)
            else:
                enemy = _spawn_enemy(e.niveau, p)
        else:
            enemy = _spawn_enemy(e.niveau, p)
    return jsonify(resultat)


@app.route("/api/skip_enemy", methods=["POST"])
def api_skip_enemy():
    global enemy, max_niveau_debloque
    p, e = get_or_init_game()
    lang = getattr(p, 'lang', 'fr')
    data = request.get_json() or {}
    amount = data.get("amount", 1)
    nouveau_niveau = e.niveau + amount
    if nouveau_niveau > max_niveau_debloque:
        max_niveau_debloque = nouveau_niveau
    enemy = _spawn_enemy(nouveau_niveau, p)
    p.hp = p.get_stats_effectives()["hp_max"]
    return jsonify({
        "success": True,
        "message": tr('api_skip_enemy', lang, niv=nouveau_niveau, nom=enemy.nom),
        "max_niveau": max_niveau_debloque,
    })


@app.route("/api/prev_enemy", methods=["POST"])
def api_prev_enemy():
    global enemy
    p, e = get_or_init_game()
    lang = getattr(p, 'lang', 'fr')
    data = request.get_json() or {}
    amount = data.get("amount", 1)
    nouveau_niveau = max(1, e.niveau - amount)
    enemy = _spawn_enemy(nouveau_niveau, p, force_non_boss=True)
    p.hp = p.get_stats_effectives()["hp_max"]
    return jsonify({
        "success": True,
        "message": tr('api_prev_enemy', lang, niv=nouveau_niveau, nom=enemy.nom),
        "max_niveau": max_niveau_debloque,
    })


@app.route("/api/alloquer_stat", methods=["POST"])
def api_allouer_stat():
    p, _ = get_or_init_game()
    lang = getattr(p, 'lang', 'fr')
    if p.donjon_actif is not None:
        return jsonify({"success": False, "message": tr('api_no_stats_dungeon', lang)})
    data = request.get_json()
    stat = data.get("stat")
    amount = data.get("amount", 1)
    allocated = 0
    for _ in range(amount):
        if p.allouer_stat(stat):
            allocated += 1
        else:
            break
    return jsonify({"success": allocated > 0, "allocated": allocated, "points_restants": p.points_stats, "stats": p.stats})


@app.route("/api/equiper", methods=["POST"])
def api_equiper():
    p, _ = get_or_init_game()
    data = request.get_json()
    coffre_idx = data.get("coffre_idx", 0)
    item_idx = data.get("item_idx", 0)
    ancien = p.equiper_item(coffre_idx, item_idx)
    return jsonify({
        "success": True,
        "equipement": {
            slot: item.to_dict() if item else None
            for slot, item in p.equipement.items()
        },
        "inventaire": [
            [item.to_dict() for item in coffre]
            for coffre in p.inventaire
        ],
    })


@app.route("/api/desequiper", methods=["POST"])
def api_desequiper():
    p, _ = get_or_init_game()
    data = request.get_json()
    slot = data.get("slot")
    ok = p.desequiper_item(slot)
    return jsonify({
        "success": ok,
        "equipement": {
            slot: item.to_dict() if item else None
            for slot, item in p.equipement.items()
        },
        "inventaire": [
            [item.to_dict() for item in coffre]
            for coffre in p.inventaire
        ],
    })


def _consolider_inventaire(p):
    tous_les_items = []
    for coffre in p.inventaire:
        tous_les_items.extend(coffre)
    p.inventaire = [[]]
    for item in tous_les_items:
        p.ajouter_item(item)


@app.route("/api/delete_item", methods=["POST"])
def api_delete_item():
    p, _ = get_or_init_game()
    lang = getattr(p, 'lang', 'fr')
    data = request.get_json()
    coffre_idx = data.get("coffre_idx", 0)
    item_idx = data.get("item_idx", 0)
    if coffre_idx >= len(p.inventaire):
        return jsonify({"success": False, "message": tr('api_chest_invalid', lang)})
    coffre = p.inventaire[coffre_idx]
    if item_idx >= len(coffre):
        return jsonify({"success": False, "message": tr('api_item_invalid', lang)})
    if coffre[item_idx].locked:
        return jsonify({"success": False, "message": tr('api_item_locked', lang)})
    item = coffre.pop(item_idx)
    _consolider_inventaire(p)
    return jsonify({
        "success": True,
        "message": tr('api_item_deleted', lang, nom=item.nom),
        "or_gagne": 0,
    })


@app.route("/api/delete_batch", methods=["POST"])
def api_delete_batch():
    p, _ = get_or_init_game()
    lang = getattr(p, 'lang', 'fr')
    data = request.get_json()
    rarete = data.get("rarete")
    count = 0
    locked_skipped = 0
    for coffre in p.inventaire:
        items_a_garder = []
        for item in coffre:
            if rarete and item.rarete == rarete and item.slot not in ("orbe", "artefact") and not item.locked and not getattr(item, 'vivant', False):
                count += 1
            else:
                if rarete and item.rarete == rarete and item.locked:
                    locked_skipped += 1
                items_a_garder.append(item)
        coffre.clear()
        coffre.extend(items_a_garder)
    _consolider_inventaire(p)
    msg = tr('api_batch_deleted', lang, n=count, rar=rarete)
    if locked_skipped > 0:
        msg += " " + tr('api_batch_locked_skipped', lang, n=locked_skipped)
    return jsonify({
        "success": True,
        "message": msg,
    })


@app.route("/api/delete_artefacts", methods=["POST"])
def api_delete_artefacts():
    p, _ = get_or_init_game()
    lang = getattr(p, 'lang', 'fr')
    count = 0
    locked_skipped = 0
    for coffre in p.inventaire:
        items_a_garder = []
        for item in coffre:
            if item.slot == "artefact" and not item.locked:
                count += 1
            else:
                if item.slot == "artefact" and item.locked:
                    locked_skipped += 1
                items_a_garder.append(item)
        coffre.clear()
        coffre.extend(items_a_garder)
    _consolider_inventaire(p)
    msg = tr('api_artefacts_deleted', lang, n=count)
    if locked_skipped > 0:
        msg += " " + tr('api_batch_locked_skipped', lang, n=locked_skipped)
    return jsonify({
        "success": True,
        "message": msg,
    })


@app.route("/api/toggle_lock", methods=["POST"])
def api_toggle_lock():
    p, _ = get_or_init_game()
    lang = getattr(p, 'lang', 'fr')
    data = request.get_json()
    coffre_idx = data.get("coffre_idx", 0)
    item_idx = data.get("item_idx", 0)
    if coffre_idx >= len(p.inventaire):
        return jsonify({"success": False, "message": tr('api_chest_invalid', lang)})
    coffre = p.inventaire[coffre_idx]
    if item_idx >= len(coffre):
        return jsonify({"success": False, "message": tr('api_item_invalid', lang)})
    item = coffre[item_idx]
    item.locked = not item.locked
    state = tr('api_locked', lang) if item.locked else tr('api_unlocked', lang)
    return jsonify({
        "success": True,
        "locked": item.locked,
        "message": tr('api_lock_toggled', lang, nom=item.nom, state=state),
    })


@app.route("/api/enchant", methods=["POST"])
def api_enchant():
    import random as _r
    p, _ = get_or_init_game()
    lang = getattr(p, 'lang', 'fr')
    data = request.get_json()

    from config import ENCHANT_MAX, ENCHANT_COUT_OR, ENCHANT_CHANCE_REUSSITE

    slot = data.get("slot")
    if slot and slot in p.equipement and p.equipement[slot] is not None:
        item = p.equipement[slot]
    else:
        coffre_idx = data.get("coffre_idx", 0)
        item_idx = data.get("item_idx", 0)
        if coffre_idx >= len(p.inventaire):
            return jsonify({"success": False, "message": tr('api_chest_invalid', lang)})
        coffre = p.inventaire[coffre_idx]
        if item_idx >= len(coffre):
            return jsonify({"success": False, "message": tr('api_item_invalid', lang)})
        item = coffre[item_idx]
    if item.slot in ("orbe", "artefact"):
        return jsonify({"success": False, "message": tr('api_enchant_not_possible', lang)})
    if item.enchant_level >= ENCHANT_MAX:
        return jsonify({"success": False, "message": tr('api_enchant_max', lang, max=ENCHANT_MAX)})

    cout = ENCHANT_COUT_OR.get(item.enchant_level, 99999)
    if p.or_ < cout:
        return jsonify({"success": False, "message": tr('api_not_enough_gold', lang, cout=cout)})

    p.or_ -= cout
    chance = ENCHANT_CHANCE_REUSSITE.get(item.enchant_level, 0)

    if _r.random() * 100 < chance:
        item.enchant_level += 1
        return jsonify({
            "success": True,
            "reussi": True,
            "message": tr('api_enchant_success', lang, nom=item.nom, niv=item.enchant_level),
            "enchant_level": item.enchant_level,
        })
    else:
        item.enchant_level = 0
        item.corrompu = True
        return jsonify({
            "success": True,
            "reussi": False,
            "message": tr('api_enchant_fail', lang, nom=item.nom),
            "enchant_level": 0,
        })


@app.route("/api/utiliser_orbe", methods=["POST"])
def api_utiliser_orbe():
    p, _ = get_or_init_game()
    lang = getattr(p, 'lang', 'fr')
    data = request.get_json()
    orbe_coffre = data.get("orbe_coffre_idx")
    orbe_idx = data.get("orbe_item_idx")
    cible_coffre = data.get("cible_coffre_idx")
    cible_idx = data.get("cible_item_idx")

    if orbe_coffre >= len(p.inventaire):
        return jsonify({"success": False, "message": tr('api_orb_chest_invalid', lang)})
    orbe_item = p.inventaire[orbe_coffre][orbe_idx]
    if not getattr(orbe_item, "orbe_type", None):
        return jsonify({"success": False, "message": tr('api_not_an_orb', lang)})

    if cible_coffre >= len(p.inventaire):
        return jsonify({"success": False, "message": tr('api_target_chest_invalid', lang)})
    cible_item = p.inventaire[cible_coffre][cible_idx]
    if cible_item.slot == "orbe":
        return jsonify({"success": False, "message": tr('api_orb_on_orb', lang)})

    orbe_type = orbe_item.orbe_type

    if cible_item.corrompu and orbe_type != "purification":
        return jsonify({"success": False, "message": tr('api_corrupted', lang)})

    from config import ORBE_TYPES, MODIFICATEURS, RARITES, RARITE_MULT
    import random

    message = ""

    if orbe_type == "amelioration":
        if not cible_item.mods:
            return jsonify({"success": False, "message": tr('api_no_stats_to_enhance', lang)})
        mod_choisi = random.choice(cible_item.mods)
        mod_choisi["valeur"] += 1
        message = tr('api_orb_enhance_result', lang, stats=f"{cible_item.nom} : {mod_choisi['nom']} +1 (+{mod_choisi['valeur']})")
        if random.random() * 100 < 10:
            cible_item.corrompu = True
            message += " " + tr('api_orb_corrupted', lang)

    elif orbe_type == "alteration":
        mods_disponibles = [m for m in MODIFICATEURS if m["stat"] not in [mod["stat"] for mod in cible_item.mods]]
        if not mods_disponibles:
            return jsonify({"success": False, "message": tr('api_all_mods_present', lang)})

        mod_choisi = random.choice(mods_disponibles)
        mult = RARITE_MULT.get(cible_item.rarete, 1.0)
        niveau_mult = 1 + cible_item.niveau * 0.1
        val_min = max(1, int(mod_choisi["min"] * mult * niveau_mult))
        val_max = max(val_min + 1, int(mod_choisi["max"] * mult * niveau_mult))
        valeur = random.randint(val_min, val_max)
        cible_item.mods.append({"nom": mod_choisi["nom"], "stat": mod_choisi["stat"], "valeur": valeur})
        message = tr('api_orb_alter_result', lang, nom=cible_item.nom, val=valeur, stat=mod_choisi['nom'])

        if random.random() * 100 < ORBE_TYPES["alteration"]["rarete_up_chance"]:
            idx = RARITES.index(cible_item.rarete)
            if idx < len(RARITES) - 1:
                cible_item.rarete = RARITES[idx + 1]
                cible_item.nom = cible_item._generer_nom()
                message += " " + tr('api_orb_alter_rarity_up', lang, rar=cible_item.rarete)
                if cible_item.rarete == "Mythique":
                    cible_item.corrompu = True
                    message += " " + tr('api_orb_alter_corrupt', lang)

        if not cible_item.corrompu and random.random() * 100 < ORBE_TYPES["alteration"]["corruption_chance"]:
            cible_item.corrompu = True
            message += " " + tr('api_orb_corrupted', lang)

    elif orbe_type == "echange":
        if len(cible_item.mods) < 2:
            return jsonify({"success": False, "message": tr('api_need_2_mods', lang)})
        mod_a, mod_b = random.sample(cible_item.mods, 2)
        mod_a["valeur"], mod_b["valeur"] = mod_b["valeur"], mod_a["valeur"]
        message = tr('api_orb_exchange_result', lang, a=mod_a['nom'], av=mod_a['valeur'], b=mod_b['nom'], bv=mod_b['valeur'])
        if random.random() * 100 < ORBE_TYPES["echange"]["corruption_chance"]:
            cible_item.corrompu = True
            message += " " + tr('api_orb_corrupted', lang)

    elif orbe_type == "fragilite":
        if len(cible_item.mods) < 2:
            return jsonify({"success": False, "message": tr('api_need_2_mods_frag', lang)})
        mod_boost = random.choice(cible_item.mods)
        mods_sauf_boost = [m for m in cible_item.mods if m is not mod_boost]
        mod_supprime = random.choice(mods_sauf_boost)
        ancien_val = mod_boost["valeur"]
        mod_boost["valeur"] = int(mod_boost["valeur"] * 1.5)
        cible_item.mods.remove(mod_supprime)
        message = tr('api_orb_frag_result', lang, a=mod_boost['nom'], old=ancien_val, new=mod_boost['valeur'], b=mod_supprime['nom'])
        if random.random() * 100 < ORBE_TYPES["fragilite"]["corruption_chance"]:
            cible_item.corrompu = True
            message += " " + tr('api_orb_corrupted', lang)

    elif orbe_type == "polymorphie":
        from config import SLOTS_EQUIPEMENT
        slots_possibles = [s for s in SLOTS_EQUIPEMENT if s not in ("artefact", cible_item.slot)]
        nouveau_slot = random.choice(slots_possibles)
        ancien_slot = cible_item.slot
        cible_item.slot = nouveau_slot
        cible_item.nom = cible_item._generer_nom()
        message = tr('api_orb_poly_result', lang, old_slot=ancien_slot, new_slot=nouveau_slot, nom=cible_item.nom)
        if random.random() * 100 < ORBE_TYPES["polymorphie"]["corruption_chance"]:
            cible_item.corrompu = True
            message += " " + tr('api_orb_corrupted', lang)

    elif orbe_type == "purification":
        if not cible_item.corrompu:
            return jsonify({"success": False, "message": tr('api_not_corrupted', lang)})
        cible_item.corrompu = False
        message = tr('api_orb_purify_result', lang, nom=cible_item.nom)

    orbe_item.quantite -= 1
    if orbe_item.quantite <= 0:
        p.inventaire[orbe_coffre].pop(orbe_idx)
    return jsonify({"success": True, "message": message})


@app.route("/api/sauvegarder", methods=["POST"])
def api_sauvegarder():
    p, e = get_or_init_game()
    lang = getattr(p, 'lang', 'fr')
    data = request.get_json() or {}
    filename = data.get("filename", "sauvegarde.json")
    confirm = data.get("confirm_overwrite", False)

    from game.save import save_exists
    if save_exists(filename) and not confirm:
        return jsonify({
            "success": False,
            "exists": True,
            "message": tr('api_save_exists', lang, file=filename),
        })

    sauvegarder(p, e, filename)
    return jsonify({"success": True, "message": tr('api_saved', lang, file=filename)})


@app.route("/api/charger", methods=["POST"])
def api_charger():
    global player, enemy
    data = request.get_json() or {}
    filename = data.get("filename", "sauvegarde.json")
    p, e = charger(filename)
    if p is None:
        return jsonify({"success": False, "message": tr('api_no_save_found', lang='fr')})
    player = p
    enemy = e
    lang = getattr(p, 'lang', 'fr')
    return jsonify({"success": True, "message": tr('api_loaded', lang, file=filename)})


@app.route("/api/sauvegardes")
def api_liste_sauvegardes():
    return jsonify({"fichiers": liste_sauvegardes()})


@app.route("/api/open_saves_folder", methods=["POST"])
def api_open_saves_folder():
    import subprocess
    from game.save import SAVE_DIR
    os.makedirs(SAVE_DIR, exist_ok=True)
    subprocess.Popen(["explorer", SAVE_DIR])
    return jsonify({"success": True})


@app.route("/api/new_game", methods=["POST"])
def api_new_game():
    global player, enemy, max_niveau_debloque, donjon_enemy
    from game.spells import spell_state
    import time
    player = Player()
    player.session_stats["debut_session"] = time.time()
    enemy = Enemy(niveau=1)
    max_niveau_debloque = 1
    donjon_enemy = None
    spell_state.reset()
    lang = getattr(player, 'lang', 'fr')
    return jsonify({"success": True, "message": tr('api_new_game', lang)})


# ─── DONJON ───────────────────────────────────────────────────────────────────

@app.route("/api/donjon/start", methods=["POST"])
def api_donjon_start():
    global donjon_enemy
    p, _ = get_or_init_game()
    lang = getattr(p, 'lang', 'fr')
    if p.donjon_actif is not None:
        return jsonify({"success": False, "message": tr('api_already_in_dungeon', lang)})

    data = request.get_json() or {}
    chapitre = data.get("chapitre", 1)

    from game.dungeon import generer_map, get_choix_disponibles, nodes_to_dict

    nodes = generer_map()
    hp_max = p.get_stats_effectives()["hp_max"]

    p.donjon_actif = {
        "chapitre": chapitre,
        "map": nodes_to_dict(nodes),
        "position": None,
        "etage": 0,
        "hp": hp_max,
        "hp_max": hp_max,
        "reliques": [],
        "ennemis_vaincus": 0,
        "combat_en_cours": False,
        "jetons_collectes": 0,
        "items_collectes": [],
        "action_en_attente": None,
        "premier_coup_utilise": False,
    }

    donjon_enemy = None

    choix = get_choix_disponibles(nodes, None, 0)
    choix_serialized = [{"col": c, "etage": e, "type": nodes[(c, e)].type} for c, e in choix]

    return jsonify({
        "success": True,
        "message": tr('api_dungeon_started', lang, chap=chapitre),
        "donjon": _build_donjon_state(p),
        "choix": choix_serialized,
    })


@app.route("/api/donjon/state")
def api_donjon_state():
    p, _ = get_or_init_game()
    lang = getattr(p, 'lang', 'fr')
    if p.donjon_actif is None:
        return jsonify({"success": False, "message": tr('api_no_dungeon', lang)})
    return jsonify({
        "success": True,
        "donjon": _build_donjon_state(p),
    })


@app.route("/api/donjon/select_node", methods=["POST"])
def api_donjon_select_node():
    global donjon_enemy
    p, _ = get_or_init_game()
    lang = getattr(p, 'lang', 'fr')
    if p.donjon_actif is None:
        return jsonify({"success": False, "message": tr('api_no_dungeon', lang)})

    data = request.get_json()
    col = data.get("col")
    etage = data.get("etage")

    from game.dungeon import nodes_from_dict, get_choix_disponibles, generer_ennemi_donjon, generer_boss_donjon, generer_evenement, nodes_to_dict
    from game.relics import tirage_reliques
    from config import DONJON_RELICS

    dj = p.donjon_actif
    nodes = nodes_from_dict(dj["map"])
    position = tuple(dj["position"]) if dj["position"] else None

    choix = get_choix_disponibles(nodes, position, dj["etage"])
    if (col, etage) not in choix:
        return jsonify({"success": False, "message": tr('api_node_inaccessible', lang)})

    node = nodes[(col, etage)]
    node.visite = True
    dj["position"] = [col, etage]
    dj["etage"] = etage
    dj["map"] = nodes_to_dict(nodes)
    dj["combat_en_cours"] = False
    dj["action_en_attente"] = None

    resultat = {"type": node.type}
    donjon_enemy = None

    if node.type == "combat":
        donjon_enemy = generer_ennemi_donjon(dj["chapitre"])
        dj["combat_en_cours"] = True
        resultat["ennemi"] = donjon_enemy.to_dict()
        resultat["message"] = tr('dj_combat_start', lang, nom=donjon_enemy.nom, niv=donjon_enemy.niveau)

    elif node.type == "boss":
        donjon_enemy = generer_boss_donjon(dj["chapitre"])
        dj["combat_en_cours"] = True
        resultat["ennemi"] = donjon_enemy.to_dict()
        resultat["message"] = tr('dj_boss_intro', lang, nom=donjon_enemy.nom)

    elif node.type == "camp":
        from game.relics import appliquer_reliques_player_stats
        saved_stats = dict(p.stats)
        appliquer_reliques_player_stats(p, dj["reliques"])
        hp_max_reliques = p.get_stats_effectives()["hp_max"]
        p.stats = saved_stats
        dj["hp"] = hp_max_reliques
        dj["hp_max"] = hp_max_reliques
        resultat["message"] = tr('dj_camp_rest', lang)

    elif node.type == "evenement":
        evt = generer_evenement(dj["chapitre"], lang)
        resultat["evenement"] = evt

        if evt["type"] == "objet":
            from game.models import Item as ItemCls
            item = ItemCls.from_dict(evt["item"])
            p.ajouter_item(item)
            dj["items_collectes"].append(item.to_dict())

        elif evt["type"] == "relique":
            if "relique" in evt:
                resultat["choix_reliques"] = [evt["relique"]]
                dj["action_en_attente"] = {"type": "choix_relique_evenement", "relique": evt["relique"]}

        elif evt["type"] == "guérison":
            heal = int(dj["hp_max"] * evt["heal_pct"] / 100)
            dj["hp"] = min(dj["hp"] + heal, dj["hp_max"])

        elif evt["type"] == "teleport":
            import random
            valid_nodes = [(c, e) for (c, e), n in nodes.items()
                          if e > dj["etage"] and e < 19 and not n.visite]
            if valid_nodes:
                target = random.choice(valid_nodes)
                dj["position"] = [target[0], target[1]]
                dj["etage"] = target[1]
                nodes[target].visite = True
                resultat["teleport"] = {"col": target[0], "etage": target[1]}
                dj["map"] = nodes_to_dict(nodes)
                col, etage = target[0], target[1]

        elif evt["type"] == "or":
            p.or_ += evt["or"]

        elif evt["type"] == "malédiction":
            perte = int(dj["hp_max"] * evt["perte_pct"] / 100)
            dj["hp"] = max(1, dj["hp"] - perte)
            dj["hp_max"] = max(dj["hp"], dj["hp_max"] - perte)

        resultat["message"] = evt["message"]

    elif node.type == "relique":
        choices = tirage_reliques(nb=3, exclure=dj["reliques"])
        resultat["choix_reliques"] = [
            {"key": k, **DONJON_RELICS[k]} for k in choices
        ]
        dj["action_en_attente"] = {"type": "choix_relique", "choix": choices}
        resultat["message"] = tr('dj_choose_relic', lang)

    choix_next = get_choix_disponibles(nodes, (col, etage), dj["etage"])
    choix_next_serialized = [
        {"col": c, "etage": e, "type": nodes[(c, e)].type}
        for c, e in choix_next
    ]
    resultat["choix_next"] = choix_next_serialized

    return jsonify({
        "success": True,
        "donjon": _build_donjon_state(p),
        "resultat": resultat,
    })


@app.route("/api/donjon/combat_tick", methods=["POST"])
def api_donjon_combat_tick():
    global donjon_enemy
    p, _ = get_or_init_game()
    lang = getattr(p, 'lang', 'fr')
    if p.donjon_actif is None or not p.donjon_actif.get("combat_en_cours"):
        return jsonify({"success": False, "message": tr('api_no_combat', lang)})
    if donjon_enemy is None:
        return jsonify({"success": False, "message": tr('api_no_enemy', lang)})

    dj = p.donjon_actif
    saved_hp = p.hp
    saved_stats = dict(p.stats)
    p.hp = dj["hp"]

    from game.relics import appliquer_reliques_stats, appliquer_reliques_player_stats, get_relique_modifiers, get_vitesse_bonus

    hp_pct = (p.hp / dj["hp_max"] * 100) if dj["hp_max"] > 0 else 100
    is_first = not dj.get("premier_coup_utilise", False)

    appliquer_reliques_player_stats(p, dj["reliques"], hp_pct=hp_pct)

    mods = get_relique_modifiers(dj["reliques"], hp_pct=hp_pct, is_first_attack=is_first)
    if mods["atk_mult"] != 1.0:
        p.stats["atk"] = int(p.stats["atk"] * mods["atk_mult"])
    if mods["crit_bonus"] > 0:
        p.stats["crit_chance"] += mods["crit_bonus"]
    if mods["crit_mult_bonus"] > 0:
        p.stats["crit_mult"] += mods["crit_mult_bonus"]
    if mods["premier_coup_mult"] > 1.0 and is_first:
        p.stats["atk"] = int(p.stats["atk"] * mods["premier_coup_mult"])
        dj["premier_coup_utilise"] = True

    _, stats_e_mod = appliquer_reliques_stats(
        p.get_stats_effectives(), donjon_enemy.stats, dj["reliques"]
    )
    vit_bonus = get_vitesse_bonus(dj["reliques"], hp_pct)
    donjon_enemy.stats = stats_e_mod

    enemy_hp_before = donjon_enemy.hp

    from game.combat import tick_player_attack
    resultat = tick_player_attack(p, donjon_enemy)

    degats_infliges = max(0, enemy_hp_before - donjon_enemy.hp)
    if mods["vol_de_vie_bonus"] > 0 and degats_infliges > 0:
        heal = int(degats_infliges * mods["vol_de_vie_bonus"] / 100)
        if heal > 0:
            stats_eff = p.get_stats_effectives()
            p.hp = min(p.hp + heal, stats_eff["hp_max"])
            resultat["log"].append(tr('dj_lifesteal_log', lang, heal=heal))

    p.stats = saved_stats
    dj["hp"] = p.hp
    p.hp = saved_hp

    if resultat["resultat"] == "victoire":
        dj["combat_en_cours"] = False
        dj["ennemis_vaincus"] += 1
        dj["premier_coup_utilise"] = False
        donjon_enemy = None

        from game.relics import get_post_combat_regen
        regen = get_post_combat_regen(dj["reliques"], dj["hp_max"])
        if regen > 0:
            dj["hp"] = min(dj["hp"] + regen, dj["hp_max"])
            resultat["regen_relique"] = regen

        if resultat.get("recompenses"):
            recomp = resultat["recompenses"]
            if "xp" in recomp:
                p.ajouter_xp(recomp["xp"])
            if "or" in recomp:
                p.or_ += recomp["or"]

        from game.dungeon import nodes_from_dict, get_choix_disponibles, nodes_to_dict
        nodes = nodes_from_dict(dj["map"])
        pos = tuple(dj["position"])
        choix_next = get_choix_disponibles(nodes, pos, dj["etage"])
        resultat["choix_next"] = [
            {"col": c, "etage": e, "type": nodes[(c, e)].type}
            for c, e in choix_next
        ]

    elif resultat["resultat"] == "defaite":
        dj["combat_en_cours"] = False
        donjon_enemy = None
        _terminer_donjon(p, victoire=False)
        resultat["donjon_termine"] = True
        resultat["message_defaite"] = tr('dj_died', lang)

    resultat["donjon"] = _build_donjon_state(p)
    return jsonify(resultat)


@app.route("/api/donjon/enemy_tick", methods=["POST"])
def api_donjon_enemy_tick():
    global donjon_enemy
    p, _ = get_or_init_game()
    lang = getattr(p, 'lang', 'fr')
    if p.donjon_actif is None or not p.donjon_actif.get("combat_en_cours"):
        return jsonify({"success": False, "message": tr('api_no_combat', lang)})
    if donjon_enemy is None:
        return jsonify({"success": False, "message": tr('api_no_enemy', lang)})

    dj = p.donjon_actif
    saved_hp = p.hp
    saved_stats = dict(p.stats)
    p.hp = dj["hp"]
    hp_before_tick = p.hp
    enemy_hp_before = donjon_enemy.hp

    from game.relics import appliquer_reliques_stats, appliquer_reliques_player_stats, get_vitesse_bonus, get_relique_modifiers

    hp_pct = (p.hp / dj["hp_max"] * 100) if dj["hp_max"] > 0 else 100
    mods = get_relique_modifiers(dj["reliques"], hp_pct=hp_pct)

    appliquer_reliques_player_stats(p, dj["reliques"], hp_pct=hp_pct)

    _, stats_e_mod = appliquer_reliques_stats(
        p.get_stats_effectives(), donjon_enemy.stats, dj["reliques"]
    )
    vit_bonus = get_vitesse_bonus(dj["reliques"], hp_pct)
    donjon_enemy.stats = stats_e_mod

    from game.combat import tick_enemy_attack
    resultat = tick_enemy_attack(p, donjon_enemy)

    degats_recus = max(0, hp_before_tick - p.hp)
    if mods["reduction_degats"] > 0 and degats_recus > 0:
        degats_recus = max(0, degats_recus - mods["reduction_degats"])
        p.hp = hp_before_tick - degats_recus

    if mods["epines_pct"] > 0 and degats_recus > 0 and donjon_enemy.hp > 0:
        reflet = int(degats_recus * mods["epines_pct"] / 100)
        if reflet > 0:
            donjon_enemy.hp -= reflet
            resultat["log"].append(tr('dj_thorns_log', lang, dmg=reflet))

    if mods["vol_de_vie_bonus"] > 0:
        degats_ennemi = max(0, enemy_hp_before - donjon_enemy.hp)
        if degats_ennemi > 0:
            heal = int(degats_ennemi * mods["vol_de_vie_bonus"] / 100)
            if heal > 0:
                stats_eff = p.get_stats_effectives()
                p.hp = min(p.hp + heal, stats_eff["hp_max"])
                resultat["log"].append(tr('dj_lifesteal_log', lang, heal=heal))

    p.stats = saved_stats
    dj["hp"] = p.hp
    p.hp = saved_hp

    if resultat["resultat"] == "victoire":
        dj["combat_en_cours"] = False
        dj["ennemis_vaincus"] += 1
        dj["premier_coup_utilise"] = False
        donjon_enemy = None

        from game.relics import get_post_combat_regen
        regen = get_post_combat_regen(dj["reliques"], dj["hp_max"])
        if regen > 0:
            dj["hp"] = min(dj["hp"] + regen, dj["hp_max"])

        if resultat.get("recompenses"):
            recomp = resultat["recompenses"]
            if "xp" in recomp:
                p.ajouter_xp(recomp["xp"])
            if "or" in recomp:
                p.or_ += recomp["or"]

        from game.dungeon import nodes_from_dict, get_choix_disponibles
        nodes = nodes_from_dict(dj["map"])
        pos = tuple(dj["position"])
        choix_next = get_choix_disponibles(nodes, pos, dj["etage"])
        resultat["choix_next"] = [
            {"col": c, "etage": e, "type": nodes[(c, e)].type}
            for c, e in choix_next
        ]

    elif resultat["resultat"] == "defaite":
        dj["combat_en_cours"] = False
        donjon_enemy = None
        _terminer_donjon(p, victoire=False)
        resultat["donjon_termine"] = True
        resultat["message_defaite"] = tr('dj_died', lang)

    resultat["donjon"] = _build_donjon_state(p)
    return jsonify(resultat)


@app.route("/api/donjon/action", methods=["POST"])
def api_donjon_action():
    p, _ = get_or_init_game()
    lang = getattr(p, 'lang', 'fr')
    if p.donjon_actif is None:
        return jsonify({"success": False, "message": tr('api_no_dungeon', lang)})

    data = request.get_json()
    action = data.get("action")
    dj = p.donjon_actif

    from config import DONJON_RELICS, DONJON_XP_BOSS, DONJON_JETONS_MIN, DONJON_JETONS_MAX, DONJON_ITEMS_RECOMPENSE
    import random

    if action == "choisir_relique":
        if not dj.get("action_en_attente"):
            return jsonify({"success": False, "message": tr('api_no_pending_action', lang)})

        rel_key = data.get("relique")
        attente = dj["action_en_attente"]

        if attente["type"] == "choix_relique" and rel_key not in attente.get("choix", []):
            return jsonify({"success": False, "message": tr('api_invalid_relic', lang)})

        if rel_key in DONJON_RELICS:
            dj["reliques"].append(rel_key)
            rel = DONJON_RELICS[rel_key]
            dj["action_en_attente"] = None
            return jsonify({
                "success": True,
                "message": tr('api_relic_acquired', lang, nom=rel['nom'], desc=rel['description']),
                "donjon": _build_donjon_state(p),
            })
        return jsonify({"success": False, "message": tr('api_unknown_relic', lang)})

    elif action == "boss_vaincu":
        if dj["etage"] != 19:
            return jsonify({"success": False, "message": tr('api_boss_not_defeated', lang)})

        chapitre = dj["chapitre"]
        deja_fait = chapitre in p.chapitres_completees

        from game.models import Item
        items_gagnes = []
        for _ in range(DONJON_ITEMS_RECOMPENSE):
            item = Item(niveau=DONJON_ITEMS_RECOMPENSE * chapitre)
            p.ajouter_item(item)
            items_gagnes.append(item.to_dict())

        _terminer_donjon(p, victoire=True)

        jetons = random.randint(DONJON_JETONS_MIN, DONJON_JETONS_MAX)
        p.jetons += jetons

        if deja_fait:
            return jsonify({
                "success": True,
                "reincarnation": False,
                "message": tr('dj_chapter_already_done', lang, chap=chapitre, jetons=jetons, items=len(items_gagnes)),
                "jetons": jetons,
                "items": items_gagnes,
                "boss_battus_total": p.boss_donjon_battus,
                "pts_par_niveau": 2 + p.boss_donjon_battus,
            })

        from config import STATS_BASE
        p.boss_donjon_battus += 1
        p.chapitres_completees.append(chapitre)

        p.niveau = 1
        p.xp = 0
        p.xp_max = p._calculer_xp_max()
        p.points_stats = 0
        p.stats = dict(STATS_BASE)
        p.hp = p.get_stats_effectives()["hp_max"]

        pts_par_niveau = 2 + p.boss_donjon_battus

        return jsonify({
            "success": True,
            "reincarnation": True,
            "message": tr('dj_reincarnation_msg', lang, pts=pts_par_niveau, jetons=jetons, items=len(items_gagnes)),
            "jetons": jetons,
            "items": items_gagnes,
            "boss_battus_total": p.boss_donjon_battus,
            "pts_par_niveau": pts_par_niveau,
        })

    return jsonify({"success": False, "message": tr('dj_unknown_action', lang)})


@app.route("/api/donjon/exit", methods=["POST"])
def api_donjon_exit():
    p, _ = get_or_init_game()
    lang = getattr(p, 'lang', 'fr')
    if p.donjon_actif is None:
        return jsonify({"success": False, "message": tr('api_no_dungeon', lang)})

    _terminer_donjon(p, victoire=False)
    return jsonify({
        "success": True,
        "message": tr('dj_exit_message', lang),
    })


def _build_donjon_state(p):
    if p.donjon_actif is None:
        return None
    dj = p.donjon_actif
    from config import DONJON_RELICS
    reliques_info = []
    for r in dj.get("reliques", []):
        if r in DONJON_RELICS:
            reliques_info.append({"key": r, **DONJON_RELICS[r]})

    ennemi_info = None
    if dj.get("combat_en_cours") and donjon_enemy is not None:
        ennemi_info = {
            "nom": donjon_enemy.nom,
            "niveau": donjon_enemy.niveau,
            "boss": donjon_enemy.boss,
            "stats": donjon_enemy.stats,
            "hp": donjon_enemy.hp,
            "hp_max": donjon_enemy.stats["hp_max"],
        }

    return {
        "chapitre": dj["chapitre"],
        "map": dj["map"],
        "position": dj["position"],
        "etage": dj["etage"],
        "hp": dj["hp"],
        "hp_max": dj["hp_max"],
        "reliques": reliques_info,
        "combat_en_cours": dj["combat_en_cours"],
        "ennemi": ennemi_info,
        "ennemis_vaincus": dj["ennemis_vaincus"],
        "jetons_collectes": dj["jetons_collectes"],
        "action_en_attente": dj.get("action_en_attente"),
    }


def _terminer_donjon(p, victoire):
    global donjon_enemy
    donjon_enemy = None
    p.donjon_actif = None


# ─── MACHINE À SOUS ──────────────────────────────────────────────────────────

@app.route("/api/slot_machine/spin", methods=["POST"])
def api_slot_machine_spin():
    import random
    from config import SLOT_MACHINE_COUT, SLOT_MACHINE_SYMBOLES
    p, _ = get_or_init_game()

    if p.jetons < SLOT_MACHINE_COUT:
        return jsonify({"success": False, "message": "Pas assez de jetons !"})

    p.jetons -= SLOT_MACHINE_COUT

    resultats = []
    for _ in range(3):
        total_poids = sum(s["poids"] for s in SLOT_MACHINE_SYMBOLES)
        r = random.uniform(0, total_poids)
        cumul = 0
        for s in SLOT_MACHINE_SYMBOLES:
            cumul += s["poids"]
            if r <= cumul:
                resultats.append(s)
                break

    r1, r2, r3 = resultats

    if r1["id"] == r2["id"] == r3["id"]:
        gain_type = "triple"
    elif r1["id"] == r2["id"]:
        gain_type = "double_gauche"
    else:
        gain_type = None

    if gain_type:
        from config import SLOT_MACHINE_GAINS
        gain = SLOT_MACHINE_GAINS[gain_type]
        return jsonify({
            "success": True,
            "resultats": [{"id": r["id"], "icone": r["icone"]} for r in resultats],
            "gain": gain_type,
            "rarete": gain["rarete"],
            "message": gain["message"],
            "jetons": p.jetons,
            "choix_slot": True,
        })
    else:
        return jsonify({
            "success": True,
            "resultats": [{"id": r["id"], "icone": r["icone"]} for r in resultats],
            "gain": None,
            "message": "Perdu... Retente ta chance !",
            "jetons": p.jetons,
            "choix_slot": False,
        })


@app.route("/api/slot_machine/claim", methods=["POST"])
def api_slot_machine_claim():
    from config import SLOT_MACHINE_GAINS, SLOT_MACHINE_SLOTS_CHOIX
    p, _ = get_or_init_game()
    data = request.get_json()
    gain_type = data.get("gain_type")
    slot_choisi = data.get("slot")

    if gain_type not in SLOT_MACHINE_GAINS:
        return jsonify({"success": False, "message": "Gain invalide."})
    if slot_choisi not in SLOT_MACHINE_SLOTS_CHOIX:
        return jsonify({"success": False, "message": "Slot invalide."})

    gain = SLOT_MACHINE_GAINS[gain_type]
    item = Item(slot=slot_choisi, rarete=gain["rarete"], niveau=p.niveau)
    p.ajouter_item(item)

    return jsonify({
        "success": True,
        "message": f"{item.nom} ajoute a l'inventaire !",
        "item": item.to_dict(),
        "jetons": p.jetons,
    })


# ─── CHAUDRON MAGIQUE ────────────────────────────────────────────────────────

@app.route("/api/chaudron/fondre", methods=["POST"])
def api_chaudron_fondre():
    p, _ = get_or_init_game()
    lang = getattr(p, 'lang', 'fr')
    data = request.get_json()
    items_input = data.get("items", [])

    from config import CHAUDRON_ITEMS_REQUIS, CHAUDRON_COUT_OR, CHAUDRON_COUT_PAR_RARETE

    if len(items_input) != CHAUDRON_ITEMS_REQUIS:
        return jsonify({"success": False, "message": tr('api_cauldron_need_3', lang)})

    items_to_remove = []
    total_cout = CHAUDRON_COUT_OR
    from config import RARITES
    input_raretes = []
    for entry in items_input:
        c = entry.get("coffre_idx", 0)
        i = entry.get("item_idx", 0)
        if c >= len(p.inventaire):
            return jsonify({"success": False, "message": tr('api_chest_invalid', lang)})
        if i >= len(p.inventaire[c]):
            return jsonify({"success": False, "message": tr('api_item_invalid', lang)})
        item = p.inventaire[c][i]
        if item.locked:
            return jsonify({"success": False, "message": tr('api_cauldron_locked', lang, nom=item.nom)})
        if item.slot in ("orbe", "artefact"):
            return jsonify({"success": False, "message": tr('api_cauldron_no_orbs', lang)})
        if getattr(item, 'vivant', False):
            return jsonify({"success": False, "message": tr('api_cauldron_no_vivant', lang, nom=item.nom)})
        total_cout += CHAUDRON_COUT_PAR_RARETE.get(item.rarete, 0)
        input_raretes.append(item.rarete)
        items_to_remove.append((c, i))

    if p.or_ < total_cout:
        return jsonify({"success": False, "message": tr('api_not_enough_gold', lang, cout=total_cout)})

    p.or_ -= total_cout

    items_to_remove.sort(key=lambda x: x[1], reverse=True)
    items_to_remove.sort(key=lambda x: x[0], reverse=True)
    for c, i in items_to_remove:
        p.inventaire[c].pop(i)

    _consolider_inventaire(p)

    import random as _r
    avg_idx = sum(RARITES.index(r) for r in input_raretes) / len(input_raretes)
    base = round(avg_idx)
    offsets = [-1, 0, 1, 2, 3]
    weights = [3, 27, 40, 20, 10]
    valid_offsets = []
    valid_weights = []
    for off, w in zip(offsets, weights):
        target = base + off
        if 0 <= target < len(RARITES):
            valid_offsets.append(off)
            valid_weights.append(w)
    total_w = sum(valid_weights)
    roll = _r.uniform(0, total_w)
    cumul = 0
    rarete_chaudron = RARITES[base]
    for off, w in zip(valid_offsets, valid_weights):
        cumul += w
        if roll <= cumul:
            rarete_chaudron = RARITES[base + off]
            break

    new_item = Item(niveau=p.niveau, rarete=rarete_chaudron)
    p.ajouter_item(new_item)

    return jsonify({
        "success": True,
        "message": tr('api_cauldron_result', lang, nom=new_item.nom, rar=new_item.rarete),
        "cout": total_cout,
        "item": new_item.to_dict(),
    })


# ─── STATISTIQUES DE SESSION ─────────────────────────────────────────────────

@app.route("/api/session_stats")
def api_session_stats():
    import time
    p, _ = get_or_init_game()
    ss = p.session_stats
    debut = ss.get("debut_session") or time.time()
    duree = time.time() - debut
    duree_min = max(duree / 60, 0.01)

    dps = round(ss["degats_infliges"] / max(duree, 1), 1)
    kills_min = round(ss["kills"] / duree_min, 1)
    degats_moyen = round(ss["degats_infliges"] / max(ss["coups_donnes"], 1), 1)
    temps_kill_moyen = round(duree / max(ss["kills"], 1), 1)

    heures = int(duree // 3600)
    minutes = int((duree % 3600) // 60)
    secondes = int(duree % 60)
    temps_str = f"{heures}h{minutes:02d}m{secondes:02d}s" if heures > 0 else f"{minutes}m{secondes:02d}s"

    return jsonify({
        "temps_jeu": temps_str,
        "duree_secondes": round(duree),
        "combat": {
            "kills": ss["kills"],
            "dps": dps,
            "kills_par_min": kills_min,
            "degats_moyen": degats_moyen,
            "temps_kill_moyen": temps_kill_moyen,
        },
        "loot": {
            "par_rarete": ss["loots_par_rarete"],
            "or_gagne": ss["or_gagne"],
            "orbes_obtenues": ss["orbes_obtenues"],
            "meilleur_loot": ss["meilleur_loot"],
        },
        "progression": {
            "xp_gagnee": ss["xp_gagnee"],
            "niveaux_montes": ss["niveaux_montes"],
        },
        "records": {
            "record_kills_sans_mourir": ss["record_kills_sans_mourir"],
            "plus_haut_ennemi": ss["plus_haut_ennemi"],
            "plus_gros_coup": ss["plus_gros_coup"],
            "morts": ss["mort"],
        },
    })


# ─── AUTO-SUPPRESSION ────────────────────────────────────────────────────────

@app.route("/api/auto_supprimer", methods=["POST"])
def api_auto_supprimer():
    p, _ = get_or_init_game()
    data = request.get_json()
    raretes = data.get("raretes", [])
    from config import RARITES
    valides = [r for r in raretes if r in RARITES]
    p.auto_supprimer = valides
    return jsonify({
        "success": True,
        "auto_supprimer": p.auto_supprimer,
    })


@app.route("/api/set_language", methods=["POST"])
def api_set_language():
    p, _ = get_or_init_game()
    data = request.get_json() or {}
    lang = data.get("lang", "fr")
    if lang not in ("fr", "en"):
        lang = "fr"
    p.lang = lang
    return jsonify({"success": True, "lang": lang})


@app.route("/api/translations")
def api_translations():
    from game.translations import TRANSLATIONS
    p, _ = get_or_init_game()
    lang = p.lang
    result = {}
    for key, val in TRANSLATIONS.items():
        result[key] = val.get(lang, val.get("fr", key))
    return jsonify(result)


@app.route("/api/toggle_force_boss", methods=["POST"])
def api_toggle_force_boss():
    global enemy
    p, e = get_or_init_game()
    lang = getattr(p, 'lang', 'fr')
    reincarnations = len(p.chapitres_completees)
    if reincarnations < 5:
        return jsonify({"success": False, "message": tr('api_force_boss_need_reinc', lang, n=reincarnations), "force_boss": p.force_boss})
    p.force_boss = not p.force_boss
    if p.force_boss:
        enemy = _spawn_enemy(e.niveau, p)
        p.hp = p.get_stats_effectives()["hp_max"]
    return jsonify({
        "success": True,
        "force_boss": p.force_boss,
        "message": tr('api_force_boss_active', lang) if p.force_boss else tr('api_force_boss_off', lang),
    })


# ─── PRO-TIPS ────────────────────────────────────────────────────────────────

@app.route("/api/pro_tip")
def api_pro_tip():
    import random
    from config import PRO_TIPS
    return jsonify({"tip": random.choice(PRO_TIPS)})


if __name__ == "__main__":
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        threading.Timer(1.0, lambda: webbrowser.open("http://127.0.0.1:5000")).start()
    app.run(debug=True, port=5000, use_reloader=True)
