import random
import math
from config import (
    STATS_BASE, STATS_PAR_NIVEAU, XP_BASE, XP_CROISSANCE,
    PENALITE_MORT_XP, STAT_ENNEMI_BASE, STAT_ENNEMI_PAR_NIVEAU,
    NOMS_MONSTRES, NOMS_BOSS, BOSS_CHANCE, BOSS_MULT_STATS,
    BOSS_MULT_XP, BOSS_MULT_OR, BOSS_MULT_LOOT,
    OR_BASE, OR_PAR_NIVEAU, OR_BOSS_MULT,
    RARITES, RARITE_POIDS, RARITE_MULT, MODIFICATEURS,
    MODS_MAX_PAR_OBJET, TYPES_OBJETS, SLOTS_EQUIPEMENT,
    CAPACITE_COFFRE, COUT_STATS, VIT_HP_BONUS, SORTS,
    ENCHANT_BONUS_PCT,
)


class Item:
    def __init__(self, slot=None, rarete=None, niveau=1):
        if slot is None:
            slot = random.choice(SLOTS_EQUIPEMENT[:-1])
        if rarete is None:
            rarete = self._roll_rarete()
        self.slot = slot
        self.rarete = rarete
        self.niveau = niveau
        self.nom = self._generer_nom()
        self.mods = self._generer_mods()
        self.corrompu = False
        self.orbe_type = None
        self.spell_type = None
        self.quantite = 1
        self.locked = False
        self.enchant_level = 0
        self.charges = 0
        self.evolution_tier = 0
        self.vivant = False

    @staticmethod
    def _roll_rarete():
        total = sum(RARITE_POIDS)
        r = random.uniform(0, total)
        cumul = 0
        for i, poids in enumerate(RARITE_POIDS):
            cumul += poids
            if r <= cumul:
                return RARITES[i]
        return RARITES[0]

    def _generer_nom(self):
        types = TYPES_OBJETS.get(self.slot, ["Objet"])
        base = random.choice(types)
        return f"{base} {self.rarete}"

    def _generer_mods(self):
        mult = RARITE_MULT.get(self.rarete, 1.0)
        nb_mods = MODS_MAX_PAR_OBJET.get(self.rarete, 1)
        mods_disponibles = list(MODIFICATEURS)
        mods_choisis = random.sample(
            mods_disponibles, min(nb_mods, len(mods_disponibles))
        )
        result = []
        for mod in mods_choisis:
            val_min = max(1, int(mod["min"] * mult * (1 + self.niveau * 0.1)))
            val_max = max(val_min + 1, int(mod["max"] * mult * (1 + self.niveau * 0.1)))
            valeur = random.randint(val_min, val_max)
            result.append({"nom": mod["nom"], "stat": mod["stat"], "valeur": valeur})
        return result

    def to_dict(self):
        return {
            "slot": self.slot,
            "rarete": self.rarete,
            "niveau": self.niveau,
            "nom": self.nom,
            "mods": self.mods,
            "corrompu": self.corrompu,
            "orbe_type": self.orbe_type,
            "spell_type": self.spell_type,
            "quantite": self.quantite,
            "locked": self.locked,
            "enchant_level": self.enchant_level,
            "charges": self.charges,
            "evolution_tier": self.evolution_tier,
            "vivant": self.vivant,
        }

    @classmethod
    def from_dict(cls, data):
        item = cls.__new__(cls)
        item.slot = data["slot"]
        item.rarete = data["rarete"]
        item.niveau = data["niveau"]
        item.nom = data["nom"]
        item.mods = data["mods"]
        item.corrompu = data.get("corrompu", False)
        item.orbe_type = data.get("orbe_type", None)
        item.spell_type = data.get("spell_type", None)
        item.quantite = data.get("quantite", 1)
        item.locked = data.get("locked", False)
        item.enchant_level = data.get("enchant_level", 0)
        item.charges = data.get("charges", 0)
        item.evolution_tier = data.get("evolution_tier", 0)
        item.vivant = data.get("vivant", False)
        if item.slot == "artefact" and item.spell_type and item.spell_type not in SORTS:
            remap = {
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
            new_type = remap.get(item.spell_type)
            if new_type:
                item.spell_type = new_type
                item.nom = f"Artefact de {SORTS[new_type]['nom']}"
        return item


class Player:
    def __init__(self):
        self.niveau = 1
        self.xp = 0
        self.xp_max = self._calculer_xp_max()
        self.points_stats = 0
        self.stats = dict(STATS_BASE)
        self.or_ = 0
        self.equipement = {slot: None for slot in SLOTS_EQUIPEMENT}
        self.inventaire = [[]]
        self.orbes = []
        self.kill_count = 0
        self.jetons = 0
        self.boss_donjon_battus = 0
        self.chapitres_completees = []
        self.donjon_actif = None
        self.auto_supprimer = []
        self.force_boss = False
        self.lang = "fr"
        self.session_stats = {
            "debut_session": None,
            "kills": 0,
            "degats_infliges": 0,
            "coups_donnes": 0,
            "plus_gros_coup": 0,
            "mort": 0,
            "kills_sans_mourir": 0,
            "record_kills_sans_mourir": 0,
            "plus_haut_ennemi": 0,
            "xp_gagnee": 0,
            "or_gagne": 0,
            "niveaux_montes": 0,
            "loots_par_rarete": {},
            "orbes_obtenues": 0,
            "meilleur_loot": None,
        }
        self.hp = self.get_stats_effectives()["hp_max"]

    def _calculer_xp_max(self):
        return int(XP_BASE * (XP_CROISSANCE ** (self.niveau - 1)))

    def ajouter_xp(self, quantite):
        self.xp += quantite
        while self.xp >= self.xp_max:
            self.xp -= self.xp_max
            self.niveau += 1
            self.points_stats += STATS_PAR_NIVEAU + self.boss_donjon_battus
            self.xp_max = self._calculer_xp_max()

    def mourir(self):
        perte = int(self.xp * PENALITE_MORT_XP)
        self.xp = max(0, self.xp - perte)
        self.hp = self.get_stats_effectives()["hp_max"]
        return perte

    def allouer_stat(self, stat):
        if stat not in COUT_STATS:
            return False
        cout = COUT_STATS[stat]
        if self.points_stats < cout:
            return False
        self.points_stats -= cout
        self.stats[stat] += 1
        if stat == "hp_max":
            self.hp += 1
        if stat == "vit":
            self.hp += VIT_HP_BONUS
        return True

    def get_stats_effectives(self):
        stats = dict(self.stats)
        for slot, item in self.equipement.items():
            if item is None:
                continue
            enchant_mult = 1 + item.enchant_level * ENCHANT_BONUS_PCT / 100
            for mod in item.mods:
                stat = mod["stat"]
                if stat in stats:
                    stats[stat] += int(mod["valeur"] * enchant_mult)
        stats["hp_max"] += stats.get("vit", 0) * VIT_HP_BONUS
        stats["esquive"] = min(stats.get("esquive", 0), 30)
        if stats.get("crit_chance", 0) > 100:
            stats["atk"] += stats["crit_chance"] - 100
            stats["crit_chance"] = 100
        if stats.get("contre", 0) > 100:
            stats["atk"] += stats["contre"] - 100
            stats["contre"] = 100
        if stats.get("chance_loot", 0) > 2000:
            stats["atk"] += stats["chance_loot"] - 2000
            stats["chance_loot"] = 2000
        return stats

    def ajouter_item(self, item):
        for coffre in self.inventaire:
            if len(coffre) < CAPACITE_COFFRE:
                coffre.append(item)
                return True
        self.inventaire.append([item])
        return True

    def ajouter_orbe(self, orbe):
        self.orbes.append(orbe)

    def equiper_item(self, coffre_idx, item_idx):
        if coffre_idx >= len(self.inventaire):
            return None
        coffre = self.inventaire[coffre_idx]
        if item_idx >= len(coffre):
            return None
        item = coffre[item_idx]
        ancien = self.equipement.get(item.slot)
        self.equipement[item.slot] = item
        coffre.pop(item_idx)
        if ancien is not None:
            self.ajouter_item(ancien)
        return ancien

    def desequiper_item(self, slot):
        item = self.equipement.get(slot)
        if item is None:
            return False
        if not self.ajouter_item(item):
            return False
        if getattr(item, 'vivant', False):
            item.charges = 0
        self.equipement[slot] = None
        return True

    def to_dict(self):
        return {
            "niveau": self.niveau,
            "xp": self.xp,
            "xp_max": self.xp_max,
            "points_stats": self.points_stats,
            "stats": self.stats,
            "hp": self.hp,
            "or": self.or_,
            "equipement": {
                slot: item.to_dict() if item else None
                for slot, item in self.equipement.items()
            },
            "inventaire": [
                [item.to_dict() for item in coffre]
                for coffre in self.inventaire
            ],
            "orbes": self.orbes,
            "kill_count": self.kill_count,
            "jetons": self.jetons,
            "boss_donjon_battus": self.boss_donjon_battus,
            "chapitres_completees": self.chapitres_completees,
            "donjon_actif": self.donjon_actif,
            "auto_supprimer": self.auto_supprimer,
            "force_boss": self.force_boss,
            "lang": self.lang,
        }

    @classmethod
    def from_dict(cls, data):
        p = cls()
        p.niveau = data["niveau"]
        p.xp = data["xp"]
        p.xp_max = data["xp_max"]
        p.points_stats = data["points_stats"]
        p.stats = data["stats"]
        p.hp = data["hp"]
        p.or_ = data["or"]
        p.equipement = {
            slot: Item.from_dict(item) if item else None
            for slot, item in data["equipement"].items()
        }
        p.inventaire = [
            [Item.from_dict(item) for item in coffre]
            for coffre in data["inventaire"]
        ]
        p.orbes = data.get("orbes", [])
        p.kill_count = data.get("kill_count", 0)
        p.jetons = data.get("jetons", 0)
        p.boss_donjon_battus = data.get("boss_donjon_battus", 0)
        p.chapitres_completees = data.get("chapitres_completees", [])
        p.donjon_actif = data.get("donjon_actif", None)
        p.auto_supprimer = data.get("auto_supprimer", [])
        p.force_boss = data.get("force_boss", False)
        p.lang = data.get("lang", "fr")
        return p


class Enemy:
    def __init__(self, niveau=1, boss=None):
        if boss is None:
            boss = random.random() < BOSS_CHANCE
        self.niveau = niveau
        self.boss = boss
        self.nom = self._generer_nom()
        self.stats = self._generer_stats()
        self.hp = self.stats["hp_max"]

    def _generer_nom(self):
        if self.boss:
            return random.choice(NOMS_BOSS)
        noms_dispo = NOMS_MONSTRES[:min(len(NOMS_MONSTRES), 5 + self.niveau // 3)]
        return random.choice(noms_dispo)

    def _generer_stats(self):
        stats = {}
        for stat, base in STAT_ENNEMI_BASE.items():
            croissance = STAT_ENNEMI_PAR_NIVEAU.get(stat, 0)
            val = base + int(croissance * (self.niveau - 1))
            if self.boss:
                val = int(val * BOSS_MULT_STATS)
            stats[stat] = val
        stats["esquive"] = min(stats.get("esquive", 0), 30)
        return stats

    def recompense_xp(self):
        base = 10 + self.niveau * 5
        if self.boss:
            base = int(base * BOSS_MULT_XP)
        return base

    def recompense_or(self):
        base = OR_BASE + OR_PAR_NIVEAU * self.niveau
        if self.boss:
            base = int(base * OR_BOSS_MULT)
        return base

    def to_dict(self):
        return {
            "niveau": self.niveau,
            "boss": self.boss,
            "nom": self.nom,
            "stats": self.stats,
            "hp": self.hp,
        }

    @classmethod
    def from_dict(cls, data):
        e = cls.__new__(cls)
        e.niveau = data["niveau"]
        e.boss = data["boss"]
        e.nom = data["nom"]
        e.stats = data["stats"]
        e.hp = data["hp"]
        return e
