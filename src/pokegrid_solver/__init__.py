import aiopoke
import asyncio

from pokegrid_solver import constraints
from pokegrid_solver.pokeapi_constants import PokeAPIConstants

async def entrypoint():
    async with aiopoke.AiopokeClient() as client: 
        flying_constraint = constraints.PokemonHasType('flying')
        flying_pokemon = await flying_constraint.determine_pkmn_set(client)
        fire_constraint = constraints.PokemonHasType('fire')
        fire_pokemom = await fire_constraint.determine_pkmn_set(client)
        print(flying_pokemon & fire_pokemom)

        print("------")
        constants = await PokeAPIConstants.get_instance(client)
        all_types = await constants.pokemon_types
        print(all_types)

        print("------")
        monotype_constraint = constraints.PokemonIsMonotype(flying_constraint)
        monotypes = await monotype_constraint.determine_pkmn_set(client)
        print(monotypes)



def main() -> None:
    asyncio.run(entrypoint())
