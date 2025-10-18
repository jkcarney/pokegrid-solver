import abc
from collections import Counter
from typing import List, Optional, Set
import asyncio

import aiopoke

from pokegrid_solver.pokeapi_constants import PokeAPIConstants

class Constraint:
    @abc.abstractmethod
    async def determine_pkmn_set(self, client: aiopoke.AiopokeClient) -> Set:
        raise NotImplementedError()

class PokemonHasType(Constraint):
    def __init__(self, type_constraint: str):
        super().__init__()
        self.type_constraint = type_constraint

    async def determine_pkmn_set(self, client: aiopoke.AiopokeClient) -> Set:
        type_info = await client.get_type(self.type_constraint)
        typed_pokemon = [pkmn.pokemon.name for pkmn in type_info.pokemon]
        return set(typed_pokemon)
    

class PokemonIsMonotype(Constraint):
    def __init__(self, type_constraint: Optional[PokemonHasType] = None):
        """
        Pokemon only has one type. 

        :param type_constraints: Optional type constraint list to filter for monotypes. Ie, you can filter for all fire monotypes
        """
        super().__init__()
        self._type_constraint = type_constraint

    async def _gather_pokemon_for_set(self, client, constraints):
        """
        Utility to gather all the pokemon that satisfy the PokemonHasType constraint

        :param client: aiopoke client
        :param constraints: list of constraints
        :return: a set of pokemon that satisfy the constraints
        """
        type_sets = await asyncio.gather(*(c.determine_pkmn_set(client) for c in constraints))
        return type_sets

    async def _get_all_pokemon_type_set(self, client) -> Set[str]:
        constants = await PokeAPIConstants.get_instance(client)
        all_types_list = await constants.pokemon_types
        all_type_constraints = [PokemonHasType(p_type) for p_type in all_types_list]
        all_type_sets = await self._gather_pokemon_for_set(client, all_type_constraints)
        return all_type_sets

    async def determine_pkmn_set(self, client) -> Set:
        all_type_sets = await self._get_all_pokemon_type_set(client)
        counter = Counter(p for s in all_type_sets for p in s)
        monotypes = {p for p, cnt in counter.items() if cnt == 1}

        if not self._type_constraint:
            return monotypes

        subset_sets = await self._gather_pokemon_for_set(client, [self._type_constraint])
        subset_allowed = set().union(*subset_sets) if subset_sets else set
        return monotypes & subset_allowed

