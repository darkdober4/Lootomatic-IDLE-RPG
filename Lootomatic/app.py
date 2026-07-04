import sys
import os
import webbrowser
import threading
sys.path.insert(0, os.path.dirname(__file__))

from flask import Flask, render_template, jsonify, request
from game.models import Player, Enemy, Item
from game.combat import tick_player_attack, tick_enemy_attack
from game.save import sauvegarder, charger, liste_sauvegardes

app = Flask(__name__)

player = None
enemy = None
max_niveau_debloque = 1
donjon_enemy = None


def get_or_init_game():
    global player, enemy, max_niveau_debloque
    if player is None:
        player = Player()
        enemy = Enemy(niveau=1)
        max_niveau_debloque = 1
        import time
        player.session_stats["debut_session"] = time.time()
    return player, enemy


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/state")
def api_state():
    p, e = get_or_init_game()
    from game.spells import get_active_spells
    from config import SORTS, RARITE_SORT_NIVEAU
    active_spells = get_active_spells(p)
    spell_info = None
    if active_spells:
        s = active_spells[0]
        spell_info = {
            "nom": s["data"]["nom"],
            "categorie": s["data"]["categorie"],
            "description": s["data"]["description"],
            "niveau": s["niveau"],
            "value": s["value"],
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
            if e.niveau >= max_niveau_debloque:
                max_niveau_debloque = e.niveau + 1
                enemy = Enemy(niveau=max_niveau_debloque)
            else:
                enemy = Enemy(niveau=e.niveau, boss=False)
        else:
            enemy = Enemy(niveau=e.niveau, boss=False)
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
            if e.niveau >= max_niveau_debloque:
                max_niveau_debloque = e.niveau + 1
                enemy = Enemy(niveau=max_niveau_debloque)
            else:
                enemy = Enemy(niveau=e.niveau, boss=False)
        else:
            enemy = Enemy(niveau=e.niveau, boss=False)
    return jsonify(resultat)


@app.route("/api/skip_enemy", methods=["POST"])
def api_skip_enemy():
    global enemy, max_niveau_debloque
    p, e = get_or_init_game()
    nouveau_niveau = e.niveau + 1
    if nouveau_niveau > max_niveau_debloque:
        max_niveau_debloque = nouveau_niveau
    enemy = Enemy(niveau=nouveau_niveau)
    p.hp = p.get_stats_effectives()["hp_max"]
    return jsonify({
        "success": True,
        "message": f"Passé à l'ennemi niveau {nouveau_niveau} : {enemy.nom}",
        "max_niveau": max_niveau_debloque,
    })


@app.route("/api/prev_enemy", methods=["POST"])
def api_prev_enemy():
    global enemy
    p, e = get_or_init_game()
    nouveau_niveau = max(1, e.niveau - 1)
    enemy = Enemy(niveau=nouveau_niveau, boss=False)
    p.hp = p.get_stats_effectives()["hp_max"]
    return jsonify({
        "success": True,
        "message": f"Retour à l'ennemi niveau {nouveau_niveau} : {enemy.nom}",
        "max_niveau": max_niveau_debloque,
    })


@app.route("/api/alloquer_stat", methods=["POST"])
def api_allouer_stat():
    p, _ = get_or_init_game()
    if p.donjon_actif is not None:
        return jsonify({"success": False, "message": "Impossible d'allouer des stats pendant un donjon."})
    data = request.get_json()
    stat = data.get("stat")
    ok = p.allouer_stat(stat)
    return jsonify({"success": ok, "points_restants": p.points_stats, "stats": p.stats})


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
    data = request.get_json()
    coffre_idx = data.get("coffre_idx", 0)
    item_idx = data.get("item_idx", 0)
    if coffre_idx >= len(p.inventaire):
        return jsonify({"success": False, "message": "Coffre invalide"})
    coffre = p.inventaire[coffre_idx]
    if item_idx >= len(coffre):
        return jsonify({"success": False, "message": "Objet invalide"})
    item = coffre.pop(item_idx)
    _consolider_inventaire(p)
    return jsonify({
        "success": True,
        "message": f"{item.nom} supprime",
        "or_gagne": 0,
    })


@app.route("/api/delete_batch", methods=["POST"])
def api_delete_batch():
    p, _ = get_or_init_game()
    data = request.get_json()
    rarete = data.get("rarete")
    count = 0
    for coffre in p.inventaire:
        items_a_garder = []
        for item in coffre:
            if rarete and item.rarete == rarete and item.slot not in ("orbe", "artefact"):
                count += 1
            else:
                items_a_garder.append(item)
        coffre.clear()
        coffre.extend(items_a_garder)
    _consolider_inventaire(p)
    return jsonify({
        "success": True,
        "message": f"{count} objet(s) {rarete} supprime(s)",
    })


@app.route("/api/utiliser_orbe", methods=["POST"])
def api_utiliser_orbe():
    p, _ = get_or_init_game()
    data = request.get_json()
    orbe_coffre = data.get("orbe_coffre_idx")
    orbe_idx = data.get("orbe_item_idx")
    cible_coffre = data.get("cible_coffre_idx")
    cible_idx = data.get("cible_item_idx")

    if orbe_coffre >= len(p.inventaire):
        return jsonify({"success": False, "message": "Coffre orbe invalide"})
    orbe_item = p.inventaire[orbe_coffre][orbe_idx]
    if not getattr(orbe_item, "orbe_type", None):
        return jsonify({"success": False, "message": "Ce n'est pas un orbe"})

    if cible_coffre >= len(p.inventaire):
        return jsonify({"success": False, "message": "Coffre cible invalide"})
    cible_item = p.inventaire[cible_coffre][cible_idx]
    if cible_item.slot == "orbe":
        return jsonify({"success": False, "message": "Impossible d'utiliser un orbe sur un autre orbe"})

    if cible_item.corrompu:
        return jsonify({"success": False, "message": "Cet objet est corrompu et ne peut plus être modifié"})

    from config import ORBE_TYPES, MODIFICATEURS, RARITES, RARITE_MULT
    import random

    message = ""
    orbe_type = orbe_item.orbe_type

    if orbe_type == "amelioration":
        if not cible_item.mods:
            return jsonify({"success": False, "message": "Cet objet n'a aucune stat à améliorer"})
        mod_choisi = random.choice(cible_item.mods)
        mod_choisi["valeur"] += 1
        message = f"✨ {cible_item.nom} : {mod_choisi['nom']} +1 (maintenant +{mod_choisi['valeur']})"
        if random.random() * 100 < 10:
            cible_item.corrompu = True
            message += " ⚠️ CORROMPU ! Cet objet ne peut plus être modifié."

    elif orbe_type == "alteration":
        mods_disponibles = [m for m in MODIFICATEURS if m["stat"] not in [mod["stat"] for mod in cible_item.mods]]
        if not mods_disponibles:
            return jsonify({"success": False, "message": "Cet objet a déjà tous les mods possibles"})

        mod_choisi = random.choice(mods_disponibles)
        mult = RARITE_MULT.get(cible_item.rarete, 1.0)
        val_min = max(1, int(mod_choisi["min"] * mult))
        val_max = max(val_min + 1, int(mod_choisi["max"] * mult))
        valeur = random.randint(val_min, val_max)
        cible_item.mods.append({"nom": mod_choisi["nom"], "stat": mod_choisi["stat"], "valeur": valeur})
        message = f"🔮 {cible_item.nom} : +{valeur} {mod_choisi['nom']} ajouté"

        if random.random() * 100 < ORBE_TYPES["alteration"]["rarete_up_chance"]:
            idx = RARITES.index(cible_item.rarete)
            if idx < len(RARITES) - 1:
                cible_item.rarete = RARITES[idx + 1]
                cible_item.nom = cible_item._generer_nom()
                message += f" → Rareté augmentée à {cible_item.rarete} !"
                if cible_item.rarete == "Mythique":
                    cible_item.corrompu = True
                    message += " ⚠️ Mythique atteint ! Objet automatiquement CORROMPU."

        if not cible_item.corrompu and random.random() * 100 < ORBE_TYPES["alteration"]["corruption_chance"]:
            cible_item.corrompu = True
            message += " ⚠️ CORROMPU ! Cet objet ne peut plus être modifié."

    orbe_item.quantite -= 1
    if orbe_item.quantite <= 0:
        p.inventaire[orbe_coffre].pop(orbe_idx)
    return jsonify({"success": True, "message": message})


@app.route("/api/sauvegarder", methods=["POST"])
def api_sauvegarder():
    p, e = get_or_init_game()
    data = request.get_json() or {}
    filename = data.get("filename", "sauvegarde.json")
    sauvegarder(p, e, filename)
    return jsonify({"success": True, "message": f"Sauvegardé : {filename}"})


@app.route("/api/charger", methods=["POST"])
def api_charger():
    global player, enemy
    data = request.get_json() or {}
    filename = data.get("filename", "sauvegarde.json")
    p, e = charger(filename)
    if p is None:
        return jsonify({"success": False, "message": "Aucune sauvegarde trouvée"})
    player = p
    enemy = e
    return jsonify({"success": True, "message": f"Chargé : {filename}"})


@app.route("/api/sauvegardes")
def api_liste_sauvegardes():
    return jsonify({"fichiers": liste_sauvegardes()})


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
    return jsonify({"success": True, "message": "Nouvelle partie commencee !"})


# ─── DONJON ───────────────────────────────────────────────────────────────────

@app.route("/api/donjon/start", methods=["POST"])
def api_donjon_start():
    global donjon_enemy
    p, _ = get_or_init_game()
    if p.donjon_actif is not None:
        return jsonify({"success": False, "message": "Vous êtes déjà dans un donjon."})

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
        "message": f"Donjon Chapitre {chapitre} commencé !",
        "donjon": _build_donjon_state(p),
        "choix": choix_serialized,
    })


@app.route("/api/donjon/state")
def api_donjon_state():
    p, _ = get_or_init_game()
    if p.donjon_actif is None:
        return jsonify({"success": False, "message": "Aucun donjon en cours."})
    return jsonify({
        "success": True,
        "donjon": _build_donjon_state(p),
    })


@app.route("/api/donjon/select_node", methods=["POST"])
def api_donjon_select_node():
    global donjon_enemy
    p, _ = get_or_init_game()
    if p.donjon_actif is None:
        return jsonify({"success": False, "message": "Aucun donjon en cours."})

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
        return jsonify({"success": False, "message": "Ce node n'est pas accessible."})

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
        resultat["message"] = f"Combat contre {donjon_enemy.nom} (Niv.{donjon_enemy.niveau}) !"

    elif node.type == "boss":
        donjon_enemy = generer_boss_donjon(dj["chapitre"])
        dj["combat_en_cours"] = True
        resultat["ennemi"] = donjon_enemy.to_dict()
        resultat["message"] = f"BOSS : {donjon_enemy.nom} ! Préparez-vous !"

    elif node.type == "camp":
        from game.relics import appliquer_reliques_player_stats
        saved_stats = dict(p.stats)
        appliquer_reliques_player_stats(p, dj["reliques"])
        hp_max_reliques = p.get_stats_effectives()["hp_max"]
        p.stats = saved_stats
        dj["hp"] = hp_max_reliques
        dj["hp_max"] = hp_max_reliques
        resultat["message"] = "Vous vous reposez au camp. PV entièrement restaurés !"

    elif node.type == "evenement":
        evt = generer_evenement(dj["chapitre"])
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
        resultat["message"] = "Choisissez une relique !"

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
    if p.donjon_actif is None or not p.donjon_actif.get("combat_en_cours"):
        return jsonify({"success": False, "message": "Pas de combat en cours."})
    if donjon_enemy is None:
        return jsonify({"success": False, "message": "Pas d'ennemi."})

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
            resultat["log"].append(f"🩸 Vol de Vie (relique) : +{heal} HP")

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
        resultat["message_defaite"] = "Vous êtes mort dans le donjon. Tout est perdu."

    resultat["donjon"] = _build_donjon_state(p)
    return jsonify(resultat)


@app.route("/api/donjon/enemy_tick", methods=["POST"])
def api_donjon_enemy_tick():
    global donjon_enemy
    p, _ = get_or_init_game()
    if p.donjon_actif is None or not p.donjon_actif.get("combat_en_cours"):
        return jsonify({"success": False, "message": "Pas de combat en cours."})
    if donjon_enemy is None:
        return jsonify({"success": False, "message": "Pas d'ennemi."})

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
            resultat["log"].append(f"🌿 Épines (relique) : {reflet} dégâts renvoyés")

    if mods["vol_de_vie_bonus"] > 0:
        degats_ennemi = max(0, enemy_hp_before - donjon_enemy.hp)
        if degats_ennemi > 0:
            heal = int(degats_ennemi * mods["vol_de_vie_bonus"] / 100)
            if heal > 0:
                stats_eff = p.get_stats_effectives()
                p.hp = min(p.hp + heal, stats_eff["hp_max"])
                resultat["log"].append(f"🩸 Vol de Vie (relique) : +{heal} HP")

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
        resultat["message_defaite"] = "Vous êtes mort dans le donjon. Tout est perdu."

    resultat["donjon"] = _build_donjon_state(p)
    return jsonify(resultat)


@app.route("/api/donjon/action", methods=["POST"])
def api_donjon_action():
    p, _ = get_or_init_game()
    if p.donjon_actif is None:
        return jsonify({"success": False, "message": "Aucun donjon en cours."})

    data = request.get_json()
    action = data.get("action")
    dj = p.donjon_actif

    from config import DONJON_RELICS, DONJON_XP_BOSS, DONJON_JETONS_MIN, DONJON_JETONS_MAX, DONJON_ITEMS_RECOMPENSE
    import random

    if action == "choisir_relique":
        if not dj.get("action_en_attente"):
            return jsonify({"success": False, "message": "Aucune action en attente."})

        rel_key = data.get("relique")
        attente = dj["action_en_attente"]

        if attente["type"] == "choix_relique" and rel_key not in attente.get("choix", []):
            return jsonify({"success": False, "message": "Relique non valide."})

        if rel_key in DONJON_RELICS:
            dj["reliques"].append(rel_key)
            rel = DONJON_RELICS[rel_key]
            dj["action_en_attente"] = None
            return jsonify({
                "success": True,
                "message": f"Relique acquise : {rel['nom']} — {rel['description']}",
                "donjon": _build_donjon_state(p),
            })
        return jsonify({"success": False, "message": "Relique inconnue."})

    elif action == "boss_vaincu":
        if dj["etage"] != 19:
            return jsonify({"success": False, "message": "Le boss n'a pas été vaincu."})

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
                "message": f"Chapitre {chapitre} déjà complété. +{jetons} jetons, +{len(items_gagnes)} objets.",
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
            "message": f"RÉINCARNATION ! Niv.1 — {pts_par_niveau} pts/niveau désormais. +{jetons} jetons, {len(items_gagnes)} objets !",
            "jetons": jetons,
            "items": items_gagnes,
            "boss_battus_total": p.boss_donjon_battus,
            "pts_par_niveau": pts_par_niveau,
        })

    return jsonify({"success": False, "message": "Action inconnue."})


@app.route("/api/donjon/exit", methods=["POST"])
def api_donjon_exit():
    p, _ = get_or_init_game()
    if p.donjon_actif is None:
        return jsonify({"success": False, "message": "Aucun donjon en cours."})

    _terminer_donjon(p, victoire=False)
    return jsonify({
        "success": True,
        "message": "Vous avez quitté le donjon. Les récompenses non obtenues sont perdues.",
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
