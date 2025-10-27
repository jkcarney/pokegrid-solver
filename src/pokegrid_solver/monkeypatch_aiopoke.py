import importlib


def patch_evolution_detail():
    """
    Due to pokeapi.co adding extra fields and aiopoke not expecting these, we need to monkeypatch the import
    so we can handle the extra fields. Call this function to patch EvolutionDetail object. 

    This is not aiopoke's fault. pokeapi.co's documentation literally does not have the fields listed: https://pokeapi.co/docs/v2#evolution-chains
    """
    mod = importlib.import_module("aiopoke.objects.resources.evolutions.evolution_chain")
    EvolutionDetail = getattr(mod, "EvolutionDetail")

    _orig_init = EvolutionDetail.__init__


    def _new_init(self, *args, **kwargs):
        base_form_id = kwargs.pop("base_form_id", None)
        region_id = kwargs.pop("region_id", None)

        _orig_init(self, *args, **kwargs)

        if base_form_id is not None:
            setattr(self, "base_form_id", None if base_form_id is None else int(base_form_id))

        if region_id is not None:
            setattr(self, "region_id", None if region_id is None else int(region_id))

    EvolutionDetail.__init__ = _new_init


def patch_all():
    """
    Patch all disfunctional aiopoke objects.
    """
    current_module = globals()
    for name, obj in current_module.items():
        # run every function that starts with "patch_" except patch_all itself
        if callable(obj) and name.startswith("patch_") and name != "patch_all":
            obj()