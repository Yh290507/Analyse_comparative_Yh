from pathlib import Path

from src.repositories.data_repository import DataRepository
from src.services.analysis_service import AnalysisService
from src.views.console_view import ConsoleView


class AnalysisController:
    def __init__(self, root: Path):
        self.root = root
        self.repository = DataRepository(root / "data" / "source")
        self.service = AnalysisService(root / "output")
        self.view = ConsoleView()
        self.last_results = None

    def run_all(self, watch_threshold=None):
        if watch_threshold is not None:
            self.service.watch_gap_percent = self.service._validate_watch_gap(watch_threshold)
        catalogue = self.repository.load_catalogue()
        offers = self.repository.load_offers(catalogue)
        comparison, summary = self.service.compare(catalogue, offers)
        coverage = self.service.coverage(catalogue, offers)
        basket_detail, basket_totals = self.service.basket(catalogue, offers)
        history, performance = self.service.history(self.root / "data" / "source" / "historique_prix.csv")
        journal = self.service.write_cleaning_journal(self.repository.issues)
        self.service.write_text_report(catalogue, comparison, summary, basket_detail, basket_totals, history, performance, journal)
        self.last_results = (comparison, summary, basket_detail, basket_totals, history, performance, journal)
        self.view.show_analysis_complete(
            comparison, journal, len(catalogue), self.repository.source_counts, coverage,
            self.service.watch_gap_percent,
        )
        return self.last_results

    def interactive(self):
        while True:
            choice = self.view.menu()
            if choice == "0":
                self.view.message("À bientôt.")
                return
            if choice == "1":
                threshold = self.view.ask_watch_threshold(self.service.watch_gap_percent)
                self.run_all(threshold)
                continue
            if choice == "7":
                performance = self.last_results[5] if self.last_results is not None else None
                self.view.show_method(performance)
                continue
            if choice not in {"2", "3", "4", "5", "6"}:
                self.view.message("Choix invalide. Sélectionne un nombre de 0 à 7.")
                continue
            if self.last_results is None:
                self.view.message("Lance d'abord l'analyse avec le choix 1.")
                continue

            comparison, summary, basket_detail, basket_totals, history, _, journal = self.last_results
            if choice == "2":
                self.view.show_summary(comparison, summary)
            elif choice == "3":
                product_id = self.view.ask_product_id()
                product = comparison[comparison["produit_id"].astype(str).str.upper() == product_id.upper()]
                if product.empty:
                    self.view.message("Code non trouvé parmi les produits comparables. Essaie un code comme P04.")
                else:
                    self.view.show_product(product.iloc[0], self.service.watch_gap_percent)
            elif choice == "4":
                self.view.show_basket(basket_detail, basket_totals)
            elif choice == "5":
                self.view.show_issues(journal)
            elif choice == "6":
                self.view.show_history(history)
