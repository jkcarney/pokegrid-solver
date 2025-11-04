import aiopoke

from pokegrid_solver.constraints import Constraint
from pokegrid_solver.strategy import PokegridStrategy

class PokegridSolver:
    def __init__(self, row_constraints: list[Constraint], column_constraints: list[Constraint], strategy: PokegridStrategy, client: aiopoke.AiopokeClient):
        if len(row_constraints) != 3:
            raise ValueError("Did not provide 3 row constraints")
        
        if len(column_constraints) != 3:
            raise ValueError("Did not provide 3 column constraints")
        
        self.row_constraints = row_constraints
        self.column_constraints = column_constraints
        self.strategy = strategy
        self.selected_pokemon = set()
        self.client = client

    async def suggest_for_constraint(self, row_idx: int, col_idx: int, top_n = 5) -> tuple[list[str], int]:
        if row_idx < 0 or row_idx > 2:
            raise ValueError("row_idx needs to be between 0 and 2")
        
        if col_idx < 0 or col_idx > 2:
            raise ValueError("col_idx needs to be between 0 and 2")
        
        row_constraint = self.row_constraints[row_idx]
        col_constraint = self.column_constraints[col_idx]
        possible_pokemon = ((await row_constraint.determine_pkmn_set(self.client) & await col_constraint.determine_pkmn_set(self.client)) - self.selected_pokemon)
        ranked_pokemon = await self.strategy.rank_options(possible_pokemon)
        return ranked_pokemon[:top_n], len(possible_pokemon)

    def choose_pokemon(self, name):
        self.selected_pokemon.add(name)