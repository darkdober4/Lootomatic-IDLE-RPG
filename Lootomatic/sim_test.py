import requests
import time

BASE = "http://127.0.0.1:5000"
kills = 0
morts = 0
loots = 0
orbes = 0

for tick in range(500):
    r = requests.post(f"{BASE}/api/combat_tick").json()
    if r.get("resultat") == "victoire":
        kills += 1
        rec = r.get("recompenses", {})
        if "loots" in rec:
            loots += len(rec["loots"])
        if "orbes" in rec:
            orbes += len(rec["orbes"])
    elif r.get("resultat") == "defaite":
        morts += 1
    time.sleep(0.02)

s = requests.get(f"{BASE}/api/state").json()
p = s["player"]
e = s["enemy"]

print("=== SIMULATION 500 TICKS ===")
print(f"Joueur : Niveau {p['niveau']} | XP {p['xp']}/{p['xp_max']}")
print(f"HP : {p['hp']}/{p['hp_max']}")
print(f"Stats : ATQ={p['stats']['atk']} DEF={p['stats']['def']} VIT={p['stats']['vit']}")
print(f"Points dispo : {p['points_stats']}")
print(f"Or : {p['or']}")
print(f"Kills : {kills} | Morts : {morts}")
print(f"Loots : {loots} | Orbes : {orbes}")
print(f"Max niveau debloque : {s['max_niveau_debloque']}")
print(f"Ennemi actuel : {e['nom']} niv.{e['niveau']} (boss={e['boss']})")
print(f"Objets en inventaire : {sum(len(c) for c in p['inventaire'])}")

orbe_counts = {}
for coffre in p["inventaire"]:
    for item in coffre:
        if item.get("slot") == "orbe":
            nom = item["nom"]
            orbe_counts[nom] = orbe_counts.get(nom, 0) + item.get("quantite", 1)
if orbe_counts:
    print(f"Orbes : {orbe_counts}")
