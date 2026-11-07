# Comparateur de prix — Abidjan

Application console Python organisée en MVC pour l'exercice de comparaison de trois enseignes. Les données du ZIP du professeur sont rangées dans `data/source/`; le sujet original est conservé dans `data/LISEZ-MOI-professeur.md`.

## Installation sous Windows

1. Installer Python 3.10 ou une version plus récente et vérifier que la commande `python` fonctionne dans le terminal.
2. Dans PowerShell, exécuter `.\installer.bat` (ou `cmd /c installer.bat`). Ce fichier batch crée `.venv` et installe pandas et openpyxl depuis `requirements.txt`.
3. Exécuter `.\lancer.bat` pour ouvrir le menu console.

Ne pas lancer un fichier `.bat` avec `python installer.bat` : Python essaierait de lire les commandes Windows comme du code Python.

Pour lancer le menu depuis la racine du projet avec la commande vue en cours :

```powershell
python main.py
```

Le bouton **Run Python File** sur ce fichier ouvre aussi le menu. Choisir 1 lance l'analyse. Pour lancer directement toutes les analyses depuis le terminal :

```powershell
.venv\Scripts\python.exe main.py --all
```

Par défaut, les écarts d'au moins 10 % sont signalés. Dans le menu, appuie sur Entrée pour garder ce seuil ou saisis un seuil entre 0 et 100 %. Pour lancer directement l'analyse avec un autre seuil, par exemple 15 % :

```powershell
.venv\Scripts\python.exe main.py --all --seuil 15
```

Le menu suit un parcours de présentation : lancer l'analyse, consulter la synthèse, examiner un produit, voir le panier, la qualité des données, l'historique et la méthode. Le [guide de compréhension](GUIDE_ORAL.md) résume le sujet avec des explications simples.

## Architecture

- `src/models/` : objets métier.
- `src/views/` : menu et affichage console.
- `src/controllers/` : enchaînement des actions.
- `src/repositories/` : lecture des sources CSV, JSON et Excel, normalisation et rapprochement des noms.
- `src/services/` : comparaison des prix, synthèse, panier, historique, benchmark et journal.
- Le comparatif indexe les offres disponibles dans un dictionnaire `produit_id → {boutique: prix}`. Pandas sert à lire les fichiers et à exporter les tableaux.
- `data/source/` : données reçues du professeur.
- `output/` : résultats générés par l’application.

Le dépôt fourni contient déjà les catalogues; aucun scraping web n'est nécessaire pour cet exercice. La couche repository peut accueillir un adaptateur du scraper de S2 si son code ou son format de sortie est ajouté ultérieurement.

## Règles principales

- Prix Marché Lagune : prix affiché, livraison incluse.
- Prix Baobab Shop : montant + frais de livraison.
- Prix Comptoir Ivoire : prix catalogue diminué de la remise; une quantité nulle est signalée comme une rupture de stock.
- Pour P04 à Marché Lagune, le prix fourni a été ajusté de 779 000 à 77 900 FCFA après vérification du dernier prix correspondant dans l'historique.
- Une offre en rupture de stock ou sans prix exploitable ne peut pas gagner.
- Une comparaison nécessite deux boutiques disponibles au minimum.
- Un écart relatif supérieur ou égal au seuil choisi est marqué « à surveiller ». Le seuil par défaut est 10 % et peut être changé au lancement.
- Les prix atypiques sont journalisés et restent affichés pour éviter toute correction inventée.

## Complexité

Une recherche naïve qui reparcourt H lignes pour chacune des Q recherches coûte O(H × Q). Avec un dictionnaire, le programme parcourt les H lignes pour construire l'index, puis effectue Q accès : O(H + Q) en temps et O(H) en mémoire. Ici, H est le nombre de lignes d'historique et Q le nombre de couples boutique-produit recherchés. La mesure comparée inclut la lecture unique et la construction de l'index; les deux méthodes vérifient les mêmes résultats. Les mesures réelles figurent dans `output/performance.json` et le rapport.

## Sorties

`output/comparatif.csv`, `synthese.csv`, `panier_detail.csv`, `panier_par_boutique.csv`, `historique_black_friday.csv`, `journal_nettoyage.csv`, `performance.json` et `rapport_resultats.txt`.

Les catalogues et l'historique sont des données fictives créées pour l'exercice. Les résultats décrivent uniquement ces fichiers.
