__all__ = ["run_comap_single_levels"]


def __getattr__(name: str):
	if name == "run_comap_single_levels":
		from .execution import run_comap_single_levels

		return run_comap_single_levels
	raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
