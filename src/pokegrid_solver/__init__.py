from pokegrid_solver import monkeypatch_aiopoke
monkeypatch_aiopoke.patch_all()

import argparse
import json
import asyncio
import secrets

import aiopoke
from load_dotenv import load_dotenv
import yaml

from pokegrid_solver import constraints
from pokegrid_solver.pokeapi_constants import PokeAPIConstants
import pokegrid_solver.strategy as strategies
from pokegrid_solver.solver import PokegridSolver

load_dotenv()

def generate_hex_id(n_bytes: int = 16) -> str:
    """Return a cryptographically secure hex ID (0-9, a-f)."""
    return secrets.token_hex(n_bytes)


def build_constraints(items):
    result = []
    for item in items:
        cls = getattr(constraints, item["type"])
        args = item.get("args", [])
        kwargs = item.get("kwargs", {})
        result.append(cls(*args, **kwargs))
    return result


def build_strategy(cfg):
    cls = getattr(strategies, cfg["name"])
    params = cfg.get("params", {})
    if params:
        m_cls = cls(**params)
    else:
        m_cls = cls()
    return m_cls, cfg["name"], params


async def entrypoint(config_path, log_path):
    with open(config_path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    
    pokegrid_id = cfg["pokegrid_id"]
    run_id = generate_hex_id(10)

    row_constraints = build_constraints(cfg["rows"])
    column_constraints = build_constraints(cfg["columns"])
    strategy, strategy_name, strategy_params = build_strategy(cfg["strategy"])

    results = []

    async with aiopoke.AiopokeClient() as client:
        solver = PokegridSolver(row_constraints, column_constraints, strategy, client)

        for i in range(3):
            for j in range(3):
                suggestions, possible_answers = await solver.suggest_for_constraint(i, j, top_n=10)
                if not suggestions:
                    print(f"\nCell ({i}, {j}) - no suggestions")
                    continue
                
                top_pokemon, top_score = suggestions[0]
                solver.choose_pokemon(top_pokemon)

                print(f"\nCell ({i}, {j}) - {row_constraints[i]} / {column_constraints[j]}")
                print("Top candidates:")
                for rank, (name, score) in enumerate(suggestions[:10], 1):
                    print(f"{rank:2}. {name:20} {score:6.3f}")
                print(f"Suggested: {top_pokemon} (score: {top_score:.3f})")

                actual = input("Actual score for this cell (blank to skip): ").strip()
                actual_score = float(actual) if actual else None

                results.append(
                    {   
                        "run_id": run_id,
                        "pokegrid_id": pokegrid_id,
                        "row": i,
                        "col": j,
                        "row_constraint": repr(row_constraints[i]),
                        "column_constraint": repr(column_constraints[j]),
                        "possible_answer_count": possible_answers,
                        "suggested_pokemon": top_pokemon,
                        "suggested_score": top_score,
                        "actual_score": actual_score,
                        "strategy": strategy_name,
                        "strategy_params": strategy_params,
                    }
                )


        # Notes to self:
        # probably two good metrics are average delta between top ranked player rarity score for a given pokegrid and also the most common rarity score
        # probably also want to factor in how many options are available in total.
        # (1 - (actual) / 100) * (1 / sqrt(count of possible answers))

    if results:
        with open(log_path, "a", encoding="utf-8") as f:
            for r in results:
                f.write(json.dumps(r) + "\n")

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="pokegrid_experiment.yml")
    parser.add_argument("--log", default="pokegrid_experiments.jsonl")
    args = parser.parse_args()
    asyncio.run(entrypoint(args.config, args.log))
