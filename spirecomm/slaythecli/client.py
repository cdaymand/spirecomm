#!/usr/bin/env python3

import os
import asyncio
import threading
import json
import readline
import pprint
import time

from spirecomm.spire.game import Game
from spirecomm.spire.screen import ScreenType
from spirecomm.spire.screen import RewardType
from spirecomm.spire.map import Node
from spirecomm.spire.card import CardRarity
from spirecomm.slaythecli.utils.command_helper import CommandHelper
from prettytable import PrettyTable
from termcolor import colored
from textwrap import fill


readline.parse_and_bind('tab: complete')
readline.parse_and_bind('set editing-mode vi')


CARD_RARITY_COLOR = {
    CardRarity.UNCOMMON: "blue",
    CardRarity.RARE: "yellow",
    CardRarity.CURSE: "magenta"
}

ORB_COLOR = {
    "Lightning": "yellow",
    "Dark": "magenta",
    "Frost": "blue",
    "Plasma": "Orange"
}


def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


class SlayTheSpireClient(threading.Thread):
    def __init__(self, ip, port):
        self.ready_for_command = threading.Event()
        self.last_update_time = None
        self.reader = None
        self.writer = None
        self.ip = ip
        self.port = port
        self.game_is_ready = None
        self.last_error = None
        self.in_game = None
        self.last_game_state = None
        self.communication_state = None
        self.available_commands = []
        self.current_node = (0, -1)
        super().__init__()

    def run(self):
        loop = asyncio.new_event_loop()
        loop.run_until_complete(self.main())

    def update_game_state(self, message):
        try:
            self.communication_state = json.loads(message)
        except json.decoder.JSONDecodeError:
            return
        self.last_error = self.communication_state.get("error", None)
        self.game_is_ready = self.communication_state.get("ready_for_command")
        if self.game_is_ready:
            self.available_commands = self.communication_state.get("available_commands") or []
        if self.last_error is None:
            self.in_game = self.communication_state.get("in_game")
            if self.in_game:
                self.last_game_state = Game.from_json(self.communication_state.get("game_state"), self.available_commands)
            else:
                self.last_game_state = None
            self.display_state()
        else:
            print(colored(self.last_error, "red"))

    def show_cards(self, cards, shop=False):
        COLUMN_NUMBER = 5
        if not cards:
            print("No card")
            return
        for chunk in chunks(cards, COLUMN_NUMBER):
            cards_table = PrettyTable(header=False)
            cards = []
            for card in chunk:
                name = card.name
                if card.rarity in CARD_RARITY_COLOR:
                    name = colored(name, CARD_RARITY_COLOR[card.rarity])
                cards.append('\n'.join([f"Cost: {card.cost}",
                                        f"Rarity: {card.rarity.name}",
                                        f"Name: {name}",
                                        f'Misc: {card.misc}',
                                        f"Description: {card.description}",
                                        f"Price: {card.price}" if shop else ""]))
            cards_table.add_row(cards)
            print(cards_table)

    def display_combat(self):
        game = self.last_game_state
        combat_row = []
        energy = str(game.player.energy) if game.player.energy > 0 else colored(game.player.energy, "red")
        damage_expected = -1 * game.player.block
        for monster in game.monsters:
            if monster.current_hp > 0:
                damage_expected += max(monster.move_adjusted_damage * monster.move_hits, 0)
        damage_expected = max(damage_expected, 0)
        if damage_expected > 0:
            damage_expected = colored(damage_expected, "red")
        else:
            damage_expected = colored(damage_expected, "green")

        combat_row.append("\n".join([
            f'HP: {game.player.current_hp}/{game.player.max_hp}',
            f'Block: {game.player.block}',
            f'Damage expected: {damage_expected}',
            f'Energy: {energy}',
            'Powers: [{}]'.format("\n".join([f"{power.power_name}({power.amount})," for power in game.player.powers])),
        ]))
        combat_table = PrettyTable(header=False)
        i = 0
        for monster in game.monsters:
            if monster.current_hp > 0:
                combat_row.append("\n".join([
                    f'{i}: {monster.name}',
                    f'HP: {monster.current_hp}/{monster.max_hp}',
                    f'Intent: {monster.intent.name}',
                    f'Block: {monster.block}',
                    'Powers: [{}]'.format("\n".join([f"{power.power_name}({power.amount})," for power in monster.powers])),
                    f'Damage: {monster.move_adjusted_damage}',
                    f'Hits: {monster.move_hits}']))
            i += 1
        combat_table.add_row(combat_row)
        print(combat_table)
        if game.player.orbs:
            orbs = ' '.join([f'[{colored(orb.name, ORB_COLOR.get(orb.name))} {orb.passive_amount}({orb.evoke_amount})]' for orb in game.player.orbs])
            print(f"Orbs: {orbs}")
        self.show_cards(game.hand)

    def display_card_reward(self):
        self.show_cards(self.last_game_state.screen.cards)

    def display_event(self):
        game = self.last_game_state
        print(f'Event: {game.screen.event_name}')
        print()
        print(fill(game.screen.body_text, 80))
        print()
        i = 0
        for option in game.screen.options:
            print(f"{option.text} (disabled:{option.disabled})")
            i += 1
        print()

    def display_game(self):
        game = self.last_game_state
        print(f"Act boss: {game.act_boss}")
        print(f"Ascension Level: {game.ascension_level}")
        print(f"Seed: {game.seed}")
        print(f"HP: {game.current_hp}/{game.max_hp}")
        print(f"Relics: {[relic.name for relic in game.relics]}")
        print(f"Potions: {[potion.name for potion in game.potions]}")
        print(f"Gold: {self.last_game_state.gold}")
        if game.in_combat:
            self.display_combat()
        if game.screen_type == ScreenType.CARD_REWARD:
            self.display_card_reward()
        elif game.screen_type == ScreenType.MAP:
            self.display_map()
        elif game.screen_type == ScreenType.EVENT:
            self.display_event()
        elif game.screen_type == ScreenType.SHOP_SCREEN:
            self.display_shop()
        elif game.screen_type == ScreenType.GAME_OVER:
            self.display_game_over()
        elif game.screen_type == ScreenType.COMBAT_REWARD:
            self.display_reward()

    def display_reward(self):
        screen = self.last_game_state.screen
        print("Reward:")
        for reward in screen.rewards:
            if reward.reward_type == RewardType.STOLEN_GOLD:
                print(f"Stolen gold: {reward.gold}")
            elif reward.reward_type == RewardType.GOLD:
                print(f"Gold: {reward.gold}")
            elif reward.reward_type == RewardType.POTION:
                print(f"Potion: {reward.potion.name}")
            elif reward.reward_type == RewardType.RELIC:
                print(f"Relic: {reward.relic.name}")

    def display_shop(self):
        screen = self.last_game_state.screen
        print("Welcome to the shop")
        self.show_cards(screen.cards, shop=True)
        print()
        print(f"Relics: {[f'{relic.name} (Price: {relic.price})' for relic in screen.relics]}")
        print(f"Potions: {[f'{potion.name} (Price: {potion.price})' for potion in screen.potions]}")
        if screen.purge_available:
            print(f"Purge cost: {screen.purge_cost}")

    def display_game_over(self):
        screen = self.last_game_state.screen
        if screen.victory:
            print("You win, perfect! :)")
        else:
            print("Game over :'(")
        print(f"Score: {screen.score}")

    def display_state(self):
        if self.last_game_state:
            self.display_game()

    async def main(self):
        self.reader, self.writer = await asyncio.open_connection(
            self.ip, self.port)
        self.send_command("state")
        await self.wait_for_message()

    async def wait_for_message(self):
        message = await self.reader.readline()
        message = message.decode()
        if not message:
            self.close_connection()
            return
        self.update_game_state(message)
        if self.last_error:
            self.send("state")
        else:
            self.last_update_time = time.time()
            self.ready_for_command.set()
        await self.wait_for_message()

    def send(self, command):
        self.ready_for_command.clear()
        self.writer.write(command.encode() + b'\n')

    def send_command(self, command):
        if not command:
            return
        if command.startswith("debug"):
            pp = pprint.PrettyPrinter(indent=4)
            command = command.split()
            if len(command) == 1:
                pp.pprint(self.last_game_state.__dict__)
            else:
                try:
                    pp.pprint(getattr(self.last_game_state, command[1]).__dict__)
                except Exception:
                    print("Attribute doesn't exist here")
        elif command == "map":
            self.display_map()
        elif command[0].isdigit():
            if "play" in self.available_commands:
                self.send('play ' + command)
            elif "choose" in self.available_commands:
                self.send('choose ' + command)
        elif command == "deck" and self.last_game_state:
            self.show_cards(self.last_game_state.deck)
        elif command in ["draw_pile",
                         "discard_pile",
                         "exhaust_pile"] and "play" in self.available_commands:
            self.show_cards(getattr(self.last_game_state, command))
        elif "choose" in self.available_commands and command in self.last_game_state.choice_list:
            self.send('choose ' + command)
        else:
            self.send(command)

    def display_map(self):
        height = 30
        width = 25
        stairs = 15
        if self.last_game_state:
            current_node = getattr(self.last_game_state.screen, "current_node", Node(0, -1, None))
            sts_map = [[" "] * width for i in range(height)]
            for i in range(stairs):
                for node in self.last_game_state.map.nodes[i].values():
                    symbol = node.symbol
                    if node.x == current_node.x and node.y == current_node.y:
                        symbol = colored(symbol, "green")
                    sts_map[(stairs-i) * 2 - 1][6 + node.x * 3] = symbol
                    for children in node.children:
                        if children.x < node.x:
                            sts_map[(stairs-i) * 2 - 2][5 + node.x * 3] = "\\"
                        elif children.x == node.x:
                            sts_map[(stairs-i) * 2 - 2][6 + node.x * 3] = "|"
                        else:
                            sts_map[(stairs-i) * 2 - 2][7 + node.x * 3] = "/"
            i = height - 1
            for line in sts_map:
                header = "   "
                if i % 2 == 0:
                    header = f"{i // 2:2}:"
                print(header + "".join(line))
                i -= 1
            print()

    def close_connection(self):
        self.writer.close()


def get_input(client, verbose):
    command_helper = CommandHelper(client, verbose)
    command_helper.receive_commands()


def main(ip, port, verbose):
    os.system("clear")
    client = SlayTheSpireClient(ip=ip, port=port)
    client.start()
    get_input(client, verbose)
    client.join()
