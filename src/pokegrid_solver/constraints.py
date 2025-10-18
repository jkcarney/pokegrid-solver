import abc
from typing import List, Optional
import aiopoke

from pokegrid_solver.pokeapi_constants import PokeAPIConstants

class Constraint:
    @abc.abstractmethod
    async def determine_pkmn_set(self, client: aiopoke.AiopokeClient):
        raise NotImplementedError()

class PokemonHasType(Constraint):
    def __init__(self, type_constraint: str):
        super().__init__()
        self.type_constraint = type_constraint

    async def determine_pkmn_set(self, client: aiopoke.AiopokeClient):
        type_info = await client.get_type(self.type_constraint)
        typed_pokemon = [pkmn.pokemon.name for pkmn in type_info.pokemon]
        return set(typed_pokemon)
    

class PokemonIsMonotype(Constraint):
    def __init__(self, type_constraints: Optional[List[PokemonHasType]] = None):
        """
        Pokemon only has one type. 

        :param type_constraints: Optional list to check against. Specifying this avoids querying every type. 
        """
        super().__init__()
        
        self._type_constraints = type_constraints

    async def determine_pkmn_set(self, client):
        if not self._type_constraints:
            constants = await PokeAPIConstants.get_instance(client)
            all_types_list = await constants.pokemon_types
            self._type_constraints = [PokemonHasType(p_type) for p_type in all_types_list]

        for type_constraint in self._type_constraints:
            pass

        return await super().determine_pkmn_set(client)

