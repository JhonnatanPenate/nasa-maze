import numpy as np

from app.core.domain.color_ramp import ColorRamp
from app.core.ports.image_encoder import ImageEncoder
from app.core.ports.raster_repository import RasterRepository
from app.features.layer_render.domain.rendered_layer import RenderedLayer

_DEFAULT_COLORMAP = "viridis"
_EMPTY_RANGE = (0.0, 1.0)


class RenderLayer:
    """Renders one whole band as a georeferenced RGBA PNG.

    Reads the band once, stretches finite values over the configured
    BandInfo.value_range (else the band's finite min/max; a defined
    (0, 1) fallback when the band has no finite cells) and encodes the
    ramp output through the ImageEncoder port. The `colormap` argument
    overrides the configured BandInfo.colormap.
    """

    def __init__(
        self, repository: RasterRepository, encoder: ImageEncoder
    ) -> None:
        self._repository = repository
        self._encoder = encoder

    def execute(
        self, dataset: str, band: str, colormap: str | None = None
    ) -> RenderedLayer:
        metadata = self._repository.metadata(dataset)
        band_info = metadata.band(band)
        ramp_name = (
            colormap
            if colormap is not None
            else band_info.colormap or _DEFAULT_COLORMAP
        )
        ramp = ColorRamp(ramp_name)
        cells = self._repository.read_cells(
            dataset, band_info.name, slice(None), slice(None)
        )
        low, high = self._value_range(band_info.value_range, cells)
        rgba = ramp.render(cells, low, high)
        return RenderedLayer(
            png=self._encoder.encode(rgba),
            bounds=metadata.bounds,
            crs=metadata.crs,
            value_range=(low, high),
        )

    @staticmethod
    def _value_range(
        configured: tuple[float, float] | None, cells: np.ndarray
    ) -> tuple[float, float]:
        if configured is not None:
            return float(configured[0]), float(configured[1])
        finite = cells[np.isfinite(cells)]
        if finite.size == 0:
            return _EMPTY_RANGE
        return float(finite.min()), float(finite.max())
