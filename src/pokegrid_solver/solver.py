from pokegrid_solver.constraints import Constraint
from pokegrid_solver.strategy import PokegridStrategy

class PokegridSolver:
    def __init__(self, row_constraints: list[Constraint], column_constraints: list[Constraint], strategy: PokegridStrategy):
        if len(row_constraints) != 3:
            raise ValueError("Did not provide 3 row constraints")
        
        if len(column_constraints) != 3:
            raise ValueError("Did not provide 3 column constraints")
        
        self.row_constraints = row_constraints
        self.column_constraints = column_constraints
        self.strategy = strategy