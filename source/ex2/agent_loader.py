"""Task 2 - Requirement 3: importing algorithms written by other student groups.

A plugin is a single .py file. The loader accepts ANY of these styles (checked in order):

  1. a module-level variable   AGENT = MyAgent()            (an instance)
  2. a module-level function   create_agent() -> agent      (factory)
  3. a class defined in the file that subclasses tank_ai.Agent, or simply has a
     method choose_action(self, state)   (instantiated with no arguments)
  4. a module-level function   choose_action(state) -> Action

`state` is a tank_game.GameState (a private copy, so a plugin cannot corrupt the game);
the plugin returns a tank_game.Action for the player whose turn it is (state.to_move).
See agents/README.md for the full contract and examples.
"""
import importlib.util
import inspect
import os
import sys
from dataclasses import dataclass
from typing import Callable, List, Optional

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:                  # plugins may `from tank_game import ...`
    sys.path.insert(0, HERE)

from tank_game import Action, GameState                      # noqa: E402
from tank_ai import Agent, RandomAgent, SearchAgent          # noqa: E402

AGENTS_DIR = os.path.join(HERE, "agents")


class AgentLoadError(Exception):
    """Raised when a plugin file cannot be turned into a working agent."""


class FunctionAgent(Agent):
    """Adapter that turns a plain function choose_action(state) into an Agent."""

    def __init__(self, fn: Callable, name: str):
        self.fn = fn
        self.name = name

    def choose_action(self, state):
        return self.fn(state)


def _has_choose_action(obj) -> bool:
    return callable(getattr(obj, "choose_action", None))


def _label(agent, fallback: str) -> str:
    name = getattr(agent, "name", None)
    return name if isinstance(name, str) and name and name != "agent" else fallback


def load_agent_from_file(path: str, validate: bool = True) -> Agent:
    """Load a plugin file and return an agent object (raises AgentLoadError)."""
    path = os.path.abspath(path)
    if not os.path.isfile(path):
        raise AgentLoadError(f"File not found: {path}")
    stem = os.path.splitext(os.path.basename(path))[0]
    modname = f"_agent_plugin_{stem}_{abs(hash(path)) % 10**8}"
    spec = importlib.util.spec_from_file_location(modname, path)
    if spec is None or spec.loader is None:
        raise AgentLoadError(f"Cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[modname] = module
    try:
        spec.loader.exec_module(module)
    except Exception as e:                                    # syntax / import errors
        raise AgentLoadError(f"{stem}: error while importing: {e!r}") from e

    agent = None
    try:
        if hasattr(module, "AGENT") and _has_choose_action(module.AGENT):
            agent = module.AGENT
        elif callable(getattr(module, "create_agent", None)):
            agent = module.create_agent()
        else:
            for _, cls in inspect.getmembers(module, inspect.isclass):
                if cls.__module__ == modname and (issubclass(cls, Agent)
                                                  or _has_choose_action(cls)):
                    agent = cls()
                    break
            else:
                if callable(getattr(module, "choose_action", None)):
                    agent = FunctionAgent(module.choose_action, stem)
    except Exception as e:
        raise AgentLoadError(f"{stem}: cannot create agent: {e!r}") from e

    if agent is None or not _has_choose_action(agent):
        raise AgentLoadError(
            f"{stem}: no agent found (define AGENT, create_agent(), a class with "
            f"choose_action(self, state) or a function choose_action(state))")
    if not isinstance(getattr(agent, "name", None), str) or agent.name == "agent":
        try:
            agent.name = stem
        except Exception:
            pass

    if validate:                                              # smoke test on the start state
        try:
            action = agent.choose_action(GameState.initial())
        except Exception as e:
            raise AgentLoadError(f"{stem}: choose_action raised {e!r}") from e
        if not isinstance(action, Action):
            raise AgentLoadError(
                f"{stem}: choose_action must return a tank_game.Action, got {action!r}")
    return agent


def discover_agent_files(folder: str = AGENTS_DIR) -> List[str]:
    """All plugin files in the agents/ folder (files starting with '_' are ignored)."""
    if not os.path.isdir(folder):
        return []
    return sorted(os.path.join(folder, f) for f in os.listdir(folder)
                  if f.endswith(".py") and not f.startswith("_"))


# ------------------------------------------------------------- selectable players
@dataclass
class AgentSpec:
    """An entry of the player-selection menu."""
    label: str
    factory: Optional[Callable[[], Agent]]      # None => human player
    path: Optional[str] = None

    @property
    def is_human(self) -> bool:
        return self.factory is None

    def create(self) -> Optional[Agent]:
        return None if self.is_human else self.factory()


def builtin_specs(depth: int = 4) -> List[AgentSpec]:
    specs = [AgentSpec("Human (keyboard)", None),
             AgentSpec("Random", lambda: RandomAgent())]
    for cfg in SearchAgent.CONFIGS:
        specs.append(AgentSpec(f"{cfg} (d={depth})",
                               lambda c=cfg: SearchAgent(c, depth, time_limit=1.0)))
    return specs


def file_spec(path: str) -> AgentSpec:
    """Load once to validate and obtain a name; each game gets a fresh instance."""
    first = load_agent_from_file(path)
    label = "[plugin] " + _label(first, os.path.splitext(os.path.basename(path))[0])
    return AgentSpec(label, lambda p=path: load_agent_from_file(p, validate=False), path)


def all_specs(include_plugins: bool = True) -> List[AgentSpec]:
    specs = builtin_specs()
    if include_plugins:
        for p in discover_agent_files():
            try:
                specs.append(file_spec(p))
            except AgentLoadError as e:
                print("Skipping plugin:", e)
    return specs