STATS_PAR_NIVEAU = 2

VIT_HP_BONUS = 5

STATS_BASE = {
    "hp_max": 100,
    "atk": 10,
    "def": 5,
    "vit": 10,
    "crit_chance": 5,
    "crit_mult": 150,
    "esquive": 3,
    "chance_loot": 50,
    "contre": 5,
    "vitesse_attaque": 100,
    "niveau_sorts": 0,
}

STATS_LABELS = {
    "hp_max": "PV Max",
    "atk": "ATQ",
    "def": "DÉF",
    "vit": "VIT",
    "crit_chance": "Critique %",
    "crit_mult": "Dégâts Crit. %",
    "esquive": "Esquive %",
    "chance_loot": "Chance de Loot %",
    "contre": "Contre-attaque %",
    "vitesse_attaque": "Vit. Attaque",
    "niveau_sorts": "Niveau Sorts",
}

COUT_STATS = {
    "hp_max": 1,
    "atk": 1,
    "def": 1,
    "vit": 1,
    "crit_chance": 1,
    "crit_mult": 5,
    "esquive": 1,
    "chance_loot": 1,
    "contre": 1,
    "vitesse_attaque": 1,
    "niveau_sorts": 1,
}

XP_BASE = 50
XP_CROISSANCE = 1.15

PENALITE_MORT_XP = 0.15

BOSS_CHANCE = 0.05
BOSS_MULT_STATS = 3.0
BOSS_MULT_XP = 5.0
BOSS_MULT_OR = 5.0
BOSS_MULT_LOOT = 2.0

STAT_ENNEMI_BASE = {
    "hp_max": 80,
    "atk": 8,
    "def": 3,
    "vit": 8,
    "crit_chance": 3,
    "crit_mult": 130,
    "esquive": 2,
    "chance_loot": 0,
    "contre": 2,
    "vitesse_attaque": 80,
    "niveau_sorts": 0,
}

STAT_ENNEMI_PAR_NIVEAU = {
    "hp_max": 15,
    "atk": 3,
    "def": 1,
    "vit": 2,
    "crit_chance": 0.5,
    "crit_mult": 3,
    "esquive": 0.3,
    "contre": 0.3,
    "vitesse_attaque": 2,
    "niveau_sorts": 0,
}

NOMS_MONSTRES = [
    "Gobelin", "Squelette", "Slime", "Rat Géant", "Chauve-souris",
    "Loup", "Araignée", "Zombie", "Bandit", "Spectre",
    "Orc", "Troll", "Gargouille", "Mimic", "Élémentaire",
    "Démon Mineur", "Golem", "Wyverne", "Liche", "Dragon",
]

NOMS_BOSS = [
    "Roi Gobelin", "Seigneur Squelette", "Archidémon",
    "Dragon Ancien", "Liche Suprême", "Titan de Pierre",
]

RARITES = ["Commun", "Rare", "Épique", "Légendaire", "Mythique"]

RARITE_POIDS = [86.5, 10, 2, 1, 0.5]

RARITE_MULT = {
    "Commun": 1.0,
    "Rare": 1.5,
    "Épique": 2.0,
    "Légendaire": 3.0,
    "Mythique": 5.0,
}

RARITE_COULEURS = {
    "Commun": "#b0b0b0",
    "Rare": "#4a90d9",
    "Épique": "#a855f7",
    "Légendaire": "#f59e0b",
    "Mythique": "#ef4444",
}

SLOTS_EQUIPEMENT = [
    "arme", "armure", "casque", "bouclier",
    "anneau", "amulette", "ceinture", "bottes", "artefact",
]

TYPES_OBJETS = {
    "arme": ["Épée", "Hache", "Masse", "Dague", "Bâton"],
    "armure": ["Cuirasse", "Plastron", "Robe", "Cotte de mailles"],
    "casque": ["Heaume", "Capuchon", "Couronne", "Diadème"],
    "bouclier": ["Bouclier", "Pavois", "Écu", "Rondache"],
    "anneau": ["Anneau", "Bague", "Signet"],
    "amulette": ["Amulette", "Pendentif", "Collier", "Talisman"],
    "ceinture": ["Ceinture", "Baudrier", "Écharpe"],
    "bottes": ["Bottes", "Sandales", "Greaves", "Bottines"],
    "artefact": ["Orbe", "Cristal", "Relique"],
    "orbe": ["Orbe"],
}

MODIFICATEURS = [
    {"nom": "Force", "stat": "atk", "min": 1, "max": 3, "poids": 30},
    {"nom": "Robustesse", "stat": "hp_max", "min": 2, "max": 10, "poids": 25},
    {"nom": "Protection", "stat": "def", "min": 1, "max": 2, "poids": 25},
    {"nom": "Agilité", "stat": "esquive", "min": 1, "max": 2, "poids": 15},
    {"nom": "Précision", "stat": "crit_chance", "min": 1, "max": 2, "poids": 15},
    {"nom": "Fureur", "stat": "crit_mult", "min": 2, "max": 8, "poids": 10},
    {"nom": "Riposte", "stat": "contre", "min": 1, "max": 2, "poids": 10},
    {"nom": "Hâte", "stat": "vitesse_attaque", "min": 2, "max": 5, "poids": 8},
    {"nom": "Fortune", "stat": "chance_loot", "min": 1, "max": 3, "poids": 8},
    {"nom": "Vitalité", "stat": "vit", "min": 1, "max": 2, "poids": 20},
]

MODS_MAX_PAR_OBJET = {
    "Commun": 1,
    "Rare": 2,
    "Épique": 3,
    "Légendaire": 4,
    "Mythique": 5,
}

OR_BASE = 10
OR_PAR_NIVEAU = 3
OR_BOSS_MULT = 5.0

CAPACITE_COFFRE = 20

TICK_INTERVAL_MS = 1000

ORBE_TYPES = {
    "amelioration": {
        "nom": "Orbe d'Amélioration",
        "description": "Augmente de +1 chaque stat présente sur l'objet",
        "drop_chance": 15,
    },
    "alteration": {
        "nom": "Orbe d'Altération",
        "description": "Ajoute un mod aléatoire, peut augmenter la rareté. 40% de corrompre l'objet.",
        "drop_chance": 5,
        "corruption_chance": 40,
        "rarete_up_chance": 25,
    },
}

SORTS = {
    "boule_feu": {
        "nom": "Boule de Feu",
        "categorie": "offensif",
        "description": "Inflige des dégâts magiques purs (ignore la DEF)",
        "trigger": "interval",
        "interval_ticks": 5,
        "base_value": 20,
    },
    "chaine_eclairs": {
        "nom": "Chaîne d'Éclairs",
        "categorie": "offensif",
        "description": "Prochaine attaque ×1.5 dégâts",
        "trigger": "chance",
        "chance": 15,
        "base_value": 150,
    },
    "poison": {
        "nom": "Poison",
        "categorie": "offensif",
        "description": "Dégâts sur la durée pendant 5 ticks",
        "trigger": "combat_start",
        "base_value": 5,
        "duration": 5,
    },
    "execution": {
        "nom": "Exécution",
        "categorie": "offensif",
        "description": "Dégâts massifs si ennemi sous 20% HP",
        "trigger": "threshold_enemy",
        "threshold": 20,
        "base_value": 300,
    },
    "frappe_astrale": {
        "nom": "Frappe Astrale",
        "categorie": "offensif",
        "description": "Prochain coup = dégâts ×3",
        "trigger": "interval",
        "interval_ticks": 8,
        "base_value": 300,
    },
    "bouclier_magique": {
        "nom": "Bouclier Magique",
        "categorie": "defensif",
        "description": "Absorbe les dégâts du prochain coup",
        "trigger": "threshold_player",
        "threshold": 50,
        "base_value": 30,
    },
    "regeneration": {
        "nom": "Régénération",
        "categorie": "defensif",
        "description": "Heal de X% HP max sur 5 ticks",
        "trigger": "threshold_player",
        "threshold": 30,
        "base_value": 5,
        "duration": 5,
    },
    "esquive_spectrale": {
        "nom": "Esquive Spectrale",
        "categorie": "defensif",
        "description": "Prochaine attaque ennemie ratée à 100%",
        "trigger": "chance_when_hit",
        "chance": 20,
        "base_value": 100,
    },
    "renvoi_sort": {
        "nom": "Renvoi de Sort",
        "categorie": "defensif",
        "description": "Renvoie X% des dégâts reçus à l'ennemi",
        "trigger": "passive",
        "base_value": 15,
    },
    "vol_de_vie": {
        "nom": "Vol de Vie",
        "categorie": "utilitaire",
        "description": "X% des dégâts infligés soignent le héros",
        "trigger": "passive",
        "base_value": 10,
    },
    "berserker": {
        "nom": "Berserker",
        "categorie": "utilitaire",
        "description": "+50% ATQ mais -25% DEF quand HP < 25%",
        "trigger": "passive_threshold",
        "threshold": 25,
        "base_value": 50,
    },
    "hate_temporelle": {
        "nom": "Hâte Temporelle",
        "categorie": "utilitaire",
        "description": "×2 vitesse d'attaque pendant 3 ticks",
        "trigger": "interval",
        "interval_ticks": 12,
        "base_value": 3,
        "duration": 3,
    },
}

RARITE_SORT_NIVEAU = {
    "Commun": 1,
    "Rare": 2,
    "Épique": 3,
    "Légendaire": 4,
    "Mythique": 5,
}

# ─── DONJON ───────────────────────────────────────────────────────────────────

DONJON_COLS = 7
DONJON_ETAGES = 20
DONJON_NODES_MIN = 3
DONJON_NODES_MAX = 5
DONJON_BOSS_MULT = 2.5
DONJON_XP_BOSS = 100
DONJON_JETONS_MIN = 5
DONJON_JETONS_MAX = 10
DONJON_ITEMS_RECOMPENSE = 3

DONJON_NIVEAU_PAR_CHAPITRE = {1: 10, 2: 20, 3: 30, 4: 40, 5: 50}

DONJON_NODE_PROBS = {
    "combat": 45,
    "camp": 15,
    "evenement": 25,
    "relique": 15,
}

DONJON_EVENEMENTS = [
    {"type": "objet", "poids": 25, "description": "Vous trouvez un objet abandonné."},
    {"type": "relique", "poids": 15, "description": "Un autel ancien brille faiblement."},
    {"type": "guérison", "poids": 20, "description": "Une source magique restore vos forces."},
    {"type": "teleport", "poids": 10, "description": "Un portail mystique s'ouvre devant vous."},
    {"type": "or", "poids": 15, "description": "Un coffre rempli d'or !"},
    {"type": "malédiction", "poids": 15, "description": "Une énergie sombre vous envahit..."},
]

DONJON_RELICS = {
    "coeur_fer": {"nom": "Cœur de Fer", "description": "+15% PV Max", "effet": "hp_max_pct", "valeur": 15, "categorie": "buff"},
    "lame_aiguisee": {"nom": "Lame Aiguisée", "description": "+10% ATQ", "effet": "atk_pct", "valeur": 10, "categorie": "buff"},
    "bouclier_ancien": {"nom": "Bouclier Ancien", "description": "+15% DÉF", "effet": "def_pct", "valeur": 15, "categorie": "buff"},
    "bottes_vent": {"nom": "Bottes du Vent", "description": "+10% Vitesse d'attaque", "effet": "vitesse_attaque_pct", "valeur": 10, "categorie": "buff"},
    "oeil_aigle": {"nom": "Œil de l'Aigle", "description": "+5% Critique", "effet": "crit_chance", "valeur": 5, "categorie": "buff"},
    "pierre_fureur": {"nom": "Pierre de Fureur", "description": "+20% Dégâts critiques", "effet": "crit_mult", "valeur": 20, "categorie": "buff"},
    "gants_riposte": {"nom": "Gants de Riposte", "description": "+5% Contre-attaque", "effet": "contre", "valeur": 5, "categorie": "buff"},
    "amulette_vampire": {"nom": "Amulette du Vampire", "description": "+8% Vol de vie", "effet": "vol_de_vie", "valeur": 8, "categorie": "buff"},
    "plume_esquive": {"nom": "Plume d'Esquive", "description": "+5% Esquive", "effet": "esquive", "valeur": 5, "categorie": "buff"},
    "regen_naturelle": {"nom": "Régénération Naturelle", "description": "Regen 5% PV après chaque combat", "effet": "regen_combat", "valeur": 5, "categorie": "buff"},
    "barriere_magique": {"nom": "Barrière Magique", "description": "Absorbe 15 dégâts au début de chaque combat", "effet": "bouclier_combat", "valeur": 15, "categorie": "buff"},
    "rage_berserker": {"nom": "Rage du Berserker", "description": "+20% ATQ si PV < 30%", "effet": "rage_berserker", "valeur": 20, "categorie": "buff"},
    "second_souffle": {"nom": "Second Souffle", "description": "+25% Vitesse si PV < 40%", "effet": "second_souffle", "valeur": 25, "categorie": "buff"},
    "aura_intimidation": {"nom": "Aura d'Intimidation", "description": "Ennemis -10% ATQ", "effet": "enemy_atk_pct", "valeur": -10, "categorie": "debuff"},
    "malediction_faiblesse": {"nom": "Malédiction de Faiblesse", "description": "Ennemis -10% DÉF", "effet": "enemy_def_pct", "valeur": -10, "categorie": "debuff"},
    "sort_len": {"nom": "Sort de Lenteur", "description": "Ennemis -10% Vitesse", "effet": "enemy_vitesse_pct", "valeur": -10, "categorie": "debuff"},
    "epines": {"nom": "Épines Enchantées", "description": "Renvoie 10% des dégâts reçus", "effet": "epines", "valeur": 10, "categorie": "buff"},
    "premier_coup": {"nom": "Premier Coup", "description": "Première attaque du combat inflige ×2", "effet": "premier_coup", "valeur": 2, "categorie": "buff"},
    "chance_du_debutant": {"nom": "Chance du Débutant", "description": "+10% Critique au premier combat", "effet": "chance_debutant", "valeur": 10, "categorie": "buff"},
    "resilience": {"nom": "Résilience", "description": "Dégâts reçus réduits de 5", "effet": "reduction_degats", "valeur": 5, "categorie": "buff"},
    "sang_froid": {"nom": "Sang-Froid", "description": "+15% Dégâts si PV > 70%", "effet": "sang_froid", "valeur": 15, "categorie": "buff"},
    "moment_critique": {"nom": "Moment Critique", "description": "+30% Dégâts critiques si PV < 25%", "effet": "moment_critique", "valeur": 30, "categorie": "buff"},
    "peau_pierre": {"nom": "Peau de Pierre", "description": "+8% PV Max et +8% DÉF", "effet": "peau_pierre", "valeur": 8, "categorie": "buff"},
}

# ─── MACHINE À SOUS ──────────────────────────────────────────────────────────

SLOT_MACHINE_COUT = 1

SLOT_MACHINE_SYMBOLES = [
    {"id": "epee",    "icone": "EPE",  "poids": 20},
    {"id": "bouclier","icone": "BOU",  "poids": 20},
    {"id": "potion",  "icone": "POT",  "poids": 20},
    {"id": "gemme",   "icone": "GEM",  "poids": 15},
    {"id": "couronne","icone": "CRN",  "poids": 12},
    {"id": "etoile",  "icone": "ETO",  "poids": 8},
    {"id": "tresor",  "icone": "TRE",  "poids": 5},
]

SLOT_MACHINE_GAINS = {
    "triple": {
        "rarete": "Mythique",
        "message": "TRIPLE ! Equipement Mythique gagne !",
    },
    "double_gauche": {
        "rarete": "Légendaire",
        "message": "PAIRE ! Equipement Legendaire gagne !",
    },
}

PRO_TIPS = [
    "Les boss donnent 5x plus d'or et d'XP que les ennemis normaux.",
    "La VIT donne +5 PV Max par point investi.",
    "L'Esquive est plafonnee a 30%, inutile d'aller au-dela.",
    "200% de Chance Loot = 2 objets garantis par kill.",
    "Les orbes d'Alteration peuvent augmenter la rarete d'un objet.",
    "Un objet monte au Mythique par orbe d'alteration est automatiquement corrompu.",
    "Les boss ont 5% de chance d'apparaitre a chaque ennemi.",
    "L'orbe d'Amelioration a 10% de risque de corrompre l'objet.",
    "Les artefacts donnent des sorts, leur niveau depend de la rarete.",
    "Le donjon rapporte 5 a 10 jetons par chapitre complete.",
    "La machine a sous donne du Legendaire minimum en cas de gain.",
    "La Vitesse d'Attaque du joueur et de l'ennemi sont independantes.",
    "L'amulette vampire du donjon donne 8% de vol de vie sur les degats infliges.",
    "Les objets Corrompus ne peuvent plus etre modifies par des orbes.",
    "La DEF reduit les degats selon la formule : DEF / (DEF + 100).",
    "Passer a l'ennemi suivant vous soigne integralement — soin gratuit quand bas en PV.",
    "La mort fait perdre 15% de l'XP actuelle, pas de l'XP max. Plus proche du level-up, plus la perte est grosse.",
    "Battre un boss de donjon pour la 1ere fois reincarne au niv.1, mais +1 point de stat permanent par niveau a chaque reincarnation.",
    "L'orbe d'Amelioration n'augmente qu'UN SEUL mod aleatoire de +1, pas tous les mods de l'objet.",
    "Les camps dans le donjon restaurent 100% des PV. Ils n'apparaissent pas dans les 3 premiers etages.",
    "La malediction dans le donjon reduit vos PV max de 5 a 15% de facon permanente pour toute la run.",
]

SLOT_MACHINE_SLOTS_CHOIX = [
    "arme", "armure", "casque", "bouclier",
    "anneau", "amulette", "ceinture", "bottes",
]
