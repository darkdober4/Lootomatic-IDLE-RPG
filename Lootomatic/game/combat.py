import random
from game.models import Player, Enemy, Item
from game.spells import (
    spell_state, process_spells_before_player_attack,
    get_player_attack_multiplier, get_hate_speed_bonus,
    process_spells_on_player_hit, is_enemy_frozen,
    get_passive_modifiers, process_lifesteal, process_execution,
    get_active_spells, accumulate_stacks_on_hit,
)


def calculer_degats(atk, def_adversaire):
    reduction = def_adversaire / (def_adversaire + 100)
    degats = max(1, int(atk * (1 - reduction)))
    return degats


def tick_player_attack(player: Player, enemy: Enemy):
    log = []
    stats_j = player.get_stats_effectives()
    stats_e = enemy.stats

    process_spells_before_player_attack(player, enemy, log)

    mods = get_passive_modifiers(player)
    atq_j = int(stats_j["atk"] * mods["atk_mult"])
    def_j = int(stats_j["def"] * mods["def_mult"])

    if enemy.hp > 0 and player.hp > 0:
        process_execution(player, enemy, log)

    if enemy.hp > 0 and player.hp > 0:
        if random.random() * 100 < stats_e["esquive"]:
            log.append(f"⚡ {enemy.nom} esquive votre attaque !")
        else:
            mult = get_player_attack_multiplier()
            degats = int(calculer_degats(atq_j, stats_e["def"]) * mult)
            if random.random() * 100 < stats_j["crit_chance"]:
                degats = int(degats * stats_j["crit_mult"] / 100)
                log.append(f"CRITIQUE ! Vous infligez {degats} degats a {enemy.nom}")
            else:
                log.append(f"Vous infligez {degats} degats a {enemy.nom}")
            enemy.hp -= degats
            for sort in get_active_spells(player):
                accumulate_stacks_on_hit(sort["key"], sort, player, enemy, log)
            ss = player.session_stats
            ss["degats_infliges"] += degats
            ss["coups_donnes"] += 1
            if degats > ss["plus_gros_coup"]:
                ss["plus_gros_coup"] = degats
            process_lifesteal(player, degats, log)
            if random.random() * 100 < stats_e["contre"]:
                contre_degats = calculer_degats(stats_e["atk"], def_j)
                player.hp -= contre_degats
                log.append(f"🔄 {enemy.nom} contre-attaque ! {contre_degats} dégâts")

    return _build_result(log, player, enemy)


def tick_enemy_attack(player: Player, enemy: Enemy):
    log = []
    stats_j = player.get_stats_effectives()
    stats_e = enemy.stats

    mods = get_passive_modifiers(player)
    atq_j = int(stats_j["atk"] * mods["atk_mult"])
    def_j = int(stats_j["def"] * mods["def_mult"])

    if enemy.hp > 0 and player.hp > 0:
        if is_enemy_frozen():
            log.append(f"{enemy.nom} est gele ! Attaque annulee")
        elif random.random() * 100 < stats_j["esquive"]:
            log.append(f"Vous esquivez l'attaque de {enemy.nom} !")
        else:
            degats = calculer_degats(stats_e["atk"], def_j)
            if random.random() * 100 < stats_e["crit_chance"]:
                degats = int(degats * stats_e["crit_mult"] / 100)
                log.append(f"{enemy.nom} CRITIQUE ! {degats} degats sur vous")
            else:
                log.append(f"{enemy.nom} vous inflige {degats} degats")
            absorbed = process_spells_on_player_hit(player, enemy, degats, log)
            degats_reels = degats - absorbed
            player.hp -= degats_reels
            if random.random() * 100 < stats_j["contre"]:
                contre_degats = calculer_degats(atq_j, stats_e["def"])
                enemy.hp -= contre_degats
                log.append(f"Vous contre-attaquez ! {contre_degats} degats")

    return _build_result(log, player, enemy)


def _build_result(log, player, enemy):
    resultat = None
    recompenses = {}

    if enemy.hp <= 0 and player.hp <= 0:
        resultat = "defaite"
        perte_xp = player.mourir()
        player.session_stats["mort"] += 1
        player.session_stats["kills_sans_mourir"] = 0
        log.append(f"Vous et {enemy.nom} etes tombes en meme temps ! -{perte_xp} XP")
        recompenses = {"perte_xp": perte_xp}

    elif enemy.hp <= 0:
        resultat = "victoire"
        xp_gagne = enemy.recompense_xp()
        or_gagne = enemy.recompense_or()
        niveau_avant = player.niveau
        player.ajouter_xp(xp_gagne)
        player.or_ += or_gagne
        player.kill_count += 1

        ss = player.session_stats
        ss["kills"] += 1
        ss["xp_gagnee"] += xp_gagne
        ss["or_gagne"] += or_gagne
        ss["kills_sans_mourir"] += 1
        if ss["kills_sans_mourir"] > ss["record_kills_sans_mourir"]:
            ss["record_kills_sans_mourir"] = ss["kills_sans_mourir"]
        if enemy.niveau > ss["plus_haut_ennemi"]:
            ss["plus_haut_ennemi"] = enemy.niveau
        ss["niveaux_montes"] += player.niveau - niveau_avant

        recompenses = {"xp": xp_gagne, "or": or_gagne}

        chance_loot = player.get_stats_effectives()["chance_loot"]
        nb_loots_garantis = int(chance_loot // 100)
        chance_bonus = chance_loot % 100
        nb_loots = nb_loots_garantis + (1 if random.random() * 100 < chance_bonus else 0)

        loots_tombes = []
        for _ in range(nb_loots):
            loot = Item(niveau=enemy.niveau)
            if enemy.boss:
                from config import RARITES
                idx = RARITES.index(loot.rarete)
                if idx < len(RARITES) - 1:
                    loot.rarete = RARITES[min(idx + 1, len(RARITES) - 1)]
                    loot.mods = loot._generer_mods()
                    loot.nom = loot._generer_nom()
            player.ajouter_item(loot)
            loots_tombes.append(loot.to_dict())
            log.append(f"🎁 Loot : {loot.nom} ({loot.rarete})")
            ss["loots_par_rarete"][loot.rarete] = ss["loots_par_rarete"].get(loot.rarete, 0) + 1
            from config import RARITES as _R
            if ss["meilleur_loot"] is None or _R.index(loot.rarete) > _R.index(ss["meilleur_loot"]["rarete"]):
                ss["meilleur_loot"] = {"nom": loot.nom, "rarete": loot.rarete}
        if loots_tombes:
            recompenses["loots"] = loots_tombes

        from config import ORBE_TYPES, SORTS
        orbes_tombes = []
        for orbe_key, orbe_data in ORBE_TYPES.items():
            chance = orbe_data["drop_chance"]
            if enemy.boss:
                chance *= 2
            if random.random() * 100 < chance:
                stacked = False
                for coffre in player.inventaire:
                    for existing in coffre:
                        if existing.slot == "orbe" and existing.orbe_type == orbe_key:
                            existing.quantite += 1
                            stacked = True
                            break
                    if stacked:
                        break
                if not stacked:
                    orbe_item = Item.__new__(Item)
                    orbe_item.slot = "orbe"
                    orbe_item.rarete = "Commun"
                    orbe_item.niveau = 1
                    orbe_item.nom = orbe_data["nom"]
                    orbe_item.mods = []
                    orbe_item.corrompu = False
                    orbe_item.orbe_type = orbe_key
                    orbe_item.spell_type = None
                    orbe_item.quantite = 1
                    orbe_item.locked = False
                    orbe_item.enchant_level = 0
                    player.ajouter_item(orbe_item)
                orbes_tombes.append({"type": orbe_key, "nom": orbe_data["nom"]})
                log.append(f"🔮 {orbe_data['nom']} obtenu(e) !")
                ss["orbes_obtenues"] += 1
        if orbes_tombes:
            recompenses["orbes"] = orbes_tombes

        from config import RARITE_SORT_NIVEAU
        artefact_chance = 2
        if enemy.boss:
            artefact_chance = 10
        if random.random() * 100 < artefact_chance:
            art = Item.__new__(Item)
            art.slot = "artefact"
            art.rarete = Item._roll_rarete()
            from config import RARITES
            min_rarete_idx = 1
            current_idx = RARITES.index(art.rarete)
            if current_idx < min_rarete_idx:
                art.rarete = RARITES[min_rarete_idx]
            art.niveau = RARITE_SORT_NIVEAU.get(art.rarete, 1)
            art.spell_type = random.choice(list(SORTS.keys()))
            art.nom = f"Artéfact de {SORTS[art.spell_type]['nom']}"
            art.mods = []
            art.corrompu = False
            art.orbe_type = None
            art.quantite = 1
            art.locked = False
            art.enchant_level = 0
            if enemy.boss:
                idx = RARITES.index(art.rarete)
                if idx < len(RARITES) - 1:
                    art.rarete = RARITES[min(idx + 1, len(RARITES) - 1)]
                    art.nom = f"Artéfact de {SORTS[art.spell_type]['nom']}"
            niv_sort = RARITE_SORT_NIVEAU.get(art.rarete, 1)
            player.ajouter_item(art)
            log.append(f"✨ ARTÉFACT : {art.nom} ({art.rarete}, Sort niv.{niv_sort})")

        if player.auto_supprimer:
            supprimes = 0
            for coffre in player.inventaire:
                avant = len(coffre)
                coffre[:] = [
                    it for it in coffre
                    if it.rarete not in player.auto_supprimer
                    or it.slot in ("orbe", "artefact")
                ]
                supprimes += avant - len(coffre)
            if supprimes > 0:
                from app import _consolider_inventaire
                _consolider_inventaire(player)
                log.append(f"Auto-suppression : {supprimes} objet(s) elimine(s)")

        log.append(f"{enemy.nom} vaincu ! +{xp_gagne} XP, +{or_gagne} or")

    elif player.hp <= 0:
        resultat = "defaite"
        perte_xp = player.mourir()
        player.session_stats["mort"] += 1
        player.session_stats["kills_sans_mourir"] = 0
        log.append(f"Vous etes mort ! -{perte_xp} XP. Resurrection...")
        recompenses = {"perte_xp": perte_xp}

    spell_stacks = None
    active_spells = get_active_spells(player)
    if active_spells:
        s = active_spells[0]
        spell_stacks = {
            "key": s["key"],
            "current": spell_state.get_stacks(s["key"]),
            "max": s["data"].get("stack_threshold", 0),
        }

    return {
        "log": log,
        "resultat": resultat,
        "recompenses": recompenses,
        "player_hp": player.hp,
        "player_hp_max": player.get_stats_effectives()["hp_max"],
        "enemy_hp": max(0, enemy.hp),
        "enemy_hp_max": enemy.stats["hp_max"],
        "spell_stacks": spell_stacks,
    }
