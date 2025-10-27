from abc import abstractmethod, ABC
import random

class PokegridStrategy(ABC):
    @abstractmethod
    def rank_options(available_pokemon: set[str]) -> list[tuple[str, float]]:
        """
        Given a set of available pokemon, return a list of tuples sorted by the second value.
        High values represent pokemon that should be chosen given the list of available options

        :param available_pokemon: Set of string of pokemon names
        :return: A sorted list of tuples of string/floats
        """
        raise NotImplementedError()
    
class RandomPokegridStrategy(PokegridStrategy):
    def rank_options(available_pokemon: set[str]) -> list[tuple[str, float]]:
        rng = random.Random()
        ranking = [(item, rng.random()) for item in sorted(available_pokemon)] 
        ranking.sort(key=lambda t: (-t[1], t[0]))
        return ranking