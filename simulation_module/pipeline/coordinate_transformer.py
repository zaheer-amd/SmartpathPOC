def transform_bbox(bounding_box_1000: list[int]) -> dict:
    """
    Converts Gemini [ymin, xmin, ymax, xmax] on a 0-1000 scale
    to CSS percentage coordinates {top, left, width, height}.
    
    Args:
        bounding_box_1000: List of 4 ints [ymin, xmin, ymax, xmax], each 0-1000.
    
    Returns:
        Dict with keys: "top", "left", "width", "height" — all float percentages.
    
    Raises:
        ValueError: If input is not exactly 4 elements or values out of range.
    """
    if len(bounding_box_1000) != 4:
        raise ValueError(f"Expected 4-element list, got {len(bounding_box_1000)}")
    
    ymin, xmin, ymax, xmax = bounding_box_1000
    
    # Validate ranges
    for name, val in [("ymin", ymin), ("xmin", xmin), ("ymax", ymax), ("xmax", xmax)]:
        if not (0 <= val <= 1000):
            raise ValueError(f"{name}={val} is out of range [0, 1000]")
    
    if ymax <= ymin:
        raise ValueError(f"ymax ({ymax}) must be > ymin ({ymin})")
    if xmax <= xmin:
        raise ValueError(f"xmax ({xmax}) must be > xmin ({xmin})")
    
    return {
        "top":    round((ymin / 1000) * 100, 2),
        "left":   round((xmin / 1000) * 100, 2),
        "width":  round(((xmax - xmin) / 1000) * 100, 2),
        "height": round(((ymax - ymin) / 1000) * 100, 2),
    }
