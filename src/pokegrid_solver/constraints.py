import abc
from collections import Counter
from typing import List, Optional, Set
import asyncio

import aiopoke

from pokegrid_solver.pokeapi_constants import PokeAPIConstants

class Constraint:
    async def _gather_pokemon_for_constraint(self, client, constraints: List["Constraint"]):
        """
        Utility to gather all the pokemon that satisfy the PokemonHasType constraint

        :param client: aiopoke client
        :param constraints: list of constraints
        :return: a set of pokemon that satisfy the constraints
        """
        type_sets = await asyncio.gather(*(c.determine_pkmn_set(client) for c in constraints))
        return type_sets
    
    @abc.abstractmethod
    async def determine_pkmn_set(self, client: aiopoke.AiopokeClient) -> Set:
        raise NotImplementedError()

class PokemonHasType(Constraint):
    def __init__(self, type_constraint: str):
        super().__init__()
        self.type_constraint = type_constraint

    def __repr__(self):
        return f"PokemonHasType({self.type_constraint})"

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

    def __repr__(self):
        return f"PokemonIsMonotype()"

    async def _get_all_pokemon_type_set(self, client) -> Set[str]:
        constants = await PokeAPIConstants.get_instance(client)
        all_types_list = await constants.pokemon_types
        all_type_constraints = [PokemonHasType(p_type) for p_type in all_types_list]
        all_type_sets = await self._gather_pokemon_for_constraint(client, all_type_constraints)
        return all_type_sets

    async def determine_pkmn_set(self, client) -> Set:
        all_type_sets = await self._get_all_pokemon_type_set(client)
        counter = Counter(p for s in all_type_sets for p in s)
        monotypes = {p for p, cnt in counter.items() if cnt == 1}

        if not self._type_constraint:
            return monotypes

        subset_sets = await self._gather_pokemon_for_constraint(client, [self._type_constraint])
        subset_allowed = set().union(*subset_sets) if subset_sets else set
        return monotypes & subset_allowed


class PokemonIsDualType(PokemonIsMonotype):
    def __init__(self, type_constraint: Optional[PokemonHasType] = None):
        super().__init__()
        self._type_constraint = type_constraint

    def __repr__(self):
        return f"PokemonIsDualType()"
    
    async def determine_pkmn_set(self, client) -> Set[str]:
        all_type_sets = await self._get_all_pokemon_type_set(client)
        counter = Counter(p for s in all_type_sets for p in s)

        # Dual (or multi) type Pokémon appear in at least 2 type sets
        dualtypes = {p for p, cnt in counter.items() if cnt >= 2}

        if not self._type_constraint:
            return dualtypes

        subset_sets = await self._gather_pokemon_for_constraint(client, [self._type_constraint])
        subset_allowed = set().union(*subset_sets) if subset_sets else set()
        return dualtypes & subset_allowed


class PokemonResistantToType(Constraint):
    def __init__(self, resistant_to):
        super().__init__()
        self._resistant_to = resistant_to

    def __repr__(self):
        return f"PokemonResistantToType({self._resistant_to})"
    
    async def determine_pkmn_set(self, client: aiopoke.AiopokeClient) -> Set[str]:
        """
        Return Pokémon whose overall damage multiplier vs the given attacking type is < 1.0.
        This accounts for dual types by multiplying per-type modifiers:
          - no_damage_to -> 0x (immunity)
          - half_damage_to -> 0.5x (resist)
          - double_damage_to -> 2x (weak)
        """
        atk_type = await client.get_type(self._resistant_to)

        # Collect defender type names for each effectiveness category
        immune_def_types = [t.name for t in atk_type.damage_relations.no_damage_to]
        resist_def_types = [t.name for t in atk_type.damage_relations.half_damage_to]
        weak_def_types   = [t.name for t in atk_type.damage_relations.double_damage_to]

        # Helper to fetch the set of Pokémon for each defender type
        async def type_to_pokemon_set(type_name: str) -> Set[str]:
            return await PokemonHasType(type_name).determine_pkmn_set(client)

        # Fetch sets concurrently
        immune_sets, resist_sets, weak_sets = await asyncio.gather(
            asyncio.gather(*(type_to_pokemon_set(t) for t in immune_def_types)),
            asyncio.gather(*(type_to_pokemon_set(t) for t in resist_def_types)),
            asyncio.gather(*(type_to_pokemon_set(t) for t in weak_def_types)),
        )

        # Flatten (handle empty lists gracefully)
        immune_sets = immune_sets or []
        resist_sets = resist_sets or []
        weak_sets   = weak_sets or []

        # Count per-Pokémon how many of its types fall into immune/resist/weak categories
        immune_counts: Counter[str] = Counter()
        resist_counts: Counter[str] = Counter()
        weak_counts:   Counter[str] = Counter()

        for s in immune_sets:
            for p in s:
                immune_counts[p] += 1
        for s in resist_sets:
            for p in s:
                resist_counts[p] += 1
        for s in weak_sets:
            for p in s:
                weak_counts[p] += 1

        # Universe to consider = any Pokémon that appear in any relevant set
        universe: Set[str] = set(immune_counts) | set(resist_counts) | set(weak_counts)

        resistant: Set[str] = set()
        for p in universe:
            if immune_counts[p] > 0:
                # Any immunity yields 0x overall
                resistant.add(p)
                continue

            # Multiply modifiers for each applicable defending type the Pokémon has
            # (most Pokémon have 1 or 2 types; counts capture dual-typing)
            modifier = (0.5 ** resist_counts[p]) * (2.0 ** weak_counts[p])

            if modifier < 1.0:
                resistant.add(p)

        return resistant
    

class PokemonWeakToType(Constraint):
    def __init__(self, weak_to: str):
        super().__init__()
        self.weak_to = weak_to

    def __repr__(self):
        return f"PokemonWeakToType({self.weak_to})"

    async def determine_pkmn_set(self, client: aiopoke.AiopokeClient) -> Set[str]:
        """
        Return Pokémon whose overall damage multiplier vs the given attacking type is > 1.0.
        Accounts for dual typing by multiplying per-type modifiers.
        """
        atk_type = await client.get_type(self.weak_to)

        immune_def_types = [t.name for t in atk_type.damage_relations.no_damage_to]
        resist_def_types = [t.name for t in atk_type.damage_relations.half_damage_to]
        weak_def_types   = [t.name for t in atk_type.damage_relations.double_damage_to]

        async def type_to_pokemon_set(type_name: str) -> Set[str]:
            return await PokemonHasType(type_name).determine_pkmn_set(client)

        immune_sets, resist_sets, weak_sets = await asyncio.gather(
            asyncio.gather(*(type_to_pokemon_set(t) for t in immune_def_types)),
            asyncio.gather(*(type_to_pokemon_set(t) for t in resist_def_types)),
            asyncio.gather(*(type_to_pokemon_set(t) for t in weak_def_types)),
        )

        immune_sets = immune_sets or []
        resist_sets = resist_sets or []
        weak_sets   = weak_sets or []

        immune_counts: Counter[str] = Counter()
        resist_counts: Counter[str] = Counter()
        weak_counts:   Counter[str] = Counter()

        for s in immune_sets:
            for p in s:
                immune_counts[p] += 1
        for s in resist_sets:
            for p in s:
                resist_counts[p] += 1
        for s in weak_sets:
            for p in s:
                weak_counts[p] += 1

        universe: Set[str] = set(immune_counts) | set(resist_counts) | set(weak_counts)

        weak_overall: Set[str] = set()
        for p in universe:
            if immune_counts[p] > 0:
                # Any immunity cancels weakness (0x overall).
                continue
            # Overall modifier = 0.5^(#resist) * 2^(#weak) = 2^(weak - resist)
            if weak_counts[p] > resist_counts[p]:
                weak_overall.add(p)

        return weak_overall

class PokemonNeutralToType(Constraint):
    def __init__(self, neutral_to: str):
        super().__init__()
        self._neutral_to = neutral_to

    def __repr__(self):
        return f"PokemonNeutralToType({self._neutral_to})"

    async def determine_pkmn_set(self, client: aiopoke.AiopokeClient) -> Set[str]:
        """
        Return Pokémon whose overall damage multiplier vs the given attacking type is exactly 1.0.
        This includes single-type Pokémon that are neutral, and dual-types whose modifiers cancel
        (e.g., one resists and the other is weak).
        """
        atk_type = await client.get_type(self._neutral_to)

        immune_def_types = [t.name for t in atk_type.damage_relations.no_damage_to]
        resist_def_types = [t.name for t in atk_type.damage_relations.half_damage_to]
        weak_def_types   = [t.name for t in atk_type.damage_relations.double_damage_to]

        async def type_to_pokemon_set(type_name: str) -> Set[str]:
            return await PokemonHasType(type_name).determine_pkmn_set(client)

        # Sets that affect the multiplier (non-1x categories)
        immune_sets, resist_sets, weak_sets = await asyncio.gather(
            asyncio.gather(*(type_to_pokemon_set(t) for t in immune_def_types)),
            asyncio.gather(*(type_to_pokemon_set(t) for t in resist_def_types)),
            asyncio.gather(*(type_to_pokemon_set(t) for t in weak_def_types)),
        )

        immune_sets = immune_sets or []
        resist_sets = resist_sets or []
        weak_sets   = weak_sets or []

        immune_counts: Counter[str] = Counter()
        resist_counts: Counter[str] = Counter()
        weak_counts:   Counter[str] = Counter()

        for s in immune_sets:
            for p in s:
                immune_counts[p] += 1
        for s in resist_sets:
            for p in s:
                resist_counts[p] += 1
        for s in weak_sets:
            for p in s:
                weak_counts[p] += 1

        # Build full Pokémon universe (all Pokémon of any type) so that neutrals
        # whose types never appear in the above lists are included.
        constants = await PokeAPIConstants.get_instance(client)
        all_types_list = await constants.pokemon_types
        all_type_sets = await asyncio.gather(
            *(PokemonHasType(t).determine_pkmn_set(client) for t in all_types_list)
        )
        universe_all: Set[str] = set().union(*all_type_sets) if all_type_sets else set()

        neutral_overall: Set[str] = set()
        for p in universe_all:
            if immune_counts[p] > 0:
                # Any immunity => not neutral (0x).
                continue
            # Overall modifier = 2^(weak - resist).
            # Neutral iff exponent == 0  <=> weak_count == resist_count.
            if weak_counts[p] == resist_counts[p]:
                neutral_overall.add(p)

        return neutral_overall


class PokemonFirstEvolutionLine(Constraint):
    def __init__(self):
        super().__init__()

    def __repr__(self):
        return "PokemonFirstEvolutionLine()"
    
    async def determine_pkmn_set(self, client):
        constants = await PokeAPIConstants.get_instance(client)
        first_evolutions = await constants.first_evolutions
        return first_evolutions
    

class PokemonMiddleEvolutionLine(Constraint):
    def __init__(self):
        super().__init__()
    
    def __repr__(self):
        return "PokemonMiddleEvolutionLine()"

    async def determine_pkmn_set(self, client):
        constants = await PokeAPIConstants.get_instance(client)
        middle_evolutions = await constants.middle_evolutions
        return middle_evolutions
    

class PokemonFinalEvolutionLine(Constraint):
    def __init__(self):
        super().__init__()

    def __repr__(self):
        return "PokemonFinalEvolutionLine()"

    async def determine_pkmn_set(self, client):
        constants = await PokeAPIConstants.get_instance(client)
        final_evolutions = await constants.final_evolutions
        return final_evolutions


class PokemonNoEvolutionLine(Constraint):
    def __init__(self):
        super().__init__()
        
    def __repr__(self):
        return "PokemonNoEvolutionLine()"

    async def determine_pkmn_set(self, client):
        constants = await PokeAPIConstants.get_instance(client)
        no_evolutions = await constants.no_evolutions
        return no_evolutions

class PokemonCanMegaEvolve(Constraint):
    def __init__(self):
        super().__init__()

    def __repr__(self):
        return "PokemonCanMegaEvolve()"
    
    async def determine_pkmn_set(self, client):
        constants = await PokeAPIConstants.get_instance(client)
        all_pokemon = await constants.all_pokemon
        megas = [pokemon for pokemon in all_pokemon if "-mega" in pokemon]
        megas = set(map(lambda s: s.split("-mega", 1)[0], megas))
        return megas
    
class PokemonIsMegaEvolution(Constraint):
    def __init__(self):
        super().__init__()
    
    def __repr__(self):
        return "PokemonIsMegaEvolution()"
    
    async def determine_pkmn_set(self, client):
        constants = await PokeAPIConstants.get_instance(client)
        all_pokemon = await constants.all_pokemon
        megas = [pokemon for pokemon in all_pokemon if "-mega" in pokemon]
        return set(megas)
    

class PokemonIsLegendaryMythical(Constraint):
    def __init__(self):
        super().__init__()
    
    def __repr__(self):
        return "PokemonIsLegendaryMythical()"
    
    async def determine_pkmn_set(self, client):
        constants = await PokeAPIConstants.get_instance(client)
        legendaries = await constants.legendary_pokemon
        mythicals = await constants.mythical_pokemon
        return set(legendaries + mythicals)
    

class PokemonCanLearnMove(Constraint):
    def __init__(self, move_name):
        super().__init__()
        self.move_name = move_name
    
    def __repr__(self):
        return f"PokemonCanLearnMove({self.move_name})"

    async def determine_pkmn_set(self, client):
        move_data = await client.get_move(self.move_name)
        pokemon_can_learn = move_data.learned_by_pokemon
        return {pkmn.name for pkmn in pokemon_can_learn}


class PokemonFirstSeenInGeneration(Constraint):
    def __init__(self, gen_number):
        super().__init__()
        self._gen_number = gen_number
    
    def __repr__(self):
        return f"PokemonFirstSeenInGeneration({self._gen_number})"

    async def determine_pkmn_set(self, client):
        generation = await client.get_generation(self._gen_number)
        generation_pokemon = generation.pokemon_species
        return {pkmn.name for pkmn in generation_pokemon}

def decimeters2ftinches(dm):
    total_inches = dm * 3.937007874015748 
    feet = int(total_inches // 12)
    inches = total_inches - feet * 12

    if inches >= 12:
        feet += 1
        inches = 0.0

    return feet, inches

def ftinches2decimeters(feet, inches):
    total_inches = feet * 12 + inches
    dm = total_inches * 0.254  # exact: 1 inch = 0.254 decimeters
    return dm

class PokemonShorterThan(Constraint):
    def __init__(self, feet, inches):
        super().__init__()
        self.feet = feet
        self.inches = inches

    def __repr__(self):
        return f"PokemonShorterThan({self.feet}ft, {self.inches}in)"
    
    async def determine_pkmn_set(self, client):
        constants = await PokeAPIConstants.get_instance(client)
        pokemon_heights = await constants.gather_heights()
        maximum = ftinches2decimeters(self.feet, self.inches)
        return {name for (name, height) in pokemon_heights if height < maximum}
    

class PokemonTallerThan(Constraint):
    def __init__(self, feet, inches):
        super().__init__()
        self.feet = feet
        self.inches = inches

    def __repr__(self):
        return f"PokemonTallerThan({self.feet}ft, {self.inches}in)"

    async def determine_pkmn_set(self, client):
        constants = await PokeAPIConstants.get_instance(client)
        pokemon_heights = await constants.gather_heights()
        maximum = ftinches2decimeters(self.feet, self.inches)
        return {name for (name, height) in pokemon_heights if height > maximum}

def hg2lbs(hg):
    return hg / 4.536

def lbs2hg(lbs):
    return lbs * 4.536

class PokemonHeavierThan(Constraint):
    def __init__(self, pounds):
        super().__init__()
        self.weight = pounds
    
    def __repr__(self):
        return f"PokemonHeavierThan({self.weight})"

    async def determine_pkmn_set(self, client):
        constants = await PokeAPIConstants.get_instance(client)
        pokemon_weights = await constants.gather_weights()
        return {name for (name, weight) in pokemon_weights if hg2lbs(weight) > self.weight}
    

class PokemonLighterThan(Constraint):
    def __init__(self, pounds):
        super().__init__()
        self.weight = pounds
    
    def __repr__(self):
        return f"PokemonLighterThan({self.weight})"

    async def determine_pkmn_set(self, client):
        constants = await PokeAPIConstants.get_instance(client)
        pokemon_weights = await constants.gather_weights()
        return {name for (name, weight) in pokemon_weights if hg2lbs(weight) < self.weight}


class PokemonHighestBaseStat(Constraint):
    def __init__(self, stat_name):
        super().__init__()
        self.stat_name = stat_name

    def __repr__(self):
        return f"PokemonHighestBaseStat({self.stat_name})"

    async def determine_pkmn_set(self, client):
        constants = await PokeAPIConstants.get_instance(client)
        highest_base_pkmn = await constants.highest_base_stats(self.stat_name)
        return set(highest_base_pkmn)
    
    