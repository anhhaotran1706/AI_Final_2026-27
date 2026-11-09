"""Example plugin (class style): a simple greedy agent written against the public API.

Rule: shoot if the enemy tank/base is in the line of fire, otherwise walk toward the
enemy base, preferring the move that gets closest.
"""
from tank_game import Action
from tank_ai import Agent, first_hit


class GreedyAgent(Agent):
    name = "Greedy (example)"

    def choose_action(self, state):
        me = state.to_move
        tank = state.tanks[me]
        hit = first_hit(state, tank.pos, tank.facing)
        if Action.FIRE in state.legal_actions() and hit and hit[0] in ("tank", "base") \
                and hit[1] != me:
            return Action.FIRE
        bx, by = state.bases[1 - me].pos
        best, best_d = Action.STAY, 10 ** 9
        for a in state.legal_actions():
            if a in (Action.FIRE, Action.STAY):
                continue
            p = state.apply(a).tanks[me].pos            # one-step lookahead via the engine
            d = abs(p[0] - bx) + abs(p[1] - by)
            if d < best_d:
                best, best_d = a, d
        return best