# 📊 Guide de Lecture du Dashboard Grafana

## Vue d'ensemble

Votre dashboard Grafana contient **6 panneaux** pour surveiller votre système de détection d'IA. Voici comment lire et interpréter chaque graphique.

---

## Panel 1: 📊 Taux de Requêtes HTTP

### Qu'est-ce que c'est ?
- **Type**: Graphique temporel (Time Series)
- **Métrique**: `rate(http_requests_total[5m])`
- **Unité**: Requêtes par seconde (reqps)

### Comment le lire ?
Cette requête calcule le **taux de requêtes HTTP par seconde** sur une fenêtre glissante de 5 minutes.

**Exemple de données actuelles**:
```
Endpoint /health:  7 requêtes totales
Endpoint /predict: 12 requêtes totales
```

### Interprétation
- **Axe X**: Temps (heures:minutes)
- **Axe Y**: Nombre de requêtes/seconde
- **Courbes**: Une ligne par combinaison (job + method)
  - `dev-api - GET` : Requêtes GET
  - `dev-api - POST`: Requêtes POST

**Ce que vous voyez**:
- Si la courbe monte → Plus d'activité sur l'API
- Si la courbe est plate à 0 → Pas de trafic récent (normal si pas de requêtes)
- Pics → Moments de forte utilisation

---

## Panel 2: ⏱️ Temps de Réponse P95

### Qu'est-ce que c'est ?
- **Type**: Jauge (Gauge)
- **Métrique**: `histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) * 1000`
- **Unité**: Millisecondes (ms)

### Comment le lire ?
Le **percentile 95** (P95) signifie que **95% des requêtes** sont traitées en **moins que cette durée**.

**Exemple de données actuelles**:
```
12 requêtes /predict:
- 0 en < 100ms
- 7 en < 250ms
- 10 en < 750ms
- 12 en < 2500ms (toutes)
```

### Interprétation
**Calcul du P95**: 95% de 12 requêtes = 11.4 requêtes
→ Le P95 se situe entre 750ms et 2500ms (probablement ~1500ms)

**Seuils de couleur**:
- 🟢 Vert (< 1000ms) : Excellent
- 🔴 Rouge (> 1000ms) : Lent, à optimiser

**Ce que vous voyez**:
- Valeur basse (~200ms) → API rapide
- Valeur élevée (>1000ms) → API lente, problème de performance

---

## Panel 3: 📈 Codes de Statut HTTP (1h)

### Qu'est-ce que c'est ?
- **Type**: Diagramme circulaire (Pie Chart)
- **Métrique**: `increase(http_requests_total[1h])`
- **Unité**: Nombre de requêtes

### Comment le lire ?
Montre la **distribution des codes de statut HTTP** sur la dernière heure.

**Données actuelles**:
```
200 (OK) - /health:  7 requêtes
200 (OK) - /predict: 12 requêtes
```

### Interprétation
**Codes HTTP importants**:
- **200**: Succès ✅
- **400**: Erreur client (mauvaise requête) ⚠️
- **500**: Erreur serveur 🔴

**Ce que vous voyez**:
- 100% en vert (200) → Tout fonctionne bien
- Présence de 400/500 → Il y a des erreurs

---

## Panel 4: ✅ Disponibilité du Service

### Qu'est-ce que c'est ?
- **Type**: Graphique temporel (Time Series)
- **Métrique**: `100 * (1 - rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m]))`
- **Unité**: Pourcentage (%)

### Comment le lire ?
Calcule le **taux de disponibilité** en excluant les erreurs 5xx (erreurs serveur).

**Formule**:
```
Disponibilité = 100% - (taux d'erreurs 5xx / taux total)
```

**Données actuelles**: 0 erreur 5xx → 100% de disponibilité

### Interprétation
**Ce que vous voyez**:
- 100% → Service parfaitement opérationnel
- 99.9% → Excellente disponibilité
- < 95% → Problème grave, service instable

---

## Panel 5: 🤖 Taux de Prédictions IA

### Qu'est-ce que c'est ?
- **Type**: Graphique temporel (Time Series)
- **Métrique**: `rate(ai_model_predictions_total[5m])`
- **Unité**: Prédictions par seconde

### Comment le lire ?
Montre combien de **prédictions IA par seconde** sont effectuées par chaque modèle.

**Données actuelles**:
```
Modèle baseline:
  - 3 prédictions "safe"
  - 3 prédictions "dangerous"

Modèle secured:
  - 2 prédictions "safe"
  - 4 prédictions "dangerous"
```

### Interprétation
**Courbes attendues**:
- `baseline - Prédictions/sec`: Ligne bleue pour le modèle non sécurisé
- `secured - Prédictions/sec`: Ligne verte pour le modèle sécurisé

**Ce que vous voyez**:
- Courbes qui suivent le même pattern → Les deux modèles reçoivent le même trafic
- Courbe plate → Pas d'activité de prédiction

---

## Panel 6: 🎯 Précision des Modèles

### Qu'est-ce que c'est ?
- **Type**: Graphique temporel (Time Series)
- **Métrique**: `ai_model_accuracy`
- **Unité**: Pourcentage (%)

### Comment le lire ?
Affiche la **précision actuelle** de chaque modèle en temps réel.

**Données actuelles**:
```
Model baseline: 96.08%
Model secured:  96.08%
```

### Interprétation
**Ce que vous voyez**:
- Ligne horizontale à ~96% → Précision stable
- Les deux modèles ont la même précision → C'est la métrique du **test set**
- Si la ligne descend soudainement → Dégradation du modèle (data drift, attaque)

**Important**: Cette métrique est mise à jour **au chargement du modèle**, pas à chaque prédiction. Elle reflète la performance sur le jeu de test.

---

## 🔍 Pourquoi certains graphiques sont vides ?

### Cas courant: "No Data"

1. **Pas assez de données historiques**
   - Les requêtes `rate()` nécessitent au moins 2 points de données
   - Solution: Attendez quelques minutes ou générez du trafic

2. **Fenêtre de temps trop courte**
   - Si vous regardez "Last 5 minutes" mais n'avez fait qu'une requête il y a 10 min
   - Solution: Augmentez la fenêtre à "Last 1 hour"

3. **Aucune donnée pour cette métrique**
   - Exemple: Panel "Disponibilité" sera vide s'il n'y a jamais eu d'erreur 5xx
   - C'est normal et même souhaitable !

---

## 🎯 Comment générer des données de test ?

Pour voir vos graphiques s'animer, envoyez des requêtes à l'API :

```bash
# Santé de l'API
curl http://localhost:9800/health

# Prédiction (remplacez par une vraie image base64)
curl -X POST http://localhost:9800/predict \
  -H "Content-Type: application/json" \
  -d '{
    "image": "iVBORw0KGgoAAAANSUhEUg...",
    "model_type": "baseline"
  }'
```

Après quelques requêtes, rafraîchissez Grafana et vous verrez les courbes apparaître !

---

## 📚 Glossaire

- **Rate**: Taux de variation par seconde
- **Increase**: Augmentation totale sur une période
- **Histogram_quantile**: Calcul de percentile à partir d'un histogram
- **P95 (95th percentile)**: 95% des valeurs sont inférieures à ce seuil
- **Counter**: Métrique qui ne fait qu'augmenter (nombre total)
- **Gauge**: Métrique qui peut monter et descendre (valeur actuelle)
- **Histogram**: Distribution de valeurs dans des buckets

---

## ⚠️ Problèmes courants

### "Expression query error"
→ La requête Prometheus est invalide ou la métrique n'existe pas

### "No data points"
→ Pas assez de données historiques, attendez ou générez du trafic

### "N/A" sur une jauge
→ La formule ne peut pas être calculée (ex: division par zéro)

### Graphique plat à 0
→ Normal si pas d'activité récente (fenêtre de 5 minutes)
