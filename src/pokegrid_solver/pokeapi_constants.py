import aiopoke
from typing import Optional

class PokeAPIConstants:
    _instance: Optional["PokeAPIConstants"] = None

    def __init__(self, client: aiopoke.AiopokeClient):
        self.client: aiopoke.AiopokeClient = client
        self._pokemon_types = None

    @classmethod
    async def get_instance(cls, client: aiopoke.AiopokeClient) -> "PokeAPIConstants":
        if cls._instance is None:
            cls._instance = cls(client)
        return cls._instance

    @property
    async def pokemon_types(self):
        if self._pokemon_types is not None:
            return self._pokemon_types
        # aiopoke's method for getting types cannot account for the no parameter version
        # We have to bypass it and get it directly and process the results.
        raw_result = await self.client.http.get("type")
        all_types = [type_result['name'] for type_result in raw_result["results"]]
        self._pokemon_types = all_types
        return self._pokemon_types