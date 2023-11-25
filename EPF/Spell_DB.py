Arcane_Cantrips = {
    "acid splash": {
        "complex": True,
        "category": "spell",
        "title": "Acid Splash",
        "lvl": 0,
        "traits": ["acid", "attack", "cantrip", "evocation"],
        "type": {
            "value": "attack",
        },
        "effect": {"success": "1d6+1 acid", "critical success": "1d6+1 acid, pd 1 acid / dc15 flat"},
        "heighten": {
            "set": {
                3: {"success": "1d6+scmod+1 acid", "critical success": "1d6+scmod+1 acid, pd 2 acid / dc15 flat"},
                5: {"success": "2d6+key+2 acid", "critical success": "1d6+scmod+1 acid, pd 3 acid / dc15 flat"},
                7: {"success": "3d6+key+3 acid", "critical success": "3d6+scmod+3 acid, pd 4 acid / dc15 flat"},
                9: {"success": "4d6+key+4 acid", "critical success": "4d6+scmod+4 acid, pd 5 acid / dc15 flat"},
            },
        },
    },
    "ancient dust": {
        "complex": True,
        "category": "spell",
        "title": "Ancient Dust",
        "lvl": 0,
        "traits": ["cantrip", "necromancy", "negative"],
        "type": {"value": "save", "save": "fort", "type": "complex"},
        "effect": {
            "success": "scmod void",
            "failure": "scmod void, pd 1 void / dc15 flat",
            "critical failure": "scmod void, pd 2 void / dc15 flat",
        },
        "heighten": {"interval": 2, "effect": "1d6 void, hpd 1 void"},
    },
    "chill touch": [
        {
            "complex": True,
            "category": "spell",
            "title": "Chill Touch (Living)",
            "lvl": 0,
            "traits": ["cantrip", "necromancy", "negative"],
            "type": {"value": "save", "save": "fort", "type": "basic"},
            "effect": {
                "failure": "1d4+key void",
                "critical failure": "1d4+scmod void, off-guard 1 unit: round auto flex myturn",
            },
            "heighten": {"interval": 1, "effect": "1d4 void"},
        },
        {
            "complex": True,
            "category": "spell",
            "title": "Chill Touch (Undead)",
            "lvl": 0,
            "traits": ["cantrip", "necromancy", "negative"],
            "type": {"value": "save", "save": "fort", "type": "complex"},
            "effect": {
                "failure": "off-guard 1 unit: round auto flex myturn",
                "critical failure": "fleeing 1 unit: round auto, off-guard 1 unit: round auto flex myturn",
            },
            "heighten": {"interval": 30, "effect": ""},
        },
    ],
}
