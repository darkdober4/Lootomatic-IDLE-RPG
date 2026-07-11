# Lootomatic-IDLE-RPG
    Lootomatic est un idle RPG web avec combat automatique 1v1, loot procedural et progression infinie.
    Farm des ennemis, equipe 9 slots d'equipement, modifie tes objets avec des orbes, et enchaîne les donjons pour te reincarner
    plus fort a chaque boss vaincu.
Help me buy a new pc https://gofund.me/4f2d4ae1f

Start the game with a terminal using python on app.py

*python app.py

# ⚔️ Lootomatic — Idle RPG

**v0.5.0** — Un idle RPG web avec combat automatique, loot procédural, donjons et craft.

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![Flask](https://img.shields.io/badge/Flask-3.x-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

## 📋 Description

Lootomatic est un jeu de type idle RPG jouable dans le navigateur. Le personnage combat automatiquement des vagues d'ennemis, accumule du loot, monte en niveau et explore des donjons procéduraux. Le jeu tourne en continu — même quand on ne fait rien, le combat avance.

## ✨ Fonctionnalités

- **Combat en temps réel** — Système de ticks (1s) avec attaque joueur et ennemi indépendantes
- **Système de loot** — Objets générés procéduralement avec 5 raretés (Commun → Mythique) et modificateurs aléatoires
- **9 slots d'équipement** — Arme, armure, casque, bouclier, anneau, amulette, ceinture, bottes, artefact
- **12 sorts (artefacts)** — Déclenchés par stacks : poison, surge de flammes, vol d'âme, exécution, etc.
- **Orbes de craft** — 5 types (amélioration, altération, échange, fragilité, polymorphie) avec risque de corruption
- **Enchantement** — Jusqu'à +10, avec chance décroissante et risque de corruption
- **Donjons procéduraux** — 5 chapitres, 20 étages, map à choix multiples (combat, boss, camp, événement, relique)
- **22+ reliques** — Buffs et debuffs permanents pour la run de donjon
- **Machine à sous** — Mise des jetons pour gagner du loot légendaire+
- **Chaudron magique** — Fusion de 3 objets en un nouvel objet
- **Sauvegarde / Chargement** — JSON local dans le dossier `saves/`
- **Statistiques de session** — Kills, dégâts, record sans mort, etc.

## 🚀 Installation

```bash
# Cloner le dépôt
git clone <[repo-url](https://github.com/darkdober4/Lootomatic-IDLE-RPG.git)>
cd Lootomatic-IDLE-RPG-v.0.5.0/Lootomatic

# Créer un environnement virtuel (recommandé)
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows

# Installer les dépendances
pip install flask
```

## 🎮 Lancement

```bash
python app.py
```

Le jeu s'ouvre automatiquement dans le navigateur à l'adresse `http://localhost:5000`.

## 🏗️ Structure du projet

```
Lootomatic/
├── app.py              # Serveur Flask + routes API
├── config.py           # Constantes de jeu (stats, loot, sorts, donjon, etc.)
├── sim_test.py         # Script de test / simulation
├── game/
│   ├── models.py       # Classes Player, Enemy, Item
│   ├── combat.py       # Logique de combat (ticks, dégâts, critiques, esquive)
│   ├── dungeon.py      # Génération procédurale de donjons et événements
│   ├── spells.py       # Système de sorts à stacks
│   ├── relics.py       # Tirage et application des reliques
│   └── save.py         # Sauvegarde / chargement JSON
├── templates/
│   └── index.html      # Interface utilisateur (HTML)
├── static/
│   ├── css/style.css   # Styles
│   └── js/
│       ├── game.js     # Logique cliente principale
│       ├── animations.js # Animations et effets visuels
│       └── dungeon.js  # Interface du donjon
└── saves/              # Fichiers de sauvegarde JSON
```

## 🎯 Mécaniques de jeu

### Combat
- Chaque tick (1 seconde), le joueur et l'ennemi attaquent
- Les dégâts sont calculés avec ATK, DÉF (réduction : `DEF / (DEF + 100)`), critiques, esquive et contre-attaques
- La victoire restaure les PV au maximum
- La mort fait perdre 1% de l'XP accumulée

### Progression
- **XP** : croît de 15% par niveau (`50 × 1.15^n`)
- **Points de stats** : 2 par niveau (+ bonus pour chaque boss de donjon battu)
- **Stats** : PV Max, ATQ, DÉF, VIT, Critique, Esquive, Loot, Contre, Vit. Attaque, Sorts

### Loot & Craft
- **Orbes** : amélioration (+1 mod), altération (ajoute un mod + chance rareté↑), échange (swap 2 mods), fragilité (+50% un mod, -1 mod), polymorphie (change le slot)
- **Corruption** : certains craft peuvent corrompre l'objet — il ne peut plus être modifié
- **Enchantement** : +10% de stats par niveau, risque d'échec croissant (+10 = 10% de chance)

### Donjon
- Map procédurale avec 7 colonnes × 20 étages
- Types de nœuds : combat, boss, camp (soin complet), événement, relique
- Battre un boss réincarne au niveau 1 avec +1 point de stat permanent par niveau

## 🛠️ Technologies

| Couche | Technologie |
|--------|-------------|
| Backend | Python 3.10+, Flask |
| Frontend | HTML5, CSS3, JavaScript vanilla |
| Sauvegarde | JSON (fichiers locaux) |

## 📄 License

MIT
