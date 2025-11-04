from pokegrid_solver.monkeypatch_aiopoke import patch_all
patch_all()

import pytest
import pytest_asyncio
import aiopoke

from pokegrid_solver.constraints import (
    PokemonHasType,
    PokemonIsMonotype,
    PokemonIsDualType, 
    PokemonResistantToType,
    PokemonWeakToType,
    PokemonNeutralToType,
    PokemonFirstEvolutionLine,
    PokemonMiddleEvolutionLine,
    PokemonFinalEvolutionLine,
    PokemonNoEvolutionLine,
    PokemonIsLegendaryMythical,
    PokemonCanLearnMove,
    PokemonFirstSeenInGeneration,
    PokemonShorterThan,
    PokemonTallerThan,
    PokemonCanMegaEvolve,
    PokemonIsMegaEvolution,
    PokemonHeavierThan,
    PokemonLighterThan,
    PokemonHighestBaseStat
)

@pytest_asyncio.fixture(loop_scope="module")
async def aiopoke_client():
    async with aiopoke.AiopokeClient() as client:
        yield client

@pytest.mark.asyncio(loop_scope="module")
async def test_pokemon_has_type(aiopoke_client):
    fire_constraint = PokemonHasType("fire")
    fire_types = await fire_constraint.determine_pkmn_set(aiopoke_client)
    assert "charmander" in fire_types
    assert "charizard" in fire_types

    assert "bulbasaur" not in fire_types
    assert "lugia" not in fire_types

@pytest.mark.asyncio(loop_scope="module")
async def test_pokemon_is_monotype_no_constraint(aiopoke_client):
    monotype_constraint = PokemonIsMonotype()
    monotypes = await monotype_constraint.determine_pkmn_set(aiopoke_client)
    assert "charmander" in monotypes
    assert "arceus" in monotypes

    assert "charizard" not in monotypes
    assert "swampert" not in monotypes

@pytest.mark.asyncio(loop_scope="module")
async def test_pokemon_is_monotype_with_constraint(aiopoke_client):
    water_constraint = PokemonHasType("water")
    mono_water_constraint = PokemonIsMonotype(water_constraint)
    mono_water_types = await mono_water_constraint.determine_pkmn_set(aiopoke_client)
    assert "wailord" in mono_water_types
    assert "panpour" in mono_water_types

    assert "swampert" not in mono_water_types
    assert "charmander" not in mono_water_types

@pytest.mark.asyncio(loop_scope="module")
async def test_pokemon_is_dualtype_no_constraint(aiopoke_client):
    dual_type_constraint = PokemonIsDualType()
    dualtypes = await dual_type_constraint.determine_pkmn_set(aiopoke_client)

    assert "charizard" in dualtypes
    assert "swampert" in dualtypes

    assert "wailord" not in dualtypes
    assert "charmander" not in dualtypes


@pytest.mark.asyncio(loop_scope="module")
async def test_pokemon_is_dualtype_with_constraint(aiopoke_client):
    water_constraint = PokemonHasType("water")
    dual_water_constraint = PokemonIsDualType(water_constraint)
    dual_water_types = await dual_water_constraint.determine_pkmn_set(aiopoke_client)
    assert "swampert" in dual_water_types
    assert "greninja" in dual_water_types

    assert "wailord" not in dual_water_types
    assert "charmander" not in dual_water_types


@pytest.mark.asyncio(loop_scope="module")
async def test_pokemon_resistant_to_type(aiopoke_client):
    resist_fire = PokemonResistantToType("fire")
    result = await resist_fire.determine_pkmn_set(aiopoke_client)

    assert "squirtle" in result
    assert "geodude" in result

    assert "bulbasaur" not in result
    assert "lugia" not in result
    assert "lotad" not in result


@pytest.mark.asyncio(loop_scope="module")
async def test_pokemon_weak_to_type(aiopoke_client):
    weak_to_electric = PokemonWeakToType("electric")
    result = await weak_to_electric.determine_pkmn_set(aiopoke_client)

    assert "gyarados" in result
    assert "squirtle" in result

    assert "geodude" not in result
    assert "pikachu" not in result


@pytest.mark.asyncio(loop_scope="module")
async def test_pokemon_neutral_to_type(aiopoke_client):
    neutral_to_ghost = PokemonNeutralToType("ghost")
    result = await neutral_to_ghost.determine_pkmn_set(aiopoke_client)

    # neutral to Ghost: Fire/Electric are neutral
    assert "charmander" in result
    assert "pikachu" in result

    # NOT neutral: Normal is immune; Dark resists Ghost
    assert "snorlax" not in result
    assert "umbreon" not in result


@pytest.mark.asyncio(loop_scope="module")
async def test_pokemon_first_evolution_line(aiopoke_client):
    first_line = PokemonFirstEvolutionLine()
    result = await first_line.determine_pkmn_set(aiopoke_client)

    # base forms with evolutions
    assert "bulbasaur" in result
    assert "charmander" in result

    # NOT base-with-evolution
    assert "charmeleon" not in result
    assert "charizard" not in result
    # dont include ones with no evolution line
    assert "tauros" not in result


@pytest.mark.asyncio(loop_scope="module")
async def test_pokemon_middle_evolution_line(aiopoke_client):
    middle_line = PokemonMiddleEvolutionLine()
    result = await middle_line.determine_pkmn_set(aiopoke_client)

    # middle-stage examples
    assert "ivysaur" in result
    assert "charmeleon" in result

    # NOT middle-stage
    assert "bulbasaur" not in result
    assert "charizard" not in result
    assert "tauros" not in result


@pytest.mark.asyncio(loop_scope="module")
async def test_pokemon_final_evolution_line(aiopoke_client):
    final_line = PokemonFinalEvolutionLine()
    result = await final_line.determine_pkmn_set(aiopoke_client)

    # final-stage examples
    assert "venusaur" in result
    assert "charizard" in result
    assert "gallade" in result
    assert "gardevoir" in result

    # NOT final-stage
    assert "bulbasaur" not in result
    assert "charmeleon" not in result
    assert "kirlia" not in result
    assert "tauros" not in result


@pytest.mark.asyncio(loop_scope="module")
async def test_pokemon_no_evolution_line(aiopoke_client):
    no_evo = PokemonNoEvolutionLine()
    result = await no_evo.determine_pkmn_set(aiopoke_client)

    # single-stage species
    assert "ditto" in result
    assert "tauros" in result

    # species with evolutions
    assert "bulbasaur" not in result
    assert "charizard" not in result



@pytest.mark.asyncio(loop_scope="module")
async def test_pokemon_is_legendary_mythical(aiopoke_client):
    legend = PokemonIsLegendaryMythical()
    result = await legend.determine_pkmn_set(aiopoke_client)

    # legendary/mythical examples
    assert "lugia" in result
    assert "mew" in result

    # non-legendary
    assert "charmander" not in result
    assert "rattata" not in result


@pytest.mark.asyncio(loop_scope="module")
async def test_pokemon_can_learn_move(aiopoke_client):
    can_fly = PokemonCanLearnMove("fly")
    result = await can_fly.determine_pkmn_set(aiopoke_client)

    # common Fly learners
    assert "charizard" in result
    assert "pidgeot" in result

    # cannot learn Fly
    assert "onix" not in result
    assert "pikachu" not in result


@pytest.mark.asyncio(loop_scope="module")
async def test_pokemon_first_seen_in_generation(aiopoke_client):
    gen1 = PokemonFirstSeenInGeneration(1)
    result = await gen1.determine_pkmn_set(aiopoke_client)

    # debuted in Gen 1
    assert "bulbasaur" in result
    assert "mew" in result

    # not Gen 1
    assert "chikorita" not in result
    assert "lucario" not in result


@pytest.mark.asyncio(loop_scope="module")
async def test_pokemon_shorter_than(aiopoke_client):
    shorter_than_3ft = PokemonShorterThan(3, 0)
    result = await shorter_than_3ft.determine_pkmn_set(aiopoke_client)

    # under 3'0"
    assert "pikachu" in result
    assert "eevee" in result

    # not under 3'0"
    assert "charizard" not in result
    assert "wailord" not in result


@pytest.mark.asyncio(loop_scope="module")
async def test_pokemon_taller_than(aiopoke_client):
    taller_than_6ft = PokemonTallerThan(6, 0)
    result = await taller_than_6ft.determine_pkmn_set(aiopoke_client)

    # over 6'0"
    assert "venusaur" in result
    assert "onix" in result

    # not over 6'0"
    assert "pikachu" not in result
    assert "charmander" not in result


@pytest.mark.asyncio(loop_scope="module")
async def test_pokemon_can_mega_evolve(aiopoke_client):
    can_mega = PokemonCanMegaEvolve()
    result = await can_mega.determine_pkmn_set(aiopoke_client)

    assert "charizard" in result
    assert "rayquaza" in result

    assert "haxorus" not in result
    assert "charmander" not in result
    assert "panpour" not in result


@pytest.mark.asyncio(loop_scope="module")
async def test_pokemon_is_mega_evolution(aiopoke_client):
    is_mega = PokemonIsMegaEvolution()
    result = await is_mega.determine_pkmn_set(aiopoke_client)

    assert "charizard-mega-x" in result
    assert "scizor-mega" in result
    assert "rayquaza-mega" in result

    assert "charizard" not in result
    assert "piplup" not in result
    
@pytest.mark.asyncio(loop_scope="module")
async def test_pokemon_is_heavier_than(aiopoke_client):
    heavier_than = PokemonHeavierThan(pounds=120)
    result = await heavier_than.determine_pkmn_set(aiopoke_client)

    assert "wailord" in result
    assert "crustle" in result
    assert "kommo-o" in result

    assert "grookey" not in result
    assert "magikarp" not in result

@pytest.mark.asyncio(loop_scope="module")
async def test_pokemon_is_lighter_than(aiopoke_client):
    lighter_than = PokemonLighterThan(pounds=120)
    result = await lighter_than.determine_pkmn_set(aiopoke_client)

    assert "cubone" in result
    assert "machop" in result
    assert "ralts" in result

    assert "groudon" not in result
    assert "celesteela" not in result

@pytest.mark.asyncio(loop_scope="module")
async def test_pokemon_highest_base_stat(aiopoke_client):
    defense_best = PokemonHighestBaseStat("defense")
    result = await defense_best.determine_pkmn_set(aiopoke_client)

    assert "cobalion" in result
    assert "stakataka" in result
    
    assert "pichu" not in result
    assert "goomy" not in result

