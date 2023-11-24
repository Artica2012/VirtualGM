Spell_DB = {
    "gust of wind": {
        "title": "gust of wind",
        "lvl": 1,
        "type": {
            "value": "save",
            "save": "fort",
        },
        "effect": {
            "critical success": None,
            "success": None,
            "failure": "prone",
            "critical failure": "prone, 2d6 bludgeoning",
        },
        "heighten": None,
    },
    "scorching blast": {
        "title": "scorching blast",
        "lvl": 1,
        "type": {
            "value": "attack",
        },
        "effect": {
            "critical success": "(2d8+Xd8)*2 fire, pd 1d6+(2X) fire / DC15 flat,",
            "success": "2d8+Xd8 fire",
            "failure": None,
            "critical failure": None,
        },
        "heighten": "X",
    },
}
