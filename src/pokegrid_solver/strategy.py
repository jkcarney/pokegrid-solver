from abc import abstractmethod, ABC
import random
from typing import List

from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel

class PokegridStrategy(ABC):
    @abstractmethod
    async def rank_options(self, available_pokemon: set[str]) -> list[tuple[str, float]]:
        """
        Given a set of available pokemon, return a list of tuples sorted by the second value.
        High values represent pokemon that should be chosen given the list of available options

        :param available_pokemon: Set of string of pokemon names
        :return: A sorted list of tuples of string/floats
        """
        raise NotImplementedError()
    
class RandomPokegridStrategy(PokegridStrategy):
    async def rank_options(self, available_pokemon: set[str]) -> list[tuple[str, float]]:
        rng = random.Random()
        ranking = [(item, rng.random()) for item in sorted(available_pokemon)] 
        ranking.sort(key=lambda t: (-t[1], t[0]))
        return ranking
    
class RankedItem(BaseModel):
    name: str = Field(description="Pokemon name exactly as provided")
    score: float = Field(description="Higher means less popular / more desirable")
    
class RankedList(BaseModel):
    ranking: List[RankedItem]

    
class ChatGPTStrategy(PokegridStrategy):
    def __init__(self, model="gpt-5-mini-2025-08-07"):
        super().__init__()
        self._model = OpenAIChatModel(model)
        self._system_prompt = \
        """
        You are a Pokemon game expert. You will receive a set of Pokemon names. You must rank each Pokemon by how 'unpopular' you think that Pokemon is. Ie, what is the probability or liklihood that that Pokemon is not in the collective conciousness.
        Your job is to return a list of tuples, where each tuple is a string, float where the string is the Pokemon's name as I originally gave it and the float is the score for that Pokemon.
        Higher floats mean that Pokemon is less popular, and therefore more desirable. Lower floats mean that Pokemon is very popular and much less desirable.
        Don't worry about ordering the list, only return it in the same order I provided you with the floats attached as tuples.
        """
        self._agent = Agent(model, output_type=RankedList, system_prompt=self._system_prompt)
    
    def ranked_list_to_tuples(self, rl: "RankedList") -> list[tuple[str, float]]:
        return [(item.name, float(item.score)) for item in rl.ranking]

    async def rank_options(self, available_pokemon: set[str]) -> list[tuple[str, float]]:
        result = await self._agent.run(f"{list(available_pokemon)}")
        gpt_ranked_list = result.output
        ranked_tuple_list = self.ranked_list_to_tuples(gpt_ranked_list)
        ranked_tuple_list.sort(key=lambda t: (-t[1], t[0]))
        return ranked_tuple_list


class ReverseChatGPTBaselineStrategy(ChatGPTStrategy):
    def __init__(self, model="gpt-5-mini-2025-08-07"):
        super().__init__(model=model)
        self._system_prompt = \
        """
        You are a Pokemon game expert. You will receive a set of Pokemon names. You must rank each Pokemon by how popular you think that Pokemon is. Ie, what is the probability or likelihood that that Pokemon is popular among the Pokemon crowd, fanbase, or general collective conciousness.
        Your job is to return a list of tuples, where each tuple is a string, float where the string is the Pokemon's name as I originally gave it and the float is the score for that Pokemon.
        Higher floats mean that Pokemon is more popular, and therefore more desirable. Lower floats mean that Pokemon is less popular and much less desirable.
        Don't worry about ordering the list, only return it in the same order I provided you with the floats attached as tuples.
        """
        self._agent = Agent(model, output_type=RankedList, system_prompt=self._system_prompt)