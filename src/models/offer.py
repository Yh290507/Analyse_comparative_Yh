from dataclasses import dataclass


@dataclass(frozen=True)
class Offer:
    """Offre normalisée issue d'une boutique."""

    product_id: str
    product_name: str
    store: str
    price_fcfa: float | None
    available: bool
    source_label: str = ""
    original_name: str = ""
    availability_reason: str = ""

