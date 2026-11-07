from pathlib import Path
from time import perf_counter

import pandas as pd


class AnalysisService:
    BASKET = {"P04": 1, "P12": 1, "P14": 2, "P15": 1, "P28": 1}
    WATCH_GAP_PERCENT = 10.0
    BLACK_FRIDAY_START = "2025-11-24"
    BLACK_FRIDAY_END = "2025-11-30"

    def __init__(self, output_dir: Path, watch_gap_percent: float = WATCH_GAP_PERCENT):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.watch_gap_percent = self._validate_watch_gap(watch_gap_percent)

    def compare(self, catalogue: pd.DataFrame, offers: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
        # Seules les offres disponibles avec un prix exploitable entrent dans le classement.
        valid = offers[offers["available"] & offers["price_fcfa"].notna()].copy()
        # Le tri puis le dédoublonnage gardent le meilleur prix disponible de chaque boutique.
        valid = valid.sort_values("price_fcfa").drop_duplicates(["product_id", "store"], keep="first")

        # Index en mémoire : produit_id -> {boutique: prix}.
        prix_par_produit: dict[str, dict[str, float]] = {}
        for offer in valid.to_dict("records"):
            product_id = str(offer["product_id"])
            store = str(offer["store"])
            prix_par_produit.setdefault(product_id, {})[store] = float(offer["price_fcfa"])

        rows = []
        catalog = catalogue.set_index("produit_id")
        for product_id, store_prices in prix_par_produit.items():
            if len(store_prices) < 2:
                continue

            values = list(store_prices.values())
            low, high = min(values), max(values)
            winners = [store for store, price in store_prices.items() if price == low]
            item = {"produit_id": product_id, "produit": catalog.loc[product_id, "nom"], "boutiques_comparees": len(values)}
            for store in ("Marché Lagune", "Baobab Shop", "Comptoir Ivoire"):
                item[f"prix_{self._slug(store)}_fcfa"] = store_prices.get(store)
            item.update({
                "prix_moyen_fcfa": round(sum(values) / len(values), 2),
                "prix_min_fcfa": low,
                "prix_max_fcfa": high,
                "meilleure_boutique": " / ".join(winners),
                "ecart_fcfa": round(high - low, 2),
                "ecart_pct": round((high - low) / low * 100, 2) if low else None,
                "a_surveiller": "Oui" if low and (high - low) / low * 100 >= self.watch_gap_percent else "Non",
            })
            rows.append(item)
        result = pd.DataFrame(rows).sort_values(["ecart_pct", "produit_id"], ascending=[False, True])
        summary = self._summary(result)
        result.to_csv(self.output_dir / "comparatif.csv", index=False, encoding="utf-8-sig")
        summary.to_csv(self.output_dir / "synthese.csv", index=False, encoding="utf-8-sig")
        return result, summary

    def _summary(self, comparison: pd.DataFrame) -> pd.DataFrame:
        rows = []
        stores = ("Marché Lagune", "Baobab Shop", "Comptoir Ivoire")
        winner_col = "meilleure_boutique"
        for store in stores:
            price_col = f"prix_{self._slug(store)}_fcfa"
            premiums = []
            if not comparison.empty and price_col in comparison:
                for _, item in comparison.iterrows():
                    price = item[price_col]
                    if pd.notna(price) and item["prix_min_fcfa"]:
                        premiums.append((price - item["prix_min_fcfa"]) / item["prix_min_fcfa"] * 100)
            wins = int(comparison[winner_col].str.split(" / ").apply(lambda xs: store in xs).sum()) if not comparison.empty else 0
            rows.append({
                "boutique": store,
                "nombre_de_produits_les_moins_chers": wins,
                "ecart_moyen_au_minimum_pct": round(sum(premiums) / len(premiums), 2) if premiums else None,
                "prix_moyen_sur_produits_comparables_fcfa": round(comparison[price_col].mean(), 2) if not comparison.empty and price_col in comparison else None,
            })
        return pd.DataFrame(rows)

    def coverage(self, catalogue: pd.DataFrame, offers: pd.DataFrame) -> pd.DataFrame:
        """Explique pourquoi les références du catalogue ne sont pas comparables."""
        valid = offers[offers["available"] & offers["price_fcfa"].notna()]
        valid_stores = valid.groupby("product_id")["store"].nunique().to_dict()
        rows = []

        for product in catalogue.itertuples(index=False):
            product_id = str(product.produit_id)
            if valid_stores.get(product_id, 0) >= 2:
                continue

            product_offers = offers[offers["product_id"] == product_id]
            reasons = set()
            for store in ("Marché Lagune", "Baobab Shop", "Comptoir Ivoire"):
                store_offers = product_offers[product_offers["store"] == store]
                if store_offers.empty:
                    reasons.add("Non référencé dans une boutique")
                elif not (store_offers["available"] & store_offers["price_fcfa"].notna()).any():
                    if store_offers["price_fcfa"].isna().any():
                        reasons.add("Prix manquant")
                    if store_offers["availability_reason"].eq("Rupture de stock").any():
                        reasons.add("Rupture de stock")

            rows.append({
                "produit_id": product_id,
                "produit": str(product.nom),
                "boutiques_avec_offre_valide": f"{valid_stores.get(product_id, 0)}/3",
                "raison": "; ".join(sorted(reasons)) or "Moins de deux offres valides",
            })

        return pd.DataFrame(rows, columns=["produit_id", "produit", "boutiques_avec_offre_valide", "raison"])

    def basket(self, catalogue: pd.DataFrame, offers: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
        valid = offers[offers["available"] & offers["price_fcfa"].notna()]
        valid = valid.sort_values("price_fcfa").drop_duplicates(["product_id", "store"])
        catalog = catalogue.set_index("produit_id")
        detail = []
        for product_id, quantity in self.BASKET.items():
            matches = valid[valid["product_id"] == product_id]
            if matches.empty:
                product_offers = offers[offers["product_id"] == product_id]
                has_stockout = product_offers["availability_reason"].eq("Rupture de stock").any()
                status = "Rupture de stock" if has_stockout else "Aucun prix valide"
                detail.append({"produit_id": product_id, "produit": catalog.loc[product_id, "nom"], "quantite": quantity, "meilleure_boutique": status, "prix_unitaire_fcfa": None, "total_fcfa": None})
                continue
            best = matches.iloc[0]
            detail.append({"produit_id": product_id, "produit": catalog.loc[product_id, "nom"], "quantite": quantity, "meilleure_boutique": best["store"], "prix_unitaire_fcfa": best["price_fcfa"], "total_fcfa": best["price_fcfa"] * quantity})
        detail_df = pd.DataFrame(detail)
        totals = []
        for store in ("Marché Lagune", "Baobab Shop", "Comptoir Ivoire"):
            total, missing = 0.0, []
            for product_id, quantity in self.BASKET.items():
                entry = valid[(valid["product_id"] == product_id) & (valid["store"] == store)]
                if entry.empty:
                    missing.append(product_id)
                else:
                    total += float(entry.iloc[0]["price_fcfa"]) * quantity
            totals.append({"boutique": store, "cout_panier_fcfa": total if not missing else None, "statut": "Complet" if not missing else "Incomplet: " + ", ".join(missing)})
        detail_df.to_csv(self.output_dir / "panier_detail.csv", index=False, encoding="utf-8-sig")
        totals_df = pd.DataFrame(totals)
        totals_df.to_csv(self.output_dir / "panier_par_boutique.csv", index=False, encoding="utf-8-sig")
        return detail_df, totals_df

    def history(self, history_path: Path) -> tuple[pd.DataFrame, dict]:
        # Une seule lecture du CSV; les recherches suivantes utilisent l'index construit en mémoire.
        start = perf_counter()
        history = pd.read_csv(history_path, parse_dates=["date"], dtype={"source": "category", "produit_id": "category"})
        read_seconds = perf_counter() - start
        history["source_norm"] = history["source"].astype(str).str.strip()
        black = history[history["date"].between(self.BLACK_FRIDAY_START, self.BLACK_FRIDAY_END)]
        year_avg = history.groupby("source_norm", observed=True)["prix_fcfa"].mean()
        bf_avg = black.groupby("source_norm", observed=True)["prix_fcfa"].mean()
        rows = []
        for store, annual in year_avg.items():
            bf = float(bf_avg.get(store)) if store in bf_avg.index else None
            rows.append({"boutique": store, "moyenne_annuelle_fcfa": round(float(annual), 2), "moyenne_semaine_black_friday_fcfa": round(bf, 2) if bf is not None else None, "difference_fcfa": round(bf - float(annual), 2) if bf is not None else None, "variation_pct": round((bf - float(annual)) / float(annual) * 100, 2) if bf is not None and annual else None})
        result = pd.DataFrame(rows).sort_values("variation_pct")
        result.to_csv(self.output_dir / "historique_black_friday.csv", index=False, encoding="utf-8-sig")

        # Construction d'un index en une passe de regroupement; clé (boutique, produit).
        t0 = perf_counter()
        index = {(str(source), str(pid)): group["prix_fcfa"].to_numpy() for (source, pid), group in history.groupby(["source_norm", "produit_id"], observed=True, sort=False)}
        build_seconds = perf_counter() - t0
        keys = list(index)
        t0 = perf_counter()
        fast_count = sum(len(index[key]) for key in keys)
        indexed_seconds = perf_counter() - t0
        t0 = perf_counter()
        naive_count = sum(1 for source, pid in keys for _ in history[(history["source_norm"] == source) & (history["produit_id"].astype(str) == pid)].itertuples())
        naive_seconds = perf_counter() - t0
        perf = {"lignes_historique": int(len(history)), "cles_indexees": len(index), "lecture_unique_secondes": round(read_seconds, 6), "construction_index_secondes": round(build_seconds, 6), "recherche_indexee_secondes": round(indexed_seconds, 6), "recherche_naive_boucles_secondes": round(naive_seconds, 6), "lignes_recuperees_indexees": fast_count, "lignes_recuperees_naives": naive_count, "complexite_index": "O(H + Q) temps, O(H) mémoire", "complexite_naive": "O(H × Q) temps", "equivalence": fast_count == naive_count == len(history)}
        pd.DataFrame([perf]).to_json(self.output_dir / "performance.json", orient="records", indent=2, force_ascii=False)
        return result, perf

    def write_cleaning_journal(self, issues: list[dict]) -> pd.DataFrame:
        journal = pd.DataFrame(issues, columns=["boutique", "type", "element", "detail"])
        if not journal.empty:
            journal.to_csv(self.output_dir / "journal_nettoyage.csv", index=False, encoding="utf-8-sig")
        else:
            journal.to_csv(self.output_dir / "journal_nettoyage.csv", index=False, encoding="utf-8-sig")
        return journal

    def write_text_report(self, catalogue, comparison, summary, basket_detail, basket_totals, history, performance, journal):
        lines = ["RAPPORT DU COMPARATEUR DE PRIX", "Données fictives fournies pour l'exercice.", ""]
        lines.append(f"Produits comparables (au moins deux boutiques disponibles) : {len(comparison)}")
        lines.append("Boutiques les plus souvent les moins chères :")
        for row in summary.itertuples():
            lines.append(f"- {row.boutique}: {row.nombre_de_produits_les_moins_chers} fois; écart moyen au minimum {row.ecart_moyen_au_minimum_pct}%")
        lines.append("\nTop 3 des écarts à comparer :")
        for row in comparison.head(3).itertuples():
            lines.append(f"- {row.produit_id} {row.produit}: écart {row.ecart_fcfa:,.0f} FCFA ({row.ecart_pct:.1f}%), minimum chez {row.meilleure_boutique}")
        lines.append("\nPanier demandé :")
        for row in basket_totals.itertuples():
            amount = f"{row.cout_panier_fcfa:,.0f} FCFA" if pd.notna(row.cout_panier_fcfa) else "non calculable: " + row.statut
            lines.append(f"- {row.boutique}: {amount}")
        if not basket_detail.empty and basket_detail["total_fcfa"].notna().all():
            lines.append(f"- Panier mixte au meilleur prix par article: {basket_detail['total_fcfa'].sum():,.0f} FCFA")
        lines.append("\nHistorique (moyenne Black Friday comparée à la moyenne annuelle) :")
        for row in history.itertuples():
            lines.append(f"- {row.boutique}: {row.moyenne_semaine_black_friday_fcfa:,.0f} vs {row.moyenne_annuelle_fcfa:,.0f} FCFA; variation {row.variation_pct:+.2f}%")
        lines.append("\nPerformance :")
        lines.extend([
            f"- Une lecture du fichier: {performance['lignes_historique']} lignes en {performance['lecture_unique_secondes']:.6f} s",
            f"- Index mémoire: {performance['cles_indexees']} clés construit en {performance['construction_index_secondes']:.6f} s",
            f"- Recherche naïve: {performance['recherche_naive_boucles_secondes']:.6f} s; recherche par index: {performance['recherche_indexee_secondes']:.6f} s",
            f"- Complexité: index O(H + Q), mémoire O(H); scans imbriqués O(H × Q).",
            f"- Journal de nettoyage: {len(journal)} événements.",
            f"- Seuil de surveillance choisi: écart relatif d'au moins {self.watch_gap_percent:g}%.",
        ])
        (self.output_dir / "rapport_resultats.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

    @staticmethod
    def _validate_watch_gap(value: float) -> float:
        value = float(value)
        if not 0 <= value <= 100:
            raise ValueError("Le seuil doit être compris entre 0 et 100 %.")
        return value

    @staticmethod
    def _slug(store: str) -> str:
        return {"Marché Lagune": "marche_lagune", "Baobab Shop": "baobab_shop", "Comptoir Ivoire": "comptoir_ivoire"}[store]

