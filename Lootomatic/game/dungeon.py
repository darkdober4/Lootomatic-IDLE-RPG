import random
from config import (
    DONJON_COLS, DONJON_ETAGES, DONJON_NODES_MIN, DONJON_NODES_MAX,
    DONJON_BOSS_MULT, DONJON_NODE_PROBS, DONJON_EVENEMENTS,
    DONJON_RELICS, DONJON_XP_BOSS, DONJON_JETONS_MIN, DONJON_JETONS_MAX,
    DONJON_ITEMS_RECOMPENSE, DONJON_NIVEAU_PAR_CHAPITRE,
    STAT_ENNEMI_BASE, STAT_ENNEMI_PAR_NIVEAU, NOMS_BOSS, RARITES,
)
from game.models import Enemy, Item
from game.relics import tirage_reliques


class DungeonNode:
    def __init__(self, col, etage, node_type="combat"):
        self.col = col
        self.etage = etage
        self.type = node_type
        self.connections = []
        self.visite = False

    def to_dict(self):
        return {
            "col": self.col,
            "etage": self.etage,
            "type": self.type,
            "connections": self.connections,
            "visite": self.visite,
        }

    @classmethod
    def from_dict(cls, data):
        n = cls(data["col"], data["etage"], data["type"])
        n.connections = data["connections"]
        n.visite = data["visite"]
        return n


def generer_map():
    nodes = {}
    floor_positions = {}

    nb_start = random.randint(DONJON_NODES_MIN, DONJON_NODES_MAX)
    start_cols = sorted(random.sample(range(DONJON_COLS), nb_start))
    for c in start_cols:
        nodes[(c, 0)] = DungeonNode(c, 0, "combat")
    floor_positions[0] = list(start_cols)

    for etage in range(1, DONJON_ETAGES - 1):
        nb = random.randint(DONJON_NODES_MIN, DONJON_NODES_MAX)
        cols = sorted(random.sample(range(DONJON_COLS), nb))
        floor_positions[etage] = cols
        for c in cols:
            nodes[(c, etage)] = DungeonNode(c, etage)

    for etage in range(1, DONJON_ETAGES - 1):
        prev_cols = sorted(floor_positions[etage - 1])
        curr_cols = sorted(floor_positions[etage])
        connected = set()

        for pc in prev_cols:
            cc = min(curr_cols, key=lambda c: abs(c - pc))
            conn = [cc, etage]
            if conn not in nodes[(pc, etage - 1)].connections:
                nodes[(pc, etage - 1)].connections.append(conn)
            connected.add(cc)

        for pc in prev_cols:
            candidates = sorted(curr_cols, key=lambda c: abs(c - pc))
            for cc in candidates:
                if cc not in connected:
                    conn = [cc, etage]
                    if conn not in nodes[(pc, etage - 1)].connections:
                        nodes[(pc, etage - 1)].connections.append(conn)
                    connected.add(cc)
                    break

        for cc in list(curr_cols):
            if cc not in connected:
                if (cc, etage) in nodes:
                    del nodes[(cc, etage)]
                if cc in floor_positions[etage]:
                    floor_positions[etage].remove(cc)

    boss_col = DONJON_COLS // 2
    nodes[(boss_col, DONJON_ETAGES - 1)] = DungeonNode(boss_col, DONJON_ETAGES - 1, "boss")
    prev_cols = sorted(floor_positions[DONJON_ETAGES - 2])
    for pc in prev_cols:
        conn = [boss_col, DONJON_ETAGES - 1]
        if conn not in nodes[(pc, DONJON_ETAGES - 2)].connections:
            nodes[(pc, DONJON_ETAGES - 2)].connections.append(conn)

    for key, node in nodes.items():
        if node.type == "combat" and node.etage > 0:
            node.type = _assigner_type(node.etage, nodes, key)

    return nodes


def _assigner_type(etage, nodes, key):
    if etage <= 1:
        return "combat"

    probs = dict(DONJON_NODE_PROBS)
    if etage < 4:
        probs["camp"] = 0

    if etage == DONJON_ETAGES - 2:
        probs["camp"] = 0

    parent_types = set()
    for (c, e), n in nodes.items():
        if e == etage - 1 and [key[0], key[1]] in n.connections:
            parent_types.add(n.type)

    types = []
    weights = []
    for t, w in probs.items():
        if w > 0:
            types.append(t)
            weights.append(w)

    if not types:
        return "combat"

    for _ in range(10):
        chosen = random.choices(types, weights=weights, k=1)[0]
        if chosen not in parent_types or len(parent_types) <= 1:
            return chosen

    return random.choices(types, weights=weights, k=1)[0]


def generer_ennemi_donjon(chapitre):
    niveau = DONJON_NIVEAU_PAR_CHAPITRE.get(chapitre, 10 * chapitre)
    enemy = Enemy(niveau=niveau, boss=False)
    return enemy


def generer_boss_donjon(chapitre):
    niveau = DONJON_NIVEAU_PAR_CHAPITRE.get(chapitre, 10 * chapitre)
    boss = Enemy(niveau=niveau, boss=False)
    boss.boss = True
    boss.nom = random.choice(NOMS_BOSS) + f" (Ch.{chapitre})"
    for stat in boss.stats:
        boss.stats[stat] = int(boss.stats[stat] * DONJON_BOSS_MULT)
    boss.hp = boss.stats["hp_max"]
    return boss


def generer_evenement(chapitre):
    types = [e["type"] for e in DONJON_EVENEMENTS]
    poids = [e["poids"] for e in DONJON_EVENEMENTS]
    type_evt = random.choices(types, weights=poids, k=1)[0]

    evt_data = next(e for e in DONJON_EVENEMENTS if e["type"] == type_evt)
    resultat = {"type": type_evt, "description": evt_data["description"]}

    if type_evt == "objet":
        niveau = DONJON_NIVEAU_PAR_CHAPITRE.get(chapitre, 10 * chapitre)
        item = Item(niveau=niveau)
        resultat["item"] = item.to_dict()
        resultat["message"] = f"Vous obtenez : {item.nom} ({item.rarete})"

    elif type_evt == "relique":
        choices = tirage_reliques(nb=1)
        if choices:
            rel = DONJON_RELICS[choices[0]]
            resultat["relique"] = choices[0]
            resultat["message"] = f"Relique obtenue : {rel['nom']} — {rel['description']}"

    elif type_evt == "guérison":
        heal_pct = random.randint(20, 50)
        resultat["heal_pct"] = heal_pct
        resultat["message"] = f"Vous récupérez {heal_pct}% de vos PV max."

    elif type_evt == "teleport":
        resultat["message"] = "Un portail vous téléporte à un autre étage !"

    elif type_evt == "or":
        or_gagne = random.randint(20, 80) * chapitre
        resultat["or"] = or_gagne
        resultat["message"] = f"Vous obtenez {or_gagne} or !"

    elif type_evt == "malédiction":
        perte_pct = random.randint(5, 15)
        resultat["perte_pct"] = perte_pct
        resultat["message"] = f"Malédiction ! Vous perdez {perte_pct}% de vos PV max."

    return resultat


def get_choix_disponibles(nodes, position, etage_actuel):
    if position is None:
        return [(c, e) for (c, e) in nodes if e == 0]

    node = nodes.get(tuple(position))
    if node is None:
        return []

    return [(c, e) for (c, e) in node.connections if (c, e) in nodes]


def nodes_to_dict(nodes):
    return {f"{c},{e}": n.to_dict() for (c, e), n in nodes.items()}


def nodes_from_dict(data):
    nodes = {}
    for key_str, node_data in data.items():
        c, e = key_str.split(",")
        nodes[(int(c), int(e))] = DungeonNode.from_dict(node_data)
    return nodes
