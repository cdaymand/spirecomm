import logging
import sys

from PyInquirer import prompt

logging.basicConfig(stream=sys.stdout, level=logging.ERROR)


class CommandHelper:
    def __init__(self, client, verbose):
        self.client = client
        self.last_update_time = None
        self.logger = logging.getLogger(__name__)
        if verbose:
            self.logger.setLevel("DEBUG")

    def get_available_commands(self):
        available_commands = list(self.client.available_commands)
        other_commands = []
        for command in ('key', 'click', 'wait'):
            if command in available_commands:
                available_commands.remove(command)
                other_commands.append(command)
        available_commands.append('other')
        if self.client.in_game:
            other_commands.extend(['map', 'deck'])
        if "play" in self.client.available_commands:
            other_commands.extend(['draw', 'discard', 'exhaust'])
        other_commands.append('back')
        available_commands.append('quit')
        return (available_commands, other_commands)

    def send(self, command):
        if not command:
            return
        self.logger.debug("Send command to server: '%s'", command)
        self.client.send(command)

    def start(self):
        game_prompt = [
            {
                'type': 'list',
                'name': 'character',
                'message': 'Choose your character',
                'choices': ["Ironclad", "Silent", "Defect"]
            },
            {
                'type': 'input',
                'name': 'ascension_level',
                'message': 'Ascension'
            },
            {
                'type': 'input',
                'name': 'seed',
                'message': 'Seed'
            }
        ]
        game = self.prompt(game_prompt)
        if not game or not game.get('character') or not game.get('ascension_level'):
            return
        self.send(f"start {game['character']} {game['ascension_level']} {game.get('seed', '')}")

    def play(self):
        game = self.client.last_game_state
        cards = [card.name for card in game.hand]
        card_prompt = [
            {
                'type': 'list',
                'name': 'card',
                'message': 'Card to play:',
                'choices': list(set(cards)) + ['back']
            }
        ]
        card = self.prompt(card_prompt).get("card")
        if not card or card == "back":
            return
        index = cards.index(card)
        target = ""
        if game.hand[index].has_target:
            targets = []
            i = 0
            for monster in game.monsters:
                if monster.current_hp > 0:
                    targets.append(f"{i}: {monster.name}")
                i += 1
            monster_prompt = [
                {
                    'type': 'list',
                    'name': 'target',
                    'message': 'Target:',
                    'choices': targets + ['back']
                }
            ]
            target = self.prompt(monster_prompt).get("target")
            if not target:
                return
            target = target.split(':')[0]
            if target == 'back':
                self.play()
                return
        self.send(f"play {index + 1} {target}")

    def choose(self):
        option_prompt = [
            {
                'type': 'list',
                'name': 'option',
                'message': 'Choose',
                'choices': self.client.last_game_state.choice_list + ['back']
            }
        ]
        option = self.prompt(option_prompt).get('option')
        if not option or option == 'back':
            return
        if option == "potion" and self.client.last_game_state.are_potions_full():
            print("You need to discard a potion!")
            return
        index = self.client.last_game_state.choice_list.index(option)
        self.send(f"choose {index}")

    def map(self):
        self.client.display_map()

    def deck(self):
        self.client.show_cards(self.client.last_game_state.deck)

    def draw(self):
        self.client.show_cards(self.client.last_game_state.draw_pile)

    def discard(self):
        self.client.show_cards(self.client.last_game_state.discard_pile)

    def exhaust(self):
        self.client.show_cards(self.client.last_game_state.exhaust_pile)

    def potion(self):
        game = self.client.last_game_state
        potions = [potion.name for potion in game.potions if potion.name != "Potion Slot"]
        potion_prompt = [
            {
                'type': 'list',
                'name': 'action',
                'message': 'Action:',
                'choices': ["use", "discard"]
            },
            {
                'type': 'list',
                'name': 'potion',
                'message': 'Potion',
                'choices': list(set(potions)) + ['back']
            }
        ]
        potion_command = self.prompt(potion_prompt)
        if not potion_command or not potion_command.get("action") or not potion_command.get('potion'):
            return
        potion = potion_command['potion']
        if potion == 'back':
            return
        index = potions.index(potion)
        target = ""
        if potion_command['action'] == 'use' and game.potions[index].requires_target:
            targets = []
            i = 0
            for monster in game.monsters:
                if monster.current_hp > 0:
                    targets.append(f"{i}: {monster.name}")
                i += 1
            monster_prompt = [
                {
                    'type': 'list',
                    'name': 'target',
                    'message': 'Target:',
                    'choices': targets + ['back']
                }
            ]
            target = self.prompt(monster_prompt).get("target")
            if not target:
                return
            target = target.split(':')[0]
            if target == 'back':
                self.potion()
                return
        self.send(f"potion {potion_command['action']} {index} {target}")

    def prompt(self, prompt_dict):
        if self.last_update_time != self.client.last_update_time:
            return {}
        result = prompt(prompt_dict)
        result = result if result is not None else {}
        return result

    def receive_commands(self):
        command = None
        while command != "quit":
            self.client.ready_for_command.wait()
            # Ensure that no new update will arrive
            self.last_update_time = self.client.last_update_time
            command_list, other_commands = self.get_available_commands()
            if "choose" in command_list:
                choices = ', '.join([c for c in self.client.last_game_state.choice_list])
                print(f"Choices available: {choices}")
            command_prompt = [
                {
                    'type': 'list',
                    'name': 'command',
                    'message': 'Command:',
                    'choices': command_list,
                }
            ]
            command = self.prompt(command_prompt).get("command")
            self.logger.debug("Command received: %s", command)
            if not command:
                continue
            if command == 'other':
                print(f"Other available commands: {', '.join([c for c in other_commands])}")
                command_prompt = [
                    {
                        'type': 'input',
                        'name': 'command',
                        'message': 'Command:',
                    }
                ]
                command = self.prompt(command_prompt).get("command")
                if not command or command == 'back':
                    continue
            if hasattr(self, command):
                getattr(self, command)()
            else:
                self.send(command)
