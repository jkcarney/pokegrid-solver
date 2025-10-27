from pprint import pprint

from pokegrid_solver import monkeypatch_aiopoke
monkeypatch_aiopoke.patch_all()

import aiopoke
import asyncio

from pokegrid_solver import constraints
from pokegrid_solver.pokeapi_constants import PokeAPIConstants
from pokegrid_solver.strategy import RandomPokegridStrategy
from pokegrid_solver.solver import PokegridSolver

async def entrypoint():
    async with aiopoke.AiopokeClient() as client:
        row_constraints = [
            constraints.PokemonHasType("dragon"),
            constraints.PokemonIsMonotype(),
            constraints.PokemonIsDualType(),
        ]
        column_constraints = [
            constraints.PokemonCanLearnMove("dragon-claw"),
            constraints.PokemonIsLegendaryMythical(),
            constraints.PokemonCanMegaEvolve(),
        ]

        strategy = RandomPokegridStrategy()
        solver = PokegridSolver(
            row_constraints,
            column_constraints,
            strategy,
            client
        )
        suggestions = await solver.suggest_for_constraint(2, 2, top_n=10)
        pprint(suggestions)

        
                




def main() -> None:
    asyncio.run(entrypoint())
