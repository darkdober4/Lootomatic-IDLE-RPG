import json
import os

SAVE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "saves")


def sauvegarder(player, enemy, filename="sauvegarde.json"):
    os.makedirs(SAVE_DIR, exist_ok=True)
    data = {
        "player": player.to_dict(),
        "enemy": enemy.to_dict(),
    }
    path = os.path.join(SAVE_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return True


def charger(filename="sauvegarde.json"):
    from game.models import Player, Enemy
    path = os.path.join(SAVE_DIR, filename)
    if not os.path.exists(path):
        return None, None
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    player = Player.from_dict(data["player"])
    enemy = Enemy.from_dict(data["enemy"])
    return player, enemy


def liste_sauvegardes():
    os.makedirs(SAVE_DIR, exist_ok=True)
    return [f for f in os.listdir(SAVE_DIR) if f.endswith(".json")]
