from dataclasses import dataclass

from app.core.domain.dem_window import DemWindow
from app.core.errors.exceptions import DomainValidationError


@dataclass(frozen=True)
class HaloWindow:
    """A DemWindow read with a halo: the requested bbox window (the core)
    expanded by extra DEM rows/columns on every side, clipped at the DEM
    edge.

    `core_rows`/`core_cols` select the core inside `window`, i.e.
    `window.elevation[core_rows, core_cols]` is exactly the window a plain
    read for the same bbox would return. A core slice may touch the window
    edge where the halo ran out of DEM cells.
    """

    window: DemWindow
    core_rows: slice
    core_cols: slice

    def __post_init__(self) -> None:
        if not isinstance(self.window, DemWindow):
            raise DomainValidationError(
                f"HaloWindow window must be a DemWindow, got {self.window!r}"
            )
        for name in ("core_rows", "core_cols"):
            if not isinstance(getattr(self, name), slice):
                raise DomainValidationError(
                    f"HaloWindow {name} must be a slice, "
                    f"got {getattr(self, name)!r}"
                )

    def core(self) -> DemWindow:
        """The window without its halo — what a plain read would return."""
        return DemWindow(
            elevation=self.window.elevation[self.core_rows, self.core_cols],
            cell_size_x_m=self.window.cell_size_x_m,
            cell_size_y_m=self.window.cell_size_y_m,
        )
