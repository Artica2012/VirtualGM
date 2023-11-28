condition_grammer = """
start: phrase+

phrase: value+ break

value: (WORD | COMBO_WORD) (SIGNED_INT | VARIABLE )  SPECIFIER         -> skill_bonus
    | "init-skill" WORD                                                -> init_skill
    | "hardness" NUMBER                                                -> hardness
    | quoted (WORD | COMBO_WORD) SIGNED_INT SPECIFIER                  -> item_bonus
    | "thp" NUMBER                                                     -> temp_hp
    | (WORD | COMBO_WORD) SPECIFIER NUMBER? ";"?                       -> resistance
    | (WORD | COMBO_WORD) SPECIFIER NUMBER? "e" (WORD | COMBO_WORD)* ";"?              -> resistance_w_exception
    | "stable" NUMBER?                                                 -> stable
    | persist_dmg
    | WORD NUMBER?                                                     -> new_condition

persist_dmg : ("persistent dmg" | "pd") roll_string WORD* ["/" "dc" NUMBER save_string]

modifier: SIGNED_INT

quoted: SINGLE_QUOTED_STRING
    | DOUBLE_QUOTED_STRING

break: ","


roll_string: ROLL (POS_NEG ROLL)* [POS_NEG NUMBER]
!save_string: "reflex" | "fort" | "will" | "flat"

ROLL: NUMBER "d" NUMBER

POS_NEG : ("+" | "-")

DOUBLE_QUOTED_STRING  : /"[^"]*"/
SINGLE_QUOTED_STRING  : /'[^']*'/

SPECIFIER : "c" | "s" | "i" | "r" | "w"
VARIABLE : "+x" | "-x"


COMBO_WORD : WORD (("-" |"_") WORD)+
%import common.ESCAPED_STRING
%import common.WORD
%import common.SIGNED_INT
%import common.NUMBER
%import common.WS
%ignore WS
"""


attack_grammer = """
start: phrase+

phrase: value+ break

value: roll_string WORD                                                -> damage_string
    | persist_dmg
    | (WORD | COMBO_WORD) NUMBER? (duration | unit | auto | stable | flex | target | data | self)*   -> new_condition
    | heighten_persist

persist_dmg : ("persistent dmg" | "pd") roll_string WORD* ["/" "dc" (NUMBER | STAT_VAR) save_string]
heighten_persist: "hpd" roll_string WORD


duration : "duration:" NUMBER
unit : "unit:" WORD
auto: "auto"
data: "data:" SINGLE_QUOTED_STRING
stable: "stable"
flex: "flex"
target: "myturn"
self: "self"

modifier: SIGNED_INT

quoted: SINGLE_QUOTED_STRING
    | DOUBLE_QUOTED_STRING

break: ","


roll_string: (ROLL (POS_NEG ROLL)* (POS_NEG (NUMBER | STAT_VAR))* | STAT_VAR (POS_NEG (NUMBER| STAT_VAR))* | NUMBER)
!save_string: "reflex" | "fort" | "will" | "flat"

ROLL: NUMBER "d" NUMBER

POS_NEG : ("+" | "-")
STAT_VAR : ("str" | "dex" | "con" | "int" | "wis" | "cha" | "lvl" | "dc" | "key"| "scmod")

DOUBLE_QUOTED_STRING  : /"[^"]*"/
SINGLE_QUOTED_STRING  : /'[^']*'/

SPECIFIER : "c" | "s" | "i" | "r" | "w"
VARIABLE : "+x" | "-x" | POS_NEG? "lvl" | (POS_NEG?  ROLL)


COMBO_WORD : WORD (("-" |"_") WORD)+
%import common.ESCAPED_STRING
%import common.WORD
%import common.SIGNED_INT
%import common.NUMBER
%import common.WS
%ignore WS
"""
