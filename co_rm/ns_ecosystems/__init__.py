__all__ = ["run_comap_single_levels", "run_cs_bivariate_all_layers"]


def __getattr__(name: str):
	if name == "run_comap_single_levels":
		from .execution_comap import run_comap_single_levels

		return run_comap_single_levels
	if name == "run_cs_bivariate_all_layers":
		from .execution import run_cs_bivariate_all_layers

		return run_cs_bivariate_all_layers
	raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
