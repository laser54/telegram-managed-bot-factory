def token_shaped_sentinel(label: str) -> str:
    """Build a recognisable non-credential without embedding the shape in artifacts."""
    return "123456789" + ":" + (label + "X" * 32)[:32]
