"""Example plugin (function style): the simplest possible plugin.
Only a function choose_action(state) -> Action is required."""
import random
from tank_game import Action

_rng = random.Random(0)


def choose_action(state):
    acts = state.legal_actions()
    if Action.FIRE in acts and _rng.random() < 0.5:
        return Action.FIRE
    return _rng.choice(acts)