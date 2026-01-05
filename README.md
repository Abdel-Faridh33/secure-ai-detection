# 🛡️ Secure AI Detection System (Docker Edition)

## Sécurisation des Modèles d'IA pour la Détection d'Objets Dangereux

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.0+-red.svg)](https://pytorch.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## 📖 Description

Ce projet implémente une méthode complète de sécurisation des modèles d'intelligence artificielle utilisés dans les systèmes de maintien de l'ordre, avec un focus sur la détection d'objets dangereux vs sûrs.

**🐳 Développement 100% conteneurisé - Aucune installation Python locale requise!**

### Caractéristiques principales:
- 🎯 **Modèle Baseline**: ResNet50 standard fine-tuné
- 🛡️ **Modèle Sécurisé**: ResNet50 avec défenses multicouches
- ⚔️ **Tests d'attaques**: FGSM, PGD, Poisoning, Backdoor
- 📊 **Comparaison détaillée**: Métriques de performance et robustesse
- 🚀 **Pipeline DevSecOps**: CI/CD complet avec GitHub Actions
- 📈 **Monitoring**: Prometheus + Grafana
- 🐳 **100% Docker**: Développement totalement conteneurisé

## 🚀 Quick Start

**Nouveau ici?** Consultez:
- **[START_HERE.md](START_HERE.md)** - Guide de démarrage
- **[DOCS_INDEX.md](DOCS_INDEX.md)** - Index complet de la documentation
- **[BASELINE_RESULTS.md](BASELINE_RESULTS.md)** - Résultats baseline (95.59% accuracy)

### Prérequis
- Docker 20.10+ (production) OU Python 3.9+ (local)
- Git

### Entraînement Rapide (Google Colab - Recommandé)

```bash
# 1. Préparer le dataset
python scripts/prepare_colab_dataset.py

# 2. Suivre le guide Colab
# Voir notebooks/COLAB_GUIDE.md
```

### Installation Locale

```bash
# 1. Installer les dépendances
pip install -r requirements.txt

# 2. Analyser les résultats baseline
python scripts/analyze_baseline_results.py
```

### Docker (Production)

```bash
# Lancer l'environnement complet
make dev
make shell
```

## 🛠️ Développement

### Services disponibles

| Service | URL | Description |
|---------|-----|-------------|
| API Dev | http://localhost:8000 | API FastAPI |
| Prometheus | http://localhost:9090 | Monitoring |
| Grafana | http://localhost:3000 | Dashboards |

### Commandes principales

```bash
# Développement
make dev          # Lance l'environnement complet
make shell        # Ouvre un shell dans le container

# Entraînement
make train-baseline  # Entraîne le modèle baseline
make train-secured   # Entraîne le modèle sécurisé

# Tests
make test           # Lance tous les tests
make test-attacks   # Teste les attaques

# Production
make prod           # Lance en production
make monitoring     # Lance le monitoring
```

## 📊 Résultats attendus

| Métrique | Baseline | Sécurisé | Amélioration |
|----------|----------|----------|--------------|
| Accuracy | 92.3% | 91.1% | -1.2% |
| ASR (FGSM) | 73.2% | 12.4% | -60.8% |
| ASR (PGD) | 85.1% | 23.7% | -61.4% |
| Privacy Risk | High | Low | ✅ |

## 🏗️ Architecture

```
┌─────────────────┐     ┌─────────────────┐
│   Data Input    │────▶│  Preprocessing  │
└─────────────────┘     └─────────────────┘
                               │
                    ┌──────────┴──────────┐
                    ▼                     ▼
           ┌─────────────────┐   ┌─────────────────┐
           │    Baseline     │   │    Secured      │
           │    ResNet50     │   │    ResNet50     │
           └─────────────────┘   └─────────────────┘
                    │                     │
                    └──────────┬──────────┘
                               ▼
                    ┌─────────────────────┐
                    │    Comparison &     │
                    │     Evaluation      │
                    └─────────────────────┘
```

## 📁 Structure du Projet

```
secure-ai-detection/
├── docker/           # Dockerfiles et compose
├── src/
│   ├── attacks/      # Modules d'attaque
│   ├── defenses/     # Mécanismes de défense
│   ├── evaluation/   # Métriques et comparaison
│   └── api/          # API FastAPI
├── models/           # Modèles entraînés
├── data/             # Datasets
└── docs/             # Documentation
```

## 🧪 Tests

Les tests sont exécutés dans des containers Docker:

```bash
# Tests unitaires
make test

# Tests de performance
docker-compose -f docker/docker-compose.dev.yml run --rm dev pytest tests/performance/

# Couverture de code
docker-compose -f docker/docker-compose.dev.yml run --rm test
```

## 📈 Monitoring

- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (admin/admin)
- **API Docs**: http://localhost:8000/docs

## 🤝 Contribution

Les contributions sont les bienvenues ! 

1. Fork le projet
2. Créer une branche (`git checkout -b feature/AmazingFeature`)
3. Commit (`git commit -m 'Add AmazingFeature'`)
4. Push (`git push origin feature/AmazingFeature`)
5. Ouvrir une Pull Request

## 📄 License

MIT License - voir [LICENSE](LICENSE)

## 📚 Références

- Goodfellow et al. (2014) - Adversarial Examples
- Madry et al. (2018) - PGD Attack
- Abadi et al. (2016) - Differential Privacy

## 👥 Auteurs

- Équipe de Recherche en Sécurité IA
- Master Sécurité Informatique 2025

---

*Projet de mémoire sur la sécurisation des modèles d'IA dans les systèmes de maintien de l'ordre*



*************  


fait un push du projet sur github

Redige moi le chapitre 4 maintenant : Resultts et discussions
Tu as une présentaté les differentes resultats de notre travail ellustré par les capture d'écan. 
On peut y avoir par exemple : Présentation des visuels conteneurs dockers,  des résultats de l'entrainement sécurisé, documentation d'API , interfaces utilsaturs, comparaison resutats surered avec Baseline. comparaison et positionnement de notre approche . Discussions des résultats . Limites .... Dis dit ce qu'il faut capturer et mettre comme image à chaque fois.


Comment fonction les conteneur test explique, il y a aussi des erreur dans le logs de ce conteneur.

Signature RSA-4096 pour non-répudiation : dans chapitre_3.4.tex : pourquoi le titre parle de RSA alors que le code montre sha256 ? Verifie Chiffrement AES-256-GCM du modèle aussi pour etre sur.