import json
from dataclasses import asdict
from pathlib import Path

import pandas as pd

from src.models.offer import Offer


class DataRepository:
    """Lit chaque source et remet les offres dans un format tabulaire commun."""

    STORES = ("Marché Lagune", "Baobab Shop", "Comptoir Ivoire")

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.issues: list[dict] = []
        self.source_counts: list[dict[str, int | str]] = []

    def load_catalogue(self) -> pd.DataFrame:
        return pd.read_csv(self.data_dir / "catalogue_reference.csv", dtype=str, keep_default_na=False)

    def load_offers(self, catalogue: pd.DataFrame) -> pd.DataFrame:
        self.issues = []
        frames = [self._load_marche(), self._load_baobab(), self._load_comptoir()]
        self.source_counts = [
            {"fichier": filename, "lignes_lues": len(frame)}
            for filename, frame in zip(
                ("marche_lagune.csv", "baobab_shop.json", "comptoir_ivoire.xlsx"),
                frames,
            )
        ]
        offers = pd.concat(frames, ignore_index=True)
        offers["product_id"] = offers["product_name_raw"].map(self._match_product)
        for row in offers[offers["product_id"].isna()].itertuples():
            self._issue(row.store, "Rapprochement", row.product_name_raw, "Nom non rapproché au catalogue")
        offers = offers.dropna(subset=["product_id"]).copy()
        names = catalogue.set_index("produit_id")["nom"].to_dict()
        offers["product_name"] = offers["product_id"].map(names)
        for product_id, group in offers[offers["price_fcfa"].notna()].groupby("product_id"):
            values = sorted(float(x) for x in group["price_fcfa"] if float(x) > 0)
            if len(values) >= 2 and values[-1] > values[0] * 3:
                high_index = group.index[group["price_fcfa"] == values[-1]]
                high = offers.loc[high_index[0]]
                self._issue(
                    high["store"],
                    "Prix atypique",
                    high["product_name_raw"],
                    f"{values[-1]:,.0f} FCFA dépasse de plus de 3 fois l'offre la moins chère "
                    f"({values[0]:,.0f} FCFA); anomalie signalée pour vérification. "
                    "La valeur source est conservée telle quelle et reste incluse dans le comparatif.",
                )
        # Repère les entrées répétées. Les valeurs identiques sont ensuite regroupées.
        duplicated = offers.duplicated(["store", "product_id"], keep=False)
        for row in offers[duplicated].itertuples():
            self._issue(row.store, "Doublon", row.product_name_raw, "Plusieurs lignes pour le même produit; l'offre disponible la moins chère sera retenue")
        # Le modèle métier Offer fixe les champs communs avant le traitement tabulaire.
        normalized_offers = []
        for row in offers.to_dict("records"):
            price = row["price_fcfa"]
            normalized_offers.append(asdict(Offer(
                product_id=str(row["product_id"]),
                product_name=str(row["product_name"]),
                store=str(row["store"]),
                price_fcfa=None if pd.isna(price) else float(price),
                available=bool(row["available"]),
                source_label=str(row["source_label"]),
                original_name=str(row["product_name_raw"]),
                availability_reason=str(row.get("availability_reason", "")),
            )))
        return pd.DataFrame(normalized_offers)

    def _load_marche(self) -> pd.DataFrame:
        path = self.data_dir / "marche_lagune.csv"
        df = pd.read_csv(path, sep=";", dtype=str, keep_default_na=False, encoding="utf-8-sig")
        rows = []
        for row in df.to_dict("records"):
            price = self._parse_price(row.get("prix"))
            status = self._text(row.get("disponibilite"))
            reason = "Rupture de stock" if status == "rupture" else ""
            available = not reason and price is not None
            if price is None:
                self._issue("Marché Lagune", "Prix manquant", row.get("designation", ""), f"Prix inexploitable: {row.get('prix', '') or '(vide)'}")
            if status == "rupture":
                self._issue("Marché Lagune", "Rupture de stock", row.get("designation", ""), "Produit indiqué en rupture de stock dans la source")
            rows.append(self._row("Marché Lagune", row.get("designation", ""), price, available, row.get("reference", ""), reason))
        return pd.DataFrame(rows)

    def _load_baobab(self) -> pd.DataFrame:
        with (self.data_dir / "baobab_shop.json").open(encoding="utf-8") as file:
            payload = json.load(file)
        rows = []
        for item in payload.get("items", []):
            pricing = item.get("pricing") or {}
            price = self._parse_price(pricing.get("amount"))
            fee = self._parse_price(pricing.get("delivery_fee")) or 0
            stock = self._parse_price(item.get("stock")) or 0
            title = item.get("title", "")
            reason = "Rupture de stock" if stock <= 0 else ""
            if price is None:
                self._issue("Baobab Shop", "Prix manquant", title, "Montant absent ou inexploitable")
            if stock <= 0:
                self._issue("Baobab Shop", "Rupture de stock", title, "Stock nul dans la source")
            rows.append(self._row("Baobab Shop", title, price + fee if price is not None else None, price is not None and stock > 0, item.get("sku", ""), reason))
        return pd.DataFrame(rows)

    def _load_comptoir(self) -> pd.DataFrame:
        df = pd.read_excel(self.data_dir / "comptoir_ivoire.xlsx", sheet_name="Tarifs octobre 2026", header=2)
        rows = []
        for row in df.to_dict("records"):
            name = str(row.get("Article", ""))
            raw_price = row.get("Prix catalogue (FCFA)")
            price = self._parse_price(raw_price)
            discount = self._parse_price(row.get("Remise (%)")) or 0
            quantity = self._parse_price(row.get("Quantité en rayon")) or 0
            net = round(price * (1 - discount / 100), 2) if price is not None else None
            reason = "Rupture de stock" if quantity <= 0 else ""
            if price is None:
                self._issue("Comptoir Ivoire", "Prix manquant", name, "Prix catalogue absent ou inexploitable")
            if quantity <= 0:
                self._issue("Comptoir Ivoire", "Rupture de stock", name, "Quantité en rayon nulle dans la source")
            rows.append(self._row("Comptoir Ivoire", name, net, price is not None and quantity > 0, str(row.get("Code", "")), reason))
        return pd.DataFrame(rows)

    @staticmethod
    def _row(store, name, price, available, label, availability_reason=""):
        return {"store": store, "product_name_raw": str(name), "price_fcfa": price, "available": bool(available), "source_label": str(label), "availability_reason": availability_reason}

    @staticmethod
    def _text(value) -> str:
        return " ".join(str(value or "").strip().lower().split())

    @staticmethod
    def _parse_price(value):
        if value is None or pd.isna(value):
            return None
        if isinstance(value, (int, float)):
            return float(value) if value > 0 else None
        digits = "".join(ch for ch in str(value) if ch.isdigit())
        return float(digits) if digits else None

    def _match_product(self, raw_name: str):
        name = self._normalise(raw_name)
        rules = [
            ("P01", ("galaxy a15", "samsun galaxy a15")), ("P02", ("galaxy a25", "samsung a25")),
            ("P03", ("galaxy a55",)), ("P04", ("spark 20",)), ("P05", ("camon 30",)),
            ("P06", ("hot 40i",)), ("P07", ("note 40",)), ("P08", ("itel a70",)),
            ("P09", ("iphone 13",)), ("P10", ("redmi note 13",)),
            ("P11", ("hp 250 g9", "250 g9")), ("P12", ("lenovo ideapad 3",)),
            ("P13", ("dell inspiron 15",)), ("P14", ("sandisk", "cle usb sandisk")),
            ("P15", ("seagate",)), ("P16", ("logitech m185",)),
            ("P17", ("deskjet 2720e",)), ("P18", ("archer c6",)),
            ("P19", ("samsung 24", "ecran samsung 24")),
            ("P20", ("hisense 205", "hisense fridge 205", "fridge 205")), ("P21", ("nasco 200",)),
            ("P22", ("samsung 43",)), ("P23", ("hisense 32",)),
            ("P24", ("clim lg 1cv", "lg air conditioner 1hp", "climatiseur lg 1cv")),
            ("P25", ("binatone 16",)), ("P26", ("moulinex",)),
            ("P27", ("philips",)), ("P28", ("microwave 23", "micro ondes samsung 23")),
            ("P29", ("kettle 1 7", "bouilloire 1 7")), ("P30", ("hisense air conditioner 1 5", "climatiseur hisense 1 5")),
        ]
        for product_id, aliases in rules:
            if any(self._normalise(alias) in name for alias in aliases):
                return product_id
        return None

    @staticmethod
    def _normalise(value: str) -> str:
        import re
        import unicodedata
        value = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode("ascii").lower()
        value = re.sub(r"[^a-z0-9]+", " ", value)
        return " ".join(value.split())

    def _issue(self, store, category, item, details):
        self.issues.append({"boutique": store, "type": category, "element": str(item), "detail": details})

