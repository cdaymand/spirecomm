from enum import Enum
from textwrap import fill
from termcolor import colored


class CardType(Enum):
    ATTACK = 1
    SKILL = 2
    POWER = 3
    STATUS = 4
    CURSE = 5


class CardRarity(Enum):
    BASIC = 1
    COMMON = 2
    UNCOMMON = 3
    RARE = 4
    SPECIAL = 5
    CURSE = 6


class Card:
    def __init__(self, card_id, name, card_type, rarity, upgrades=0, has_target=False, cost=0, uuid="", misc=0, price=0, is_playable=False, exhausts=False, description=None):
        self.card_id = card_id
        self.name = name
        self.type = card_type
        self.rarity = rarity
        self.upgrades = upgrades
        self.has_target = has_target
        self.cost = cost
        self.uuid = uuid
        self.misc = misc
        self.price = price
        self.is_playable = is_playable
        self.exhausts = exhausts
        self.description = description

    @classmethod
    def from_json(cls, json_object):
        description = json_object.get("raw_description", "")
        description = description.replace("NL", "\n")
        damage = f"{json_object['base_damage']}" if json_object['damage'] == -1 else f"{json_object['damage']}"
        block = f"{json_object['base_block']}" if json_object['block'] == -1 else f"{json_object['block']}"
        magic_number = f"{json_object['base_magic_number']}" if json_object['damage'] == -1 else f"{json_object['magic_number']}"
        description = description.replace("!D!", colored(damage, "red"))
        description = description.replace("!B!", colored(block, "green"))
        description = description.replace("!M!", colored(magic_number, "yellow"))
        description = fill(description, 15)
        cost = json_object["cost"]
        if cost == 0:
            cost = colored(f'{cost}', "green")
        return cls(
            card_id=json_object["id"],
            name=json_object["name"],
            card_type=CardType[json_object["type"]],
            rarity=CardRarity[json_object["rarity"]],
            upgrades=json_object["upgrades"],
            has_target=json_object["has_target"],
            cost=cost,
            uuid=json_object["uuid"],
            misc=json_object.get("misc", 0),
            price=json_object.get("price", 0),
            is_playable=json_object.get("is_playable", False),
            exhausts=json_object.get("exhausts", False),
            description=description
        )

    def __eq__(self, other):
        return self.uuid == other.uuid
