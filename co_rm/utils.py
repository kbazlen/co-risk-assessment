import re

def extract_gwl(filename):
    """Pull a GWL label like '2C' or '1.5C' out of a tif filename. Returns None if not found."""
    match = re.search(r'GWL([\d.]+)C', filename)
    if match:
        return f"{match.group(1)}°C"
    # fallback: check for other common patterns (e.g. ssp245, D2, etc.)
    return None
