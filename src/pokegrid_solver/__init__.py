from pokegrid_solver import monkeypatch_aiopoke
monkeypatch_aiopoke.patch_all()

import aiopoke
import asyncio

from pokegrid_solver import constraints
from pokegrid_solver.pokeapi_constants import PokeAPIConstants

async def entrypoint():
    async with aiopoke.AiopokeClient() as client: 
        data = await client.get_evolution_chain(140)
        print(data.chain.evolves_to[0].species.name)

        
                




def main() -> None:
    asyncio.run(entrypoint())
