# Comprendre le comparateur

Ces notes servent à comprendre le projet. Sers-t'en pour expliquer la démarche avec tes propres mots.

## Résumé

- Le programme compare les prix de trois boutiques.
- Chaque boutique fournit son catalogue dans un format différent : CSV, JSON ou Excel.
- Le nettoyage rend les noms comparables et signale les prix absents ou suspects.
- Le programme calcule le moins cher, l'écart en FCFA et le pourcentage.
- Il traite aussi le panier de rentrée, l'historique et la vitesse des recherches.

## Explication des parties

## Ce que chaque partie signifie

- **Model** : représente les offres, les prix et les produits à comparer.
- **View** : affiche le menu, les tableaux et les explications dans la console.
- **Controller** : reçoit le choix du menu et appelle les traitements dans le bon ordre.
- **Repository** : lit les fichiers CSV, JSON et Excel.
- **Service** : applique les règles de prix et calcule comparatif, panier, historique et performance.

MVC aide à modifier l'affichage sans changer les règles de calcul. Le repository peut aussi être adapté si l'équipe ajoute le scraper de S2.

## Parcourir le programme

1. Lance `python main.py` ou `lancer.bat` depuis la racine du projet.
2. Choisis **1** pour analyser les fichiers. Appuie sur Entrée pour garder le seuil par défaut de 10 %, ou saisis un autre pourcentage entre 0 et 100. Le bilan affiche aussi le nombre d'éléments lus dans chaque source.
3. Choisis **2** pour présenter la synthèse des boutiques, puis **3** pour comparer un produit comme P04.
4. Utilise **4** pour le panier, **5** pour les problèmes de données, **6** pour l'historique et **7** pour la méthode et Big O.
5. Les exports détaillés sont dans `output/`, notamment `comparatif.csv`, `journal_nettoyage.csv` et `performance.json`.

## Exemple de calcul

Le produit P29 coûte 9 200 FCFA au moins cher et 11 600 FCFA au plus cher. Son écart vaut 2 400 FCFA. Le pourcentage est calculé par `(11 600 − 9 200) ÷ 9 200 × 100`, soit environ 26,1 %. Le seuil « à surveiller » de 10 % est un choix d'affichage du projet, pas une règle imposée dans le sujet.

Pour P04 (Tecno Spark 20 128 Go), le fichier de Marché Lagune affichait 779 000 FCFA. Après vérification du dernier prix fourni dans l'historique, le groupe a retenu 77 900 FCFA et recalculé les résultats. P04 est alors présent dans trois boutiques : minimum 75 000 FCFA, moyenne 76 400 FCFA, maximum 77 900 FCFA et écart relatif 3,87 %. Il n'est pas « à surveiller » avec le seuil par défaut de 10 %.

## Résultats obtenus sur les fichiers fournis

- 23 produits ont des offres exploitables chez au moins deux boutiques.
- Comptoir Ivoire est le moins cher le plus souvent dans les comparaisons; Baobab Shop et Comptoir Ivoire restent proches sur le panier demandé.
- Le panier complet coûte 504 300 FCFA à Marché Lagune, 491 500 FCFA chez Baobab Shop et 484 075 FCFA chez Comptoir Ivoire. Le panier mixte, en choisissant le meilleur prix de chaque article, coûte 477 575 FCFA.
- La moyenne de la semaine du Black Friday est environ 11 % plus basse que la moyenne annuelle chez Baobab Shop et Marché Lagune dans ce jeu de données fictif.

Les temps exacts changent selon l'ordinateur et la version de Python. Il faut présenter ceux affichés par la dernière exécution, pas mémoriser un nombre fixe.

## Questions possibles

**Comment expliquer le prix retenu pour P04 ?**  
La valeur de Marché Lagune utilisée est 77 900 FCFA, cohérente avec la dernière valeur de l'historique fournie pour ce produit. Le comparatif et le journal sont recalculés depuis cette source.

**Pourquoi exclure une boutique en rupture ?**  
Une offre en rupture de stock ou sans prix exploitable ne peut pas gagner le comparatif.

**Pourquoi le dictionnaire accélère-t-il les recherches ?**  
Pour le comparatif, le programme range les prix sous la forme `produit_id → boutique → prix`. Il peut ainsi retrouver directement les prix des boutiques pour un produit, calculer le minimum et l'écart, puis comparer les offres.

Pour l'historique, H désigne le nombre de lignes et Q le nombre de couples boutique-produit recherchés. La méthode naïve balaie les H lignes pour chacune des Q recherches, donc son temps croît comme O(H × Q). Avec un dictionnaire, le programme lit et indexe H lignes une fois, puis fait Q accès : O(H + Q) en temps et O(H) en mémoire. Sur les données actuelles, cela représente 20 876 lignes et 76 couples indexés. Les temps mesurés varient selon l'ordinateur; le rapport compare aussi la lecture et la construction de l'index.

**Pourquoi l'écart moyen varie-t-il selon la boutique ?**  
Chaque boutique est évaluée sur les produits où elle a une offre disponible. L'écart compare alors son prix au meilleur prix observé pour le même produit.
