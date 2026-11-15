from dataclasses import dataclass

from app.core.domain.grid_geometry import GridGeometry
from app.core.errors.exceptions import RasterValidationError

_FIELDS = (
    "row_start",
    "row_stop",
    "col_start",
    "col_stop",
    "core_row_start",
    "core_row_stop",
    "core_col_start",
    "core_col_stop",
)


@dataclass(frozen=True)
class CellWindow:
    """The outer cell range actually returned and the core range inside it.

    Ranges are in grid coordinates and may fall outside the grid (a
    point+radius read pads out-of-extent cells); bbox reads clip the halo
    to the grid via ``with_halo``. The core is the sub-range a plain bbox
    read would return; on point reads the core equals the outer range.
    """

    row_start: int
    row_stop: int
    col_start: int
    col_stop: int
    core_row_start: int
    core_row_stop: int
    core_col_start: int
    core_col_stop: int

    def __post_init__(self) -> None:
        for name in _FIELDS:
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int):
                raise RasterValidationError(
                    f"CellWindow field {name} must be an int, got {value!r}"
                )
        if self.row_stop <= self.row_start or self.col_stop <= self.col_start:
            raise RasterValidationError(
                "CellWindow outer range must be non-empty, got "
                f"rows {self.row_start}:{self.row_stop}, "
                f"cols {self.col_start}:{self.col_stop}"
            )
        if (
            self.core_row_stop <= self.core_row_start
            or self.core_col_stop <= self.core_col_start
        ):
            raise RasterValidationError("CellWindow core range must be non-empty")
        if not (
            self.row_start <= self.core_row_start
            and self.core_row_stop <= self.row_stop
            and self.col_start <= self.core_col_start
            and self.core_col_stop <= self.col_stop
        ):
            raise RasterValidationError(
                "CellWindow core range must lie inside the outer range"
            )

    @classmethod
    def with_halo(
        cls,
        row_start: int,
        row_stop: int,
        col_start: int,
        col_stop: int,
        halo_cells: int,
        grid_rows: int,
        grid_cols: int,
    ) -> "CellWindow":
        """Core range expanded by halo_cells on every side, clipped to the
        grid; the core keeps the unexpanded range."""
        GridGeometry.window_size(halo_cells)  # validates halo_cells
        return cls(
            row_start=max(row_start - halo_cells, 0),
            row_stop=min(row_stop + halo_cells, grid_rows),
            col_start=max(col_start - halo_cells, 0),
            col_stop=min(col_stop + halo_cells, grid_cols),
            core_row_start=row_start,
            core_row_stop=row_stop,
            core_col_start=col_start,
            core_col_stop=col_stop,
        )

    @classmethod
    def around(
        cls, center_row: int, center_col: int, radius_cells: int
    ) -> "CellWindow":
        """(2*radius+1)^2 window centred on a cell; not clipped, so the
        range may extend past the grid edges (padding)."""
        size = GridGeometry.window_size(radius_cells)  # validates radius_cells
        row_start = center_row - radius_cells
        col_start = center_col - radius_cells
        row_stop = row_start + size
        col_stop = col_start + size
        return cls(
            row_start=row_start,
            row_stop=row_stop,
            col_start=col_start,
            col_stop=col_stop,
            core_row_start=row_start,
            core_row_stop=row_stop,
            core_col_start=col_start,
            core_col_stop=col_stop,
        )

    @property
    def rows(self) -> int:
        return self.row_stop - self.row_start

    @property
    def cols(self) -> int:
        return self.col_stop - self.col_start

    @property
    def core_rows(self) -> int:
        return self.core_row_stop - self.core_row_start

    @property
    def core_cols(self) -> int:
        return self.core_col_stop - self.core_col_start

    @property
    def row_off(self) -> int:
        return self.core_row_start - self.row_start

    @property
    def col_off(self) -> int:
        return self.core_col_start - self.col_start

    @property
    def rows_slice(self) -> slice:
        return slice(self.row_start, self.row_stop)

    @property
    def cols_slice(self) -> slice:
        return slice(self.col_start, self.col_stop)

    @property
    def core_slice(self) -> tuple[slice, slice]:
        """Slice selecting the core inside the returned (outer) array."""
        return (
            slice(self.row_off, self.row_off + self.core_rows),
            slice(self.col_off, self.col_off + self.core_cols),
        )

    def outer_bounds(
        self, geometry: GridGeometry
    ) -> tuple[float, float, float, float]:
        """(min_lon, min_lat, max_lon, max_lat) of the outer cell edges.

        Returned unvalidated: a padded point+radius window may cross the
        poles or the antimeridian and must not raise (point reads never
        fail for coverage)."""
        e = geometry.extent
        return (
            e.min_lon + self.col_start * geometry.res_lon_deg,
            e.max_lat - self.row_stop * geometry.res_lat_deg,
            e.min_lon + self.col_stop * geometry.res_lon_deg,
            e.max_lat - self.row_start * geometry.res_lat_deg,
        )
