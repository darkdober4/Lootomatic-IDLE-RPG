from config import SORTS, RARITE_SORT_NIVEAU


class SpellState:
    def __init__(self):
        self.stacks = {}
        self.tick_count = 0
        self.active_effects = {}
        self.next_attack_mult = 1.0
        self.hate_ticks_remaining = 0
        self.shield_active = False
        self.shield_value = 0
        self.malediction_hits = 0
        self.malediction_bonus = 50
        self.lifesteal_bonus = 0
        self.enemy_frozen = 0
        self.accumulated_damage = 0

    def reset(self):
        self.stacks = {}
        self.tick_count = 0
        self.active_effects = {}
        self.next_attack_mult = 1.0
        self.hate_ticks_remaining = 0
        self.shield_active = False
        self.shield_value = 0
        self.malediction_hits = 0
        self.malediction_bonus = 50
        self.lifesteal_bonus = 0
        self.enemy_frozen = 0
        self.accumulated_damage = 0

    def add_stack(self, spell_key, count=1):
        self.stacks[spell_key] = self.stacks.get(spell_key, 0) + count

    def get_stacks(self, spell_key):
        return self.stacks.get(spell_key, 0)

    def reset_stacks(self, spell_key):
        self.stacks[spell_key] = 0

    def get_all_stacks(self):
        return dict(self.stacks)


spell_state = SpellState()


OLD_SPELL_REMAP = {
    "boule_feu": "surge_flammes",
    "frappe_astrale": "lame_spectrale",
    "bouclier_magique": "peau_fer",
    "regeneration": "vol_ame",
    "esquive_spectrale": "gel_accumule",
    "renvoi_sort": "vengeance",
    "vol_de_vie": "vol_ame",
    "berserker": "marque_maudite",
    "hate_temporelle": "distorsion",
}


def get_active_spells(player):
    spells = []
    item = player.equipement.get("artefact")
    if item is None:
        return spells
    spell_type = getattr(item, "spell_type", None)
    if spell_type and spell_type not in SORTS:
        spell_type = OLD_SPELL_REMAP.get(spell_type)
        if spell_type:
            item.spell_type = spell_type
            item.nom = f"Artefact de {SORTS[spell_type]['nom']}"
    if spell_type and spell_type in SORTS:
        niveau = RARITE_SORT_NIVEAU.get(item.rarete, 1)
        sort_data = SORTS[spell_type]
        level_mult = 1 + (niveau - 1) * 0.5
        value = int(sort_data["base_value"] * level_mult)
        if spell_type == "poison":
            atk = player.get_stats_effectives()["atk"]
            value = int(value * (1 + atk / 100))
        spells.append({
            "key": spell_type,
            "data": sort_data,
            "niveau": niveau,
            "value": value,
        })
    return spells


def process_spells_before_player_attack(player, enemy, log):
    spells = get_active_spells(player)
    spell_state.tick_count += 1
    stats = player.get_stats_effectives()
    hp_max = stats["hp_max"]

    for sort in spells:
        key = sort["key"]
        data = sort["data"]
        value = sort["value"]
        trigger = data["trigger"]

        if trigger == "stack_auto":
            spell_state.add_stack(key)
            _check_stack_threshold(key, sort, player, enemy, log)

        elif trigger == "combat_start":
            if key == "poison" and spell_state.tick_count == 1:
                spell_state.active_effects["poison"] = {
                    "ticks_remaining": data.get("duration", 5),
                    "damage": value,
                }
                log.append(f"Poison applique sur {enemy.nom} ({value} degats/tick)")

    if "poison" in spell_state.active_effects:
        poison = spell_state.active_effects["poison"]
        if poison["ticks_remaining"] > 0 and enemy.hp > 0:
            enemy.hp -= poison["damage"]
            poison["ticks_remaining"] -= 1
            log.append(f"Poison : {poison['damage']} degats sur {enemy.nom}")
            if poison["ticks_remaining"] <= 0:
                del spell_state.active_effects["poison"]

    if "hemorragie_bleed" in spell_state.active_effects:
        bleed = spell_state.active_effects["hemorragie_bleed"]
        if bleed["ticks_remaining"] > 0 and enemy.hp > 0:
            enemy.hp -= bleed["damage"]
            bleed["ticks_remaining"] -= 1
            log.append(f"Hemorragie : {bleed['damage']} degats sur {enemy.nom}")
            if bleed["ticks_remaining"] <= 0:
                del spell_state.active_effects["hemorragie_bleed"]


def accumulate_stacks_on_hit(spell_key, sort, player, enemy, log):
    data = sort["data"]
    if data["trigger"] != "stack_on_hit":
        return
    spell_state.add_stack(spell_key)
    _check_stack_threshold(spell_key, sort, player, enemy, log)


def accumulate_stacks_on_damage_taken(spell_key, sort, player, enemy, degats_recus, log):
    data = sort["data"]
    if data["trigger"] != "stack_on_damage_taken":
        return
    spell_state.add_stack(spell_key)
    _check_stack_threshold(spell_key, sort, player, enemy, log)


def _check_stack_threshold(spell_key, sort, player, enemy, log):
    data = sort["data"]
    threshold = data.get("stack_threshold", 0)
    if threshold <= 0:
        return
    if spell_state.get_stacks(spell_key) < threshold:
        return

    value = sort["value"]
    spell_state.reset_stacks(spell_key)
    _trigger_spell_effect(spell_key, sort, player, enemy, log)


def _trigger_spell_effect(key, sort, player, enemy, log):
    data = sort["data"]
    value = sort["value"]
    niveau = sort["niveau"]
    level_mult = 1 + (niveau - 1) * 0.5
    stats = player.get_stats_effectives()
    hp_max = stats["hp_max"]

    if key == "surge_flammes":
        enemy.hp -= value
        log.append(f"Surge de Flammes ! {value} degats purs sur {enemy.nom}")

    elif key == "hemorragie":
        spell_state.active_effects["hemorragie_bleed"] = {
            "ticks_remaining": data.get("duration", 3),
            "damage": value,
        }
        log.append(f"Hemorragie declenchee ! {value} degats/tick pendant {data.get('duration', 3)} ticks")

    elif key == "gel_accumule":
        spell_state.enemy_frozen = niveau
        log.append(f"Gel Accumule ! {enemy.nom} gele pour {niveau} attaque(s)")

    elif key == "vengeance":
        total = int(spell_state.accumulated_damage * level_mult)
        if total > 0:
            enemy.hp -= total
            log.append(f"Vengeance ! {total} degats accumules relaches sur {enemy.nom} (x{level_mult})")
            spell_state.accumulated_damage = 0

    elif key == "chaine_eclairs":
        degats = value
        enemy.hp -= degats
        log.append(f"Chaine d'Eclairs ! {degats} degats sur {enemy.nom}")

    elif key == "vol_ame":
        heal = int(hp_max * value / 100)
        if heal > 0:
            spell_state.lifesteal_bonus += value
            player.hp = min(player.hp + heal, hp_max)
            log.append(f"Vol d'Ame ! +{heal} HP et +{value}% vol de vie permanent")

    elif key == "lame_spectrale":
        mult = 1.5 + niveau * 0.5
        spell_state.next_attack_mult = mult
        log.append(f"Lame Spectrale ! Prochain coup x{mult} degats")

    elif key == "marque_maudite":
        hits = 4 + niveau
        bonus_pct = 40 + niveau * 10
        spell_state.malediction_hits = hits
        spell_state.malediction_bonus = bonus_pct
        log.append(f"Marque Maudite ! +{bonus_pct}% degats pendant {hits} coups")

    elif key == "peau_fer":
        spell_state.shield_active = True
        spell_state.shield_value = value
        log.append(f"Peau de Fer ! Bouclier de {value} points actif")

    elif key == "distorsion":
        ticks = 2 + niveau
        spell_state.hate_ticks_remaining = ticks
        log.append(f"Distorsion ! Vitesse x2 pendant {ticks} ticks")

    elif key == "execution":
        enemy_hp_pct = (enemy.hp / enemy.stats["hp_max"] * 100) if enemy.stats["hp_max"] > 0 else 0
        threshold_pct = data.get("enemy_hp_threshold", 30)
        if enemy_hp_pct <= threshold_pct:
            exec_mult = 3 + niveau
            degats = int(player.get_stats_effectives()["atk"] * exec_mult)
            enemy.hp -= degats
            log.append(f"EXECUTION ! {degats} degats massifs sur {enemy.nom} (x{exec_mult})")
        else:
            log.append(f"Execution echouee ({enemy_hp_pct:.0f}% HP, besoin < {threshold_pct}%)")


def get_player_attack_multiplier():
    mult = spell_state.next_attack_mult
    if spell_state.malediction_hits > 0:
        mult *= 1 + spell_state.malediction_bonus / 100
        spell_state.malediction_hits -= 1
    spell_state.next_attack_mult = 1.0
    return mult


def get_hate_speed_bonus():
    if spell_state.hate_ticks_remaining > 0:
        spell_state.hate_ticks_remaining -= 1
        return 100
    return 0


def is_enemy_frozen():
    if spell_state.enemy_frozen > 0:
        spell_state.enemy_frozen -= 1
        return True
    return False


def process_spells_on_player_hit(player, enemy, degats_recus, log):
    spells = get_active_spells(player)

    if spell_state.shield_active:
        absorbed = min(degats_recus, spell_state.shield_value)
        spell_state.shield_active = False
        spell_state.shield_value = 0
        log.append(f"Peau de Fer absorbe {absorbed} degats")
        return absorbed

    spell_state.accumulated_damage += degats_recus

    for sort in spells:
        key = sort["key"]
        accumulate_stacks_on_damage_taken(key, sort, player, enemy, degats_recus, log)

    return 0


def get_passive_modifiers(player):
    mods = {"atk_mult": 1.0, "def_mult": 1.0, "lifesteal_pct": spell_state.lifesteal_bonus}
    return mods


def process_lifesteal(player, degats_infliges, log):
    if spell_state.lifesteal_bonus > 0:
        heal = int(degats_infliges * spell_state.lifesteal_bonus / 100)
        if heal > 0:
            hp_max = player.get_stats_effectives()["hp_max"]
            player.hp = min(player.hp + heal, hp_max)
            log.append(f"Vol d'Ame : +{heal} HP")


def process_execution(player, enemy, log):
    return False
