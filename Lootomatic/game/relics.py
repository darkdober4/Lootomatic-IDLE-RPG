import random
from config import DONJON_RELICS


def tirage_reliques(nb=3, exclure=None):
    if exclure is None:
        exclure = []
    disponibles = [k for k in DONJON_RELICS if k not in exclure]
    if not disponibles:
        disponibles = list(DONJON_RELICS.keys())
    choises = random.sample(disponibles, min(nb, len(disponibles)))
    return choises


def appliquer_reliques_stats(stats_joueur, stats_ennemi, reliques):
    stats_j = dict(stats_joueur)
    stats_e = dict(stats_ennemi)

    for rel_key in reliques:
        if rel_key not in DONJON_RELICS:
            continue
        rel = DONJON_RELICS[rel_key]
        effet = rel["effet"]
        val = rel["valeur"]

        if effet == "enemy_atk_pct":
            stats_e["atk"] = max(1, int(stats_e["atk"] * (1 + val / 100)))
        elif effet == "enemy_def_pct":
            stats_e["def"] = max(0, int(stats_e["def"] * (1 + val / 100)))
        elif effet == "enemy_vitesse_pct":
            stats_e["vitesse_attaque"] = max(10, int(stats_e["vitesse_attaque"] * (1 + val / 100)))

    return stats_j, stats_e


def appliquer_reliques_player_stats(p, reliques, hp_pct=100):
    for rel_key in reliques:
        if rel_key not in DONJON_RELICS:
            continue
        rel = DONJON_RELICS[rel_key]
        effet = rel["effet"]
        val = rel["valeur"]

        if effet == "atk_pct":
            p.stats["atk"] = int(p.stats["atk"] * (1 + val / 100))
        elif effet == "def_pct":
            p.stats["def"] = int(p.stats["def"] * (1 + val / 100))
        elif effet == "hp_max_pct":
            p.stats["hp_max"] = int(p.stats["hp_max"] * (1 + val / 100))
        elif effet == "vitesse_attaque_pct":
            p.stats["vitesse_attaque"] = int(p.stats["vitesse_attaque"] * (1 + val / 100))
        elif effet == "crit_chance":
            p.stats["crit_chance"] += val
        elif effet == "crit_mult":
            p.stats["crit_mult"] += val
        elif effet == "contre":
            p.stats["contre"] += val
        elif effet == "esquive":
            p.stats["esquive"] = min(p.stats.get("esquive", 0) + val, 30)
        elif effet == "peau_pierre":
            p.stats["hp_max"] = int(p.stats["hp_max"] * (1 + val / 100))
            p.stats["def"] = int(p.stats["def"] * (1 + val / 100))


def get_relique_modifiers(reliques, hp_pct=100, is_first_attack=False):
    mods = {
        "atk_mult": 1.0,
        "crit_bonus": 0,
        "crit_mult_bonus": 0,
        "reduction_degats": 0,
        "epines_pct": 0,
        "vol_de_vie_bonus": 0,
        "bouclier_absorb": 0,
        "premier_coup_mult": 1.0,
    }

    for rel_key in reliques:
        if rel_key not in DONJON_RELICS:
            continue
        rel = DONJON_RELICS[rel_key]
        effet = rel["effet"]
        val = rel["valeur"]

        if effet == "vol_de_vie":
            mods["vol_de_vie_bonus"] += val
        elif effet == "bouclier_combat":
            mods["bouclier_absorb"] += val
        elif effet == "epines":
            mods["epines_pct"] += val
        elif effet == "reduction_degats":
            mods["reduction_degats"] += val
        elif effet == "rage_berserker" and hp_pct < 30:
            mods["atk_mult"] += val / 100
        elif effet == "sang_froid" and hp_pct > 70:
            mods["atk_mult"] += val / 100
        elif effet == "moment_critique" and hp_pct < 25:
            mods["crit_mult_bonus"] += val
        elif effet == "premier_coup" and is_first_attack:
            mods["premier_coup_mult"] = val
        elif effet == "chance_debutant" and is_first_attack:
            mods["crit_bonus"] += val

    return mods


def get_post_combat_regen(reliques, hp_max):
    total = 0
    for rel_key in reliques:
        if rel_key not in DONJON_RELICS:
            continue
        rel = DONJON_RELICS[rel_key]
        if rel["effet"] == "regen_combat":
            total += int(hp_max * rel["valeur"] / 100)
    return total


def get_vitesse_bonus(reliques, hp_pct):
    bonus = 0
    for rel_key in reliques:
        if rel_key not in DONJON_RELICS:
            continue
        rel = DONJON_RELICS[rel_key]
        if rel["effet"] == "second_souffle" and hp_pct < 40:
            bonus += rel["valeur"]
    return bonus
