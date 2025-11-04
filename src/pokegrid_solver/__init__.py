from pokegrid_solver import monkeypatch_aiopoke
monkeypatch_aiopoke.patch_all()

from pprint import pprint 
import aiopoke
import asyncio
from load_dotenv import load_dotenv
load_dotenv()

from pokegrid_solver import constraints
from pokegrid_solver.pokeapi_constants import PokeAPIConstants
from pokegrid_solver.strategy import RandomPokegridStrategy, ChatGPTStrategy, ReverseChatGPTBaselineStrategy
from pokegrid_solver.solver import PokegridSolver

async def entrypoint():
    async with aiopoke.AiopokeClient() as client:
        row_constraints = [
            constraints.PokemonHasType("steel"),
            constraints.PokemonHasType("rock"),
            constraints.PokemonIsDualType()
        ]
        column_constraints = [
            constraints.PokemonCanLearnMove("stone-edge"),
            constraints.PokemonNeutralToType('fire'),
            constraints.PokemonHighestBaseStat("defense")
        ]

        # strategy = RandomPokegridStrategy()
        # strategy = ChatGPTStrategy()
        strategy = ChatGPTStrategy(request_return=20)
        solver = PokegridSolver(
            row_constraints,
            column_constraints,
            strategy,
            client
        )
        for i in range(3):
            for j in range(3):
                suggestions = await solver.suggest_for_constraint(i, j, top_n=10)
                top_pokemon, top_score = suggestions[0]
                solver.choose_pokemon(top_pokemon)
                print(f"For {row_constraints[i]} and {column_constraints[j]}, choose {top_pokemon} (score: {top_score:.2f})")
                pprint(suggestions)

        # Notes to self:
        # probably two good metrics are average delta between top ranked player rarity score for a given pokegrid and also the most common rarity score

def main() -> None:
    asyncio.run(entrypoint())
