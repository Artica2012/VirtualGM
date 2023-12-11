import logging

import d20

import EPF.EPF_Character


async def damage_calc_resist(dmg_roll, dmg_type, target: EPF.EPF_Character.EPF_Character, weapon=None):
    logging.info("damage_calc_resist")
    if target.resistance == {}:
        return dmg_roll
    dmg = dmg_roll
    if dmg_type is None:
        return dmg_roll
    dmg_type = dmg_type.lower()
    # print(target.resistance)
    # print(dmg_type)
    # print(dmg_roll)

    if weapon is not None:
        if "traits" in weapon.keys():
            if "concussive" in weapon["traits"]:
                if "piercing" in target.resistance.keys():
                    dmg_type = "bludgeoning"
                elif "bludgeoning" in target.resistance.keys():
                    dmg_type = "piercing"
                elif "piercing" in target.resistance.keys() and "bludgeoning" in target.resistance.keys():
                    try:
                        p_resist = target.resistance["piercing"]["r"]
                    except KeyError:
                        p_resist = 0

                    try:
                        b_resist = target.resistance["bludgeoning"]["r"]
                    except KeyError:
                        b_resist = 0

                    if p_resist > b_resist:
                        dmg_type = "bludgeoning"
                    else:
                        dmg_type = "piercing"
                elif "piercing" in target.resistance.keys():
                    dmg_type = "bludgeoning"
                elif "bludgeoning" in target.resistance.keys():
                    dmg_type = "piercing"
        try:
            mat = weapon["mat"].lower()
        except KeyError:
            mat = ""
    else:
        mat = ""
    # print(f"Mat: {mat}")

    if "physical" in target.resistance.keys():
        # print("Physical Resistance")
        if (
            dmg_type.lower() == "slashing"
            or dmg_type.lower() == "piercing"
            or dmg_type.lower() == "bludgeoning"
            or dmg_type.lower() == "precision"
        ):
            dmg_type = "physical"
            # print(dmg_type)

    if mat != "":
        exception_list = [mat]
        dmg_list = [dmg_type.lower(), "all-damage", mat]
    else:
        dmg_list = [dmg_type.lower(), "all-damage"]
        exception_list = []
    if weapon is not None:
        # print(weapon["runes"])
        if "Ghost Touch" in weapon["runes"]:
            exception_list.append("ghost-touch")
            dmg_list.append("ghost-touch")

    # print(dmg_list)
    # print(exception_list)
    # Remaster Conversion Code
    if dmg_type.lower() == "negative":
        dmg_list.append("void")
    elif dmg_type.lower() == "void":
        dmg_list.append("negative")
    elif dmg_type.lower() == "positive":
        dmg_list.append("vitality")
    elif dmg_type.lower() == "vitality":
        dmg_list.append("positive")

    for item in dmg_list:  # This is completely rewritten. It might be broken
        # print(item)
        if item in target.resistance.keys():
            if "r" in target.resistance[item].keys():
                # print(target.resistance[item].keys())
                exempt = False
                if "except" in target.resistance[item].keys():
                    # print(target.resistance[item]["except"])

                    for e in exception_list:
                        if e in target.resistance[item]["except"]:
                            exempt = True
                            # print(e, "exempt")
                if not exempt:
                    # print('not exempt')
                    # print(dmg)
                    dmg = dmg - target.resistance[item]["r"]
                    # print(dmg)
                    if dmg < 0:
                        dmg = 0

            if "w" in target.resistance[item]:
                exempt = False
                if "except" in target.resistance[item].keys():
                    for e in exception_list:
                        if e in target.resistance[item]["except"]:
                            exempt = True
                if not exempt:
                    dmg = dmg + target.resistance[item]["w"]

            if "i" in target.resistance[item]:
                if "except" in target.resistance[item].keys():
                    exempt = False
                    for e in exception_list:
                        if e in target.resistance[item]["except"]:
                            exempt = True
                    if not exempt:
                        dmg = 0

    # print("DMG:", dmg)
    return dmg


async def roll_dmg_resist(
    Character_Model: EPF.EPF_Character.EPF_Character,
    Target_Model: EPF.EPF_Character.EPF_Character,
    attack: str,
    crit: bool,
    flat_bonus="",
    dmg_type_override=None,
):
    """
    Rolls damage and calculates resists
    :param Character_Model:
    :param Target_Model:
    :param attack:
    :param crit:
    :return: Tuple of damage_output_string(string), total_damage(int)
    """
    logging.info("roll_dmg_resist")
    dmg_output = []
    # Roll the critical damage and apply resistances
    damage_roll = d20.roll(await Character_Model.weapon_dmg(attack, crit=crit, flat_bonus=flat_bonus))
    weapon = await Character_Model.get_weapon(attack)
    if dmg_type_override == "":
        dmg_type_override = None
    if dmg_type_override is not None:
        base_dmg_type = dmg_type_override
    else:
        base_dmg_type = weapon["dmg_type"]
    total_damage = await damage_calc_resist(damage_roll.total, base_dmg_type, Target_Model, weapon=weapon)
    dmg_output_string = f"{damage_roll}"
    output = {"dmg_output_string": dmg_output_string, "dmg_type": base_dmg_type}
    dmg_output.append(output)

    # Check for bonus damage
    if "bonus" in Character_Model.character_model.attacks[attack]:
        if crit:
            crit_mod = "*2"
        else:
            crit_mod = ""
        for item in Character_Model.character_model.attacks[attack]["bonus"]:
            bonus_roll = d20.roll(f"({item['damage']}){crit_mod}")
            bonus_damage = await damage_calc_resist(bonus_roll.total, item["dmg_type"], Target_Model)
            dmg_output_string = f"{dmg_output_string}+{bonus_roll}"
            total_damage += bonus_damage
            output = {"dmg_output_string": bonus_roll, "dmg_type": item["dmg_type"]}
            dmg_output.append((output))
    # print(dmg_output_string, total_damage)

    # Hardness
    try:
        total_damage = total_damage - Target_Model.character_model.bonuses["other"]["hardness"]
    except KeyError:
        # print("No Hardness")
        pass

    return dmg_output, total_damage


async def roll_persist_dmg(
    Target_Model: EPF.EPF_Character.EPF_Character,
    roll: str,
    dmg_type_override=None,
):
    logging.info("roll_dmg_resist")
    dmg_output = []
    # Roll the critical damage and apply resistances
    damage_roll = d20.roll(roll)
    if dmg_type_override == "":
        dmg_type_override = None
    if dmg_type_override is not None:
        base_dmg_type = dmg_type_override
    else:
        base_dmg_type = None

    total_damage = await damage_calc_resist(damage_roll.total, base_dmg_type, Target_Model)
    dmg_output_string = f"{damage_roll}"
    output = {"dmg_output_string": dmg_output_string, "dmg_type": base_dmg_type}
    dmg_output.append(output)

    # print(dmg_output_string, total_damage)
    return dmg_output, total_damage
