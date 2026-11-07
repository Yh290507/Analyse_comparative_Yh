"""Affichage lisible des résultats et du menu console."""

import os
import sys


class ConsoleView:
    CYAN = "\033[96m"
    GOLD = "\033[93m"
    RESET = "\033[0m"
    STORES = (
        ("Marché Lagune", "marche_lagune"),
        ("Baobab Shop", "baobab_shop"),
        ("Comptoir Ivoire", "comptoir_ivoire"),
    )

    def __init__(self):
        self.color = sys.stdout.isatty() and (os.name != "nt" or "WT_SESSION" in os.environ or "TERM_PROGRAM" in os.environ)

    def menu(self) -> str:
        self._heading("COMPARATEUR DE PRIX | ABIDJAN")
        print("  1  Lancer l'analyse")
        print("  2  Voir la synthèse des boutiques")
        print("  3  Comparer un produit")
        print("  4  Comparer le panier de rentrée")
        print("  5  Voir les problèmes de données")
        print("  6  Consulter l'historique Black Friday")
        print("  7  Comprendre la méthode et la complexité")
        print("  0  Quitter")
        return input("\n  Choix : ").strip()

    def ask_watch_threshold(self, default: float) -> float:
        while True:
            raw = input(f"\n  Seuil d'alerte en % [Entrée = {default:g} %] : ").strip().replace(",", ".")
            if not raw:
                return float(default)
            try:
                value = float(raw)
            except ValueError:
                print("  Entre un nombre de 0 à 100, ou appuie sur Entrée pour garder le seuil par défaut.")
                continue
            if 0 <= value <= 100:
                return value
            print("  Le seuil doit être compris entre 0 et 100 %.")

    def show_analysis_complete(self, comparison, journal, catalogue_count, source_counts, coverage, watch_threshold):
        self._heading("ANALYSE TERMINÉE")
        watch_count = int((comparison["a_surveiller"] == "Oui").sum()) if not comparison.empty else 0
        self._section("Bilan des données")
        self._table(
            ("INDICATEUR", "NOMBRE"),
            [
                ("Produits au catalogue", str(catalogue_count)),
                ("Produits comparables (au moins 2 boutiques)", str(len(comparison))),
                ("Produits non comparables", str(len(coverage))),
                (f"À surveiller (écart ≥ {watch_threshold:g} %)", str(watch_count)),
            ],
        )
        print("  Les produits à surveiller font partie des produits comparables.")

        self._section("Fichiers chargés")
        source_rows = [("catalogue_reference.csv", str(catalogue_count))]
        source_rows.extend((item["fichier"], str(item["lignes_lues"])) for item in source_counts)
        self._table(("SOURCE", "ÉLÉMENTS LUS"), source_rows)

        self._section("Qualité des données relevée")
        issue_counts = journal["type"].value_counts().to_dict() if not journal.empty else {}
        self._table(
            ("OBSERVATION", "LIGNES"),
            [(kind, str(count)) for kind, count in sorted(issue_counts.items())]
            or [("Aucune anomalie relevée", "0")],
        )

        if not coverage.empty:
            self._section("Pourquoi certains produits sont exclus")
            rows = [
                (item.produit_id, self._short(item.produit, 27), item.boutiques_avec_offre_valide,
                 self._short(item.raison, 39))
                for item in coverage.itertuples()
            ]
            self._table(("ID", "PRODUIT", "OFFRES VALIDES", "RAISON"), rows)

        if not comparison.empty:
            largest = comparison.iloc[0]
            self._section("Point à retenir")
            print(
                f"  Plus grand écart : {largest['produit_id']} — {self._short(largest['produit'], 35)} "
                f"({self._money(largest['ecart_fcfa'])}, {self._percent(largest['ecart_pct'], 2)})."
            )

        print(f"  {len(journal)} problèmes ou observations sont inscrits au journal.")
        print("  Résultats enregistrés : comparatif, synthèse, paniers, historique et journal dans output/.")
        print("  Choisis 2 à 7 pour explorer les résultats par thème.")

    def show_summary(self, comparison, summary):
        self._heading("SYNTHÈSE DES BOUTIQUES")
        print(f"  Produits comparables : {len(comparison)}")

        rows = [
            (item.boutique, str(item.nombre_de_produits_les_moins_chers),
             self._percent(item.ecart_moyen_au_minimum_pct, 1),
             self._money(item.prix_moyen_sur_produits_comparables_fcfa))
            for item in summary.itertuples()
        ]
        self._table(("BOUTIQUE", "MEILLEUR PRIX", "SURPRIX MOYEN", "PRIX MOYEN OBSERVÉ"), rows)
        if not summary.empty:
            best = summary.sort_values("nombre_de_produits_les_moins_chers", ascending=False).iloc[0]
            print(f"  La boutique la plus souvent la moins chère : {best['boutique']}.")
            print("  Le meilleur prix peut toutefois changer selon le produit.")

        self._section("Trois plus grands écarts")
        top_rows = [
            (item.produit_id, self._short(item.produit, 24), item.meilleure_boutique,
             self._percent(item.ecart_pct, 1))
            for item in comparison.head(3).itertuples()
        ]
        self._table(("ID", "PRODUIT", "MOINS CHER", "ÉCART"), top_rows)

    def ask_product_id(self) -> str:
        return input("\n  Code produit à comparer (ex. P04) : ").strip().upper()

    def show_product(self, product, watch_threshold=10.0):
        self._heading(f"COMPARAISON DU PRODUIT {product['produit_id']}")
        print(f"  {product['produit']} · {int(product['boutiques_comparees'])} boutiques comparées")
        rows = []
        for store, slug in self.STORES:
            price = product[f"prix_{slug}_fcfa"]
            if self._is_missing(price):
                status = "Aucune offre valide"
            elif float(price) == float(product["prix_min_fcfa"]):
                status = "Meilleur prix"
            else:
                status = f"+{float(price) - float(product['prix_min_fcfa']):,.0f} FCFA".replace(",", " ")
            rows.append((store, self._money(price), status))
        self._table(("BOUTIQUE", "PRIX PAYÉ", "ÉCART AU MINIMUM"), rows)
        print(f"  Minimum : {self._money(product['prix_min_fcfa'])} · moyenne : {self._money(product['prix_moyen_fcfa'])} · maximum : {self._money(product['prix_max_fcfa'])}")
        print(f"  Écart entre le plus haut et le plus bas : {self._money(product['ecart_fcfa'])} ({self._percent(product['ecart_pct'], 2)})")
        print(f"  Meilleur prix : {product['meilleure_boutique']}")
        if product["a_surveiller"] == "Oui":
            print(f"  À surveiller : l’écart atteint le seuil choisi de {self._percent(watch_threshold, 1)}.")
        else:
            print(f"  Écart inférieur au seuil de surveillance de {self._percent(watch_threshold, 1)}.")

    def show_basket(self, detail, totals):
        self._heading("PANIER DE RENTRÉE")
        rows = [
            (item.boutique,
             self._money(item.cout_panier_fcfa) if item.statut == "Complet" else item.statut)
            for item in totals.itertuples()
        ]
        if detail["total_fcfa"].notna().all():
            rows.append(("Meilleur prix par article", self._money(detail["total_fcfa"].sum())))
        self._section("Coût total")
        self._table(("OPTION", "TOTAL"), rows)

        self._section("Où acheter chaque article au meilleur prix")
        item_rows = [
            (item.produit_id, self._short(item.produit, 27), str(item.quantite),
             self._short(item.meilleure_boutique, 18), self._money(item.prix_unitaire_fcfa),
             self._money(item.total_fcfa))
            for item in detail.itertuples()
        ]
        self._table(("ID", "ARTICLE", "QTÉ", "BOUTIQUE", "PRIX UNITAIRE", "TOTAL ARTICLE"), item_rows)

    def show_issues(self, journal):
        self._heading("QUALITÉ DES DONNÉES")
        if journal.empty:
            print("Aucun problème relevé.")
            return
        treatment = {
            "Prix manquant": "Exclu du comparatif",
            "Rupture de stock": "Exclue du classement",
            "Doublon": "Signalé; offres regroupées",
            "Prix atypique": "Signalé; prix conservé",
            "Rapprochement": "À associer au catalogue",
        }
        counts = journal.groupby("type").size()
        rows = [(kind, str(count), treatment.get(kind, "Signalé")) for kind, count in counts.items()]
        self._table(("PROBLÈME", "LIGNES", "TRAITEMENT"), rows)

        notable = journal[journal["type"].isin(["Prix atypique", "Prix manquant", "Rapprochement", "Rupture de stock"])]
        if not notable.empty:
            examples = []
            for item in notable.drop_duplicates("type").itertuples():
                examples.append((item.boutique, item.type, self._short(item.element, 30)))
            self._section("Exemples à regarder")
            self._table(("BOUTIQUE", "TYPE", "ÉLÉMENT"), examples)
        print("\n  Le détail complet est dans output/journal_nettoyage.csv.")

    def show_history(self, history):
        self._heading("HISTORIQUE BLACK FRIDAY")
        print("  Moyenne des prix du 24 au 30 novembre 2025, comparée à la moyenne annuelle.")
        rows = [
            (item.boutique, self._money(item.moyenne_annuelle_fcfa),
             self._money(item.moyenne_semaine_black_friday_fcfa),
             self._money(item.difference_fcfa),
             self._percent(item.variation_pct, 1, signed=True))
            for item in history.itertuples()
        ]
        self._table(("BOUTIQUE", "MOY. ANNUELLE", "MOY. BLACK FRIDAY", "DIFFÉRENCE", "VARIATION"), rows)

    def show_method(self, performance=None):
        self._heading("MÉTHODE ET PERFORMANCE")
        rows = [
            ("1", "Lire", "Catalogues CSV, JSON et Excel avec pandas"),
            ("2", "Nettoyer", "Uniformiser les noms et convertir les prix"),
            ("3", "Rapprocher", "Relier les offres au catalogue commun"),
            ("4", "Indexer", "Dictionnaire produit → boutique → prix"),
            ("5", "Comparer", "Minimum, moyenne et écarts en FCFA et en %"),
        ]
        self._table(("ÉTAPE", "ACTION", "RÉSULTAT"), rows)
        print("\n  H = lignes de l'historique; Q = recherches de prix (une par couple boutique-produit).")
        print("  Méthode naïve : pour chaque recherche, reparcourir les H lignes → O(H × Q) en temps.")
        print("  Avec index : lire et indexer H lignes, puis faire Q accès dictionnaire → O(H + Q) en temps.")
        print("  Mémoire de l'index : O(H), car les lignes utiles sont conservées par groupe.")
        if performance is not None:
            naive = performance["recherche_naive_boucles_secondes"]
            indexed = performance["lecture_unique_secondes"] + performance["construction_index_secondes"] + performance["recherche_indexee_secondes"]
            speedup = naive / indexed if indexed else 0
            print(f"  Mesure sur {performance['lignes_historique']:,} lignes : parcours répétés {naive:.3f} s; index complet {indexed:.3f} s.".replace(",", " "))
            print(f"  Gain mesuré : environ {self._percent(speedup, 1)} fois sur cette exécution.")
            print(f"  Index : {performance['cles_indexees']} couples boutique-produit; lecture unique incluse dans le temps indexé.")
            print(f"  Résultats identiques : {'oui' if performance['equivalence'] else 'non'}.")
        else:
            print("  Lance d'abord l'analyse avec le choix 1 pour afficher les temps mesurés.")

    def _heading(self, text):
        print("\n" + self._paint("=" * 58, self.CYAN))
        print(self._paint(text.center(58), self.CYAN, bold=True))
        print(self._paint("=" * 58, self.CYAN))

    def _section(self, text):
        print("\n" + self._paint(text, self.GOLD, bold=True))

    def _table(self, headers, rows):
        if not rows:
            print("  (aucune donnée)")
            return
        widths = [max(len(str(headers[i])), *(len(str(row[i])) for row in rows)) for i in range(len(headers))]
        top = "  ┌" + "┬".join("─" * (width + 2) for width in widths) + "┐"
        middle = "  ├" + "┼".join("─" * (width + 2) for width in widths) + "┤"
        bottom = "  └" + "┴".join("─" * (width + 2) for width in widths) + "┘"
        print(top)
        print("  │" + "│".join(" " + self._paint(str(value).ljust(widths[i]), self.CYAN, bold=True) + " " for i, value in enumerate(headers)) + "│")
        print(middle)
        for row in rows:
            print("  │" + "│".join(" " + str(value).ljust(widths[i]) + " " for i, value in enumerate(row)) + "│")
        print(bottom)

    @staticmethod
    def _money(value):
        if ConsoleView._is_missing(value):
            return "—"
        return f"{float(value):,.0f} FCFA".replace(",", " ")

    @staticmethod
    def _percent(value, decimals=1, signed=False):
        if ConsoleView._is_missing(value):
            return "—"
        number = float(value)
        formatted = f"{number:+.{decimals}f}" if signed else f"{number:.{decimals}f}"
        return formatted.replace(".", ",") + " %"

    @staticmethod
    def _is_missing(value):
        if value is None:
            return True
        try:
            return bool(value != value)
        except (TypeError, ValueError):
            return True

    @staticmethod
    def _short(value, limit):
        value = str(value)
        return value if len(value) <= limit else value[:limit - 1] + "…"

    def _paint(self, text, color, bold=False):
        if not self.color:
            return text
        prefix = "\033[1m" if bold else ""
        return f"{prefix}{color}{text}{self.RESET}"

    @staticmethod
    def message(text: str):
        print(f"\n{text}\n")
