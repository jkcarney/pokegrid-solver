import aiopoke
from typing import Optional, List
import asyncio

STAT_NAME_TO_INDICES = {
    "hp": 0,
    "attack": 1,
    "defense": 2,
    "special-attack": 3,
    "special-defense": 4,
    "speed": 5
}

class PokeAPIConstants:
    _instance: Optional["PokeAPIConstants"] = None

    def __init__(self, client: aiopoke.AiopokeClient):
        self.client: aiopoke.AiopokeClient = client
        self._pokemon_types = None
        self._all_pokemon = None
        self._legendaries = None
        self._mythicals = None

        self._first_evolutions = None
        self._middle_evolutions = None
        self._final_evolutions = None
        self._no_evolutions = None
        
        self._weights = None
        self._heights = None
        

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
    
    @property
    async def legendary_pokemon(self) -> List[str]:
        if self._legendaries is not None:
            return self._legendaries
    
        await self._gather_legendaries_and_mythicals()
        return self._legendaries
        
    @property
    async def mythical_pokemon(self) -> List[str]:
        if self._mythicals is not None:
            return self._mythicals
        
        await self._gather_legendaries_and_mythicals()
        return self._mythicals
    
    async def gather_heights(self):
        if self._heights is not None:
            return self._heights
    
        all_species = await self.client.http.get("pokemon?limit=200000&offset=0")
        all_species = all_species["results"]
        species_ids = [d["url"].rstrip("/").split("/")[-1] for d in all_species]

        async def get_pokemon_data(entry):
            return await self.client.get_pokemon(int(entry))

        species_data = await asyncio.gather(*(get_pokemon_data(n) for n in species_ids))
        self._heights = [(species.name, species.height) for species in species_data]
        return self._heights

    async def gather_weights(self):
        if self._weights is not None:
            return self._weights
        
        all_species = await self.client.http.get("pokemon?limit=200000&offset=0")
        all_species = all_species["results"]
        species_ids = [d["url"].rstrip("/").split("/")[-1] for d in all_species]

        async def get_pokemon_data(entry):
            return await self.client.get_pokemon(int(entry))

        species_data = await asyncio.gather(*(get_pokemon_data(n) for n in species_ids))
        self._weights = [(species.name, species.weight) for species in species_data]
        return self._weights
    
    async def highest_base_stats(self, stat_name):
        index = STAT_NAME_TO_INDICES[stat_name]

        all_species = await self.client.http.get("pokemon?limit=200000&offset=0")
        all_species = all_species["results"]
        species_ids = [d["url"].rstrip("/").split("/")[-1] for d in all_species]

        async def get_pokemon_data(entry):
            return await self.client.get_pokemon(int(entry))
        
        species_data = await asyncio.gather(*(get_pokemon_data(n) for n in species_ids))
        pkmn_names = []
        for species in species_data:
            stat_to_beat = species.stats[index].base_stat
            is_highest = True

            for stat in species.stats:
                if stat.stat.name == stat_name:
                    continue
                
                if stat.base_stat > stat_to_beat or stat.base_stat == stat_to_beat:
                    is_highest = False
            
            if is_highest:
                pkmn_names.append(species.name)
        
        return pkmn_names

    async def _gather_legendaries_and_mythicals(self) -> None:
        all_species = await self.client.http.get("pokemon-species?limit=200000&offset=0")
        all_species = all_species["results"]
        species_ids = [d["url"].rstrip("/").split("/")[-1] for d in all_species]

        async def get_species_data(entry):
            return await self.client.get_pokemon_species(int(entry))

        species_data = await asyncio.gather(*(get_species_data(n) for n in species_ids))
        legendaries = [species.name for species in species_data if species.is_legendary]
        mythicals = [species.name for species in species_data if species.is_mythical]

        self._legendaries = legendaries
        self._mythicals = mythicals

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
        

        