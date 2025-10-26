import aiopoke
from typing import Optional, List
import asyncio

class PokeAPIConstants:
    _instance: Optional["PokeAPIConstants"] = None

    def __init__(self, client: aiopoke.AiopokeClient):
        self.client: aiopoke.AiopokeClient = client
        self._pokemon_types = None
        self._all_pokemon = None

        self._first_evolutions = None
        self._middle_evolutions = None
        self._final_evolutions = None
        self._no_evolutions = None
        

    @classmethod
    async def get_instance(cls, client: aiopoke.AiopokeClient) -> "PokeAPIConstants":
        if cls._instance is None:
            cls._instance = cls(client)
        else:
            # Rebind to the live client provided by the caller (pytest fixture)
            cls._instance.client = client
        return cls._instance
    

    @property
    async def pokemon_types(self):
        if self._pokemon_types is not None:
            return self._pokemon_types
        # aiopoke's method for getting types cannot account for the no parameter version
        # We have to bypass it and get it directly and process the results.
        # maybe make a PR for it LOL
        raw_result = await self.client.http.get("type")
        all_types = [type_result['name'] for type_result in raw_result["results"]]
        self._pokemon_types = all_types
        return self._pokemon_types
    
    @property
    async def first_evolutions(self):
        if self._first_evolutions is None:
            await self._classify_evolution_roles()
        return self._first_evolutions
    
    @property
    async def middle_evolutions(self):
        if self._middle_evolutions is None:
            await self._classify_evolution_roles()
        return self._middle_evolutions
    
    @property
    async def final_evolutions(self):
        if self._final_evolutions is None:
            await self._classify_evolution_roles()
        return self._final_evolutions
    
    @property
    async def no_evolutions(self):
        if self._no_evolutions is None:
            await self._classify_evolution_roles()
        return self._no_evolutions
    

    @property
    async def all_pokemon(self) -> List[str]:
        """
        Cached list of every Pokémon name returned by PokeAPI's /pokemon endpoint.
        Uses a very high `limit` to avoid pagination and does one network call.
        """
        if self._all_pokemon is not None:
            return self._all_pokemon

        # This returns basic Pokémon resources (not species), which is typically what you want
        # for names/typing/moves, and includes forms like "mr-mime" as named by PokeAPI.
        raw_result = await self.client.http.get("pokemon?limit=200000&offset=0")
        self._all_pokemon = [p["name"] for p in raw_result["results"]]
        return self._all_pokemon
    
    async def _classify_evolution_roles(self) -> None:
        all_evolution_chains = await self.client.http.get("evolution-chain?limit=200000&offset=0")
        all_evolution_chains = all_evolution_chains["results"]
        chain_ids = [d["url"].rstrip("/").split("/")[-1] for d in all_evolution_chains]

        async def get_evolution_chain_data(entry):
            return await self.client.get_evolution_chain(int(entry))

        evolution_chain_data = await asyncio.gather(*(get_evolution_chain_data(n) for n in chain_ids))

        def _collect_paths(node, cur, out) -> None:
            name = node.species.name
            children = getattr(node, "evolves_to", []) or []
            if not children:
                out.append(cur + [name])
                return
            for child in children:
                _collect_paths(child, cur + [name], out)

        def evolution_roles(evo_chain):
            paths = []
            _collect_paths(evo_chain.chain, [], paths)

            # Single-species chain (no evolutions): classify separately
            if len(paths) == 1 and len(paths[0]) == 1:
                no_evos = {paths[0][0]}
                return {"paths": paths, "first": set(), "middle": set(), "final": set(), "no_evolutions": no_evos}


            first = {p[0] for p in paths}
            final= {p[-1] for p in paths}
            middle = set()
            for p in paths:
                if len(p) > 2:
                    middle.update(p[1:-1])

            return {"paths": paths, "first": first, "middle": middle, "final": final, "no_evolutions": set()}
        
        first_all = set()
        middle_all = set()
        final_all = set()
        no_evolutions_all = set()

        for chain in evolution_chain_data:
            roles = evolution_roles(chain)
            first_all |= roles["first"]
            middle_all |= roles["middle"]
            final_all |= roles["final"]
            no_evolutions_all |= roles["no_evolutions"]

        self._first_evolutions = first_all
        self._middle_evolutions = middle_all
        self._final_evolutions = final_all
        self._no_evolutions = no_evolutions_all
        

        