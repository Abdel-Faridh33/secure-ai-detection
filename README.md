# Secure AI Detection System

## Sécurisation end-to-end d'un modèle d'IA pour la détection d'objets dangereux

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.0+-red.svg)](https://pytorch.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## Description

Ce projet implémente une architecture de sécurité à 5 zones pour un système de vision par ordinateur basé sur MobileNetV2, dédié à la détection d'objets dangereux (armes à feu) vs sûrs.

Le modèle unique déployé est le **modèle sécurisé** intégrant l'ensemble des défenses de l'architecture proposée.

### Architecture de sécurité (5 zones)

| Zone | Protection | Implémentation |
|------|-----------|----------------|
| Zone 1 | Données | Tests statistiques (Chi², KS, Z-score), détection DBSCAN, stockage AES-256-GCM |
| Zone 2 | Modèle | Adversarial training FGSM+PGD (ε=0.08), clipping gradient, signature RSA-4096 |
| Zone 3 | Infrastructure | Docker isolation, Nginx TLS 1.2/1.3, rate limiting (30 req/min) |
| Zone 4 | Runtime | WAF Python+Nginx, JWT/RBAC (3 rôles), détecteur d'anomalies |
| Zone 5 | Monitoring | Prometheus, Grafana, audit trail append-only SHA-256 |

### Modèle

- **Architecture**: MobileNetV2 (3.5M paramètres, 14MB, ~25ms CPU)
- **Dataset**: 1 896 images (948 safe/COCO + 948 dangerous/Kaggle), split 70/15/15
- **Clean accuracy**: 96.08%
- **Robustesse FGSM** (ε=0.1): 68.14% (+36% vs non sécurisé)
- **Robustesse PGD**: 46.7% (vs 53.3% attack success rate référence)

## Démarrage rapide

### Docker (recommandé)

```bash
# Production complète
docker-compose -f docker/docker-compose.prod.yml up -d

# Développement
docker-compose -f docker/docker-compose.dev.yml up -d
```

### Services

| Service | URL | Description |
|---------|-----|-------------|
| API Sécurisée (via Nginx) | https://localhost | API FastAPI + défenses actives |
| Prometheus | http://localhost:9090 | Métriques |
| Grafana | http://localhost:3000 | Dashboards |

### Entraînement local

```bash
# Pipeline complet (dataset → entraînement → évaluation)
python run_full_pipeline.py --skip-dataset

# Sécurisé uniquement
python src/experiments/secured/train_mobilenet_secured.py

# Évaluation robustesse adversariale
python src/experiments/secured/attack_secured.py
```

## Résultats de robustesse

| Attaque | Taux de succès (référence) | Taux de succès (sécurisé) | Réduction |
|---------|---------------------------|--------------------------|-----------|
| FGSM (ε=0.1) | 50% | 31.86% | -36% |
| PGD (3 iter) | 53.3% | ~31% | -41% |
| Poisoning | ~28.6% détecté | Quarantaine auto | Zone 1 |

## Structure du projet

```
projet-secure-ai-detection/
├── src/
│   ├── api/              # FastAPI + sécurité (WAF, JWT, audit)
│   ├── data/             # Vérification, chiffrement, quarantaine
│   ├── security/         # Anomaly detector, WAF
│   ├── monitoring/       # Prometheus, Grafana, audit logger
│   └── experiments/
│       └── secured/      # Entraînement + évaluation sécurisés
├── docker/               # Dockerfiles et docker-compose
├── configs/              # Nginx, Prometheus, Grafana
├── models/secured/       # Modèle chiffré AES-256-GCM + signature RSA-4096
└── results/              # Résultats d'évaluation
```
