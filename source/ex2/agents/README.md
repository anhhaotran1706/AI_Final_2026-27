# Plugin agents for the Tank Battle arena

Drop a `.py` file in this folder (or load it from the menu with `L`, or pass its path to
`python arena.py a.py b.py`). One of the following is enough:

| Style | What the file defines |
|---|---|
| Instance | `AGENT = MyAgent()` |
| Factory | `def create_agent(): return MyAgent()` |
| Class | `class MyAgent(Agent)` (or any class with `choose_action(self, state)`), no-argument constructor |
| Function | `def choose_action(state): ...` |

`choose_action(state)` receives a `tank_game.GameState` (a private copy) and must return a
`tank_game.Action` for the player to move (`state.to_move`: 0 = MAX/blue, 1 = MIN/red).

Useful API: `state.legal_actions()`, `state.apply(action)` (returns a new state),
`state.is_terminal()`, `state.utility()` (from MAX's view), `state.tanks`, `state.bases`,
`state.walls`, `state.bullets`, `state.key()`, and `tank_ai.first_hit(...)`.

Rules enforced by the arena: time limit per move (default 3 s) -> move replaced by STAY;
exceptions or invalid return values -> STAY; the agent must work for BOTH sides.
Files whose name starts with `_` are ignored.