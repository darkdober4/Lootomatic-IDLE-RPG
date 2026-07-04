import random
from config import SORTS, RARITE_SORT_NIVEAU


class SpellState:
    def __init__(self):
        self.tick_count = 0
        self.cooldowns = {}
        self.active_effects = {}
        self.shield_active = False
        self.spectral_dodge = False
        self.next_attack_mult = 1.0
        self.hate_ticks_remaining = 0

    def reset(self):
        self.tick_count = 0
        self.cooldowns = {}
        self.active_effects = {}
        self.shield_active = False
        self.spectral_dodge = False
        self.next_attack_mult = 1.0
        self.hate_ticks_remaining = 0


spell_state = SpellState()


def get_active_spells(player):
    spells = []
    item = player.equipement.get("artefact")
    if item is None:
        return spells
    spell_type = getattr(item, "spell_type", None)
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

        if trigger == "interval":
            interval = data["interval_ticks"]
            if spell_state.tick_count % interval == 0:
                if key == "boule_feu":
                    degats = value
                    enemy.hp -= degats
                    log.append(f"🔥 Boule de Feu : {degats} dégâts purs sur {enemy.nom}")
                elif key == "frappe_astrale":
                    spell_state.next_attack_mult = 3.0
                    log.append(f"🌟 Frappe Astrale activée ! Prochain coup ×3")
                elif key == "hate_temporelle":
                    spell_state.hate_ticks_remaining = data.get("duration", 3)
                    log.append(f"⏩ Hâte Temporelle ! Vitesse ×2 pendant {spell_state.hate_ticks_remaining} ticks")

        elif trigger == "combat_start":
            if key == "poison" and spell_state.tick_count == 1:
                spell_state.active_effects["poison"] = {
                    "ticks_remaining": data.get("duration", 5),
                    "damage": value,
                }
                log.append(f"☠️ Poison appliqué sur {enemy.nom} ({value} dégâts/tick)")

        elif trigger == "chance":
            if key == "chaine_eclairs":
                if random.random() * 100 < data["chance"]:
                    spell_state.next_attack_mult = value / 100
                    log.append(f"⚡ Chaîne d'Éclairs ! Prochaine attaque ×{value/100}")

        elif trigger == "threshold_player":
            hp_pct = (player.hp / hp_max * 100) if hp_max > 0 else 0
            if hp_pct < data["threshold"]:
                if key == "bouclier_magique" and not spell_state.shield_active:
                    spell_state.shield_active = True
                    log.append(f"🛡️ Bouclier Magique activé ! (HP < {data['threshold']}%)")
                elif key == "regeneration" and "regeneration" not in spell_state.active_effects:
                    spell_state.active_effects["regeneration"] = {
                        "ticks_remaining": data.get("duration", 5),
                        "heal_pct": value,
                    }
                    log.append(f"💚 Régénération activée ! ({value}% HP/tick)")

    if "poison" in spell_state.active_effects:
        poison = spell_state.active_effects["poison"]
        if poison["ticks_remaining"] > 0 and enemy.hp > 0:
            enemy.hp -= poison["damage"]
            poison["ticks_remaining"] -= 1
            log.append(f"☠️ Poison : {poison['damage']} dégâts sur {enemy.nom}")
            if poison["ticks_remaining"] <= 0:
                del spell_state.active_effects["poison"]

    if "regeneration" in spell_state.active_effects:
        regen = spell_state.active_effects["regeneration"]
        if regen["ticks_remaining"] > 0 and player.hp > 0:
            heal = int(hp_max * regen["heal_pct"] / 100)
            player.hp = min(player.hp + heal, hp_max)
            regen["ticks_remaining"] -= 1
            log.append(f"💚 Régénération : +{heal} HP")
            if regen["ticks_remaining"] <= 0:
                del spell_state.active_effects["regeneration"]


def get_player_attack_multiplier():
    mult = spell_state.next_attack_mult
    spell_state.next_attack_mult = 1.0
    return mult


def get_hate_speed_bonus():
    if spell_state.hate_ticks_remaining > 0:
        spell_state.hate_ticks_remaining -= 1
        return 100
    return 0


def process_spells_on_player_hit(player, enemy, degats_recus, log):
    spells = get_active_spells(player)
    for sort in spells:
        key = sort["key"]
        data = sort["data"]
        value = sort["value"]

        if key == "bouclier_magique" and spell_state.shield_active:
            absorbed = min(degats_recus, value)
            spell_state.shield_active = False
            log.append(f"🛡️ Bouclier absorbe {absorbed} dégâts")
            return absorbed

        if key == "renvoi_sort" and data["trigger"] == "passive":
            reflet = int(degats_recus * value / 100)
            if reflet > 0:
                enemy.hp -= reflet
                log.append(f"🔄 Renvoi de Sort : {reflet} dégâts renvoyés à {enemy.nom}")

        if key == "esquive_spectrale" and data["trigger"] == "chance_when_hit":
            if random.random() * 100 < data["chance"]:
                spell_state.spectral_dodge = True
                log.append(f"👻 Esquive Spectrale ! Prochaine attaque évitée")

    return 0


def should_spectral_dodge():
    if spell_state.spectral_dodge:
        spell_state.spectral_dodge = False
        return True
    return False


def get_passive_modifiers(player):
    mods = {"atk_mult": 1.0, "def_mult": 1.0, "lifesteal_pct": 0}
    spells = get_active_spells(player)
    stats = player.get_stats_effectives()
    hp_max = stats["hp_max"]
    hp_pct = (player.hp / hp_max * 100) if hp_max > 0 else 100

    for sort in spells:
        key = sort["key"]
        data = sort["data"]
        value = sort["value"]

        if key == "vol_de_vie" and data["trigger"] == "passive":
            mods["lifesteal_pct"] += value

        if key == "berserker" and data["trigger"] == "passive_threshold":
            if hp_pct < data["threshold"]:
                mods["atk_mult"] += value / 100
                mods["def_mult"] -= 0.25

    return mods


def process_lifesteal(player, degats_infliges, log):
    mods = get_passive_modifiers(player)
    if mods["lifesteal_pct"] > 0:
        heal = int(degats_infliges * mods["lifesteal_pct"] / 100)
        if heal > 0:
            hp_max = player.get_stats_effectives()["hp_max"]
            player.hp = min(player.hp + heal, hp_max)
            log.append(f"🩸 Vol de Vie : +{heal} HP")


def process_execution(player, enemy, log):
    spells = get_active_spells(player)
    for sort in spells:
        if sort["key"] == "execution":
            hp_pct = (enemy.hp / enemy.stats["hp_max"] * 100) if enemy.stats["hp_max"] > 0 else 0
            if hp_pct <= sort["data"]["threshold"]:
                degats = sort["value"]
                enemy.hp -= degats
                log.append(f"⚰️ Exécution ! {degats} dégâts sur {enemy.nom} ({hp_pct:.0f}% HP)")
                return True
    return False
