from dataclasses import dataclass, replace


@dataclass(frozen=True)
class PipelineConfig:
    # autocrop
    crop_blur_kernel: int = 5
    crop_threshold: int = 200
    crop_margin_px: int = 20

    # perspective
    perspective_enabled: bool = True
    hough_threshold: int = 80
    hough_min_line_length: int = 100
    hough_max_line_gap: int = 10

    # background cleanup
    bg_adaptive_block_size: int = 51
    bg_adaptive_c: int = 8

    # contrast
    contrast_clip_limit: float = 2.0
    contrast_tile_size: int = 8
    ink_darkness_floor: int = 40
    white_ceiling: int = 220

    # output
    output_dpi: int = 300
    output_format: str = "PNG"

    def with_overrides(self, **kwargs) -> "PipelineConfig":
        return replace(self, **kwargs)
