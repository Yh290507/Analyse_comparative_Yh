import argparse
import sys
from pathlib import Path

# Les tableaux de la console utilisent des caractères Unicode sur Windows.
for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8", errors="replace")

# Permet aussi l'exécution directe depuis VS Code : python src/main.py.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.controllers.analysis_controller import AnalysisController


def parse_threshold(value: str) -> float:
    try:
        threshold = float(value.replace(",", "."))
    except ValueError as error:
        raise argparse.ArgumentTypeError("Le seuil doit être un nombre entre 0 et 100.") from error
    if not 0 <= threshold <= 100:
        raise argparse.ArgumentTypeError("Le seuil doit être compris entre 0 et 100 %.")
    return threshold


def main():
    parser = argparse.ArgumentParser(description="Comparateur de prix multi-boutiques en MVC")
    parser.add_argument("--all", action="store_true", help="lance l'analyse complète sans menu")
    parser.add_argument("--menu", action="store_true", help="affiche le menu console")
    parser.add_argument("--seuil", type=parse_threshold, help="seuil d'alerte en pourcentage (0 à 100; défaut : 10)")
    args = parser.parse_args()
    controller = AnalysisController(PROJECT_ROOT)
    if args.all:
        controller.run_all(args.seuil)
    else:
        if args.seuil is not None:
            controller.service.watch_gap_percent = args.seuil
        controller.interactive()


if __name__ == "__main__":
    main()

