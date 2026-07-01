#!/usr/bin/env python3
"""
Generateur de trafic de test - Grafana dashboard population
Genere differents types de requetes vers l'API securisee pour remplir les panneaux Grafana :
  - Predictions valides (safe et dangerous)
  - Erreurs 422 (mauvais format)
  - Bursts de charge (test rate-limiting Nginx)
  - Requetes lentes (grandes images)
  - Images a pattern adversarial
"""

import requests
import time
import random
import sys
import io
import argparse
import urllib3
from PIL import Image
import numpy as np

# Desactiver les warnings SSL pour les certs auto-signes
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- Configuration ---
SECURED_URL = "https://localhost"   # via nginx HTTPS

VERIFY_SSL = False  # cert auto-signe en dev

# Couleurs terminal
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
BLUE   = "\033[94m"
CYAN   = "\033[96m"
RESET  = "\033[0m"
BOLD   = "\033[1m"


# ---------------------------------------------------------------------------
# Generateurs d'images
# ---------------------------------------------------------------------------

def make_normal_image(size=(64, 64)):
    """Image RGB aleatoire normale -> prediction probable 'safe'."""
    arr = np.random.randint(100, 200, (*size, 3), dtype=np.uint8)
    img = Image.fromarray(arr)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf

def make_noisy_image(size=(64, 64)):
    """Image tres bruitee -> peut declencher 'dangerous'."""
    arr = np.random.randint(0, 256, (*size, 3), dtype=np.uint8)
    img = Image.fromarray(arr)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf

def make_adversarial_image(size=(64, 64)):
    """Image avec pattern regulier fort -> simulation d'image adversariale."""
    arr = np.zeros((*size, 3), dtype=np.uint8)
    for i in range(size[0]):
        for j in range(size[1]):
            arr[i, j] = [(i * 4) % 256, (j * 4) % 256, ((i + j) * 2) % 256]
    img = Image.fromarray(arr)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf

def make_large_image(size=(512, 512)):
    """Grande image -> latence plus elevee."""
    arr = np.random.randint(0, 256, (*size, 3), dtype=np.uint8)
    img = Image.fromarray(arr)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf

def make_invalid_file():
    """Fichier non-image -> provoque une erreur 422."""
    return io.BytesIO(b"ceci n'est pas une image valide - erreur intentionnelle")

def make_empty_file():
    """Fichier vide -> provoque une erreur 422."""
    return io.BytesIO(b"")


# ---------------------------------------------------------------------------
# Fonctions de requete
# ---------------------------------------------------------------------------

def predict(file_buf, filename="test.png", content_type="image/png", verify=False):
    """Envoie une requete de prediction vers l'API securisee. Retourne (status_code, result_dict)."""
    try:
        file_buf.seek(0)
        files = {"file": (filename, file_buf, content_type)}
        r = requests.post(
            f"{SECURED_URL}/predict",
            files=files,
            timeout=60,
            verify=verify
        )
        try:
            return r.status_code, r.json()
        except Exception:
            return r.status_code, {}
    except requests.exceptions.ConnectionError:
        return -1, {"error": "connexion refusee"}
    except requests.exceptions.Timeout:
        return -2, {"error": "timeout"}
    except Exception as e:
        return -3, {"error": str(e)}

def health_check(verify=False):
    """Verifie que l'API securisee repond."""
    try:
        r = requests.get(f"{SECURED_URL}/health", timeout=10, verify=verify)
        return r.status_code == 200
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Scenarios
# ---------------------------------------------------------------------------

SCENARIOS = {
    "normal": {
        "desc": "Prediction normale (safe)",
        "image_fn": make_normal_image,
        "weight": 35,
    },
    "noisy": {
        "desc": "Image bruitee (probable dangerous)",
        "image_fn": make_noisy_image,
        "weight": 20,
    },
    "adversarial": {
        "desc": "Pattern adversarial simule",
        "image_fn": make_adversarial_image,
        "weight": 15,
    },
    "large": {
        "desc": "Grande image 512x512 (latence elevee)",
        "image_fn": make_large_image,
        "weight": 10,
    },
    "invalid": {
        "desc": "Fichier invalide (erreur 422)",
        "image_fn": make_invalid_file,
        "weight": 10,
        "filename": "not_an_image.txt",
        "content_type": "text/plain",
    },
    "empty": {
        "desc": "Fichier vide (erreur 422)",
        "image_fn": make_empty_file,
        "weight": 10,
        "filename": "empty.png",
        "content_type": "image/png",
    },
}


def pick_scenario():
    """Choisit un scenario aleatoirement selon les poids."""
    keys = list(SCENARIOS.keys())
    weights = [SCENARIOS[k]["weight"] for k in keys]
    return SCENARIOS[random.choices(keys, weights=weights, k=1)[0]]


def run_scenario(sc, idx, total):
    """Execute un scenario et affiche le resultat."""
    buf = sc["image_fn"]()
    fname = sc.get("filename", "test.png")
    ctype = sc.get("content_type", "image/png")

    t0 = time.time()
    status, result = predict(buf, fname, ctype, VERIFY_SSL)
    elapsed_ms = (time.time() - t0) * 1000

    if status == 200:
        prediction = result.get("prediction", "?")
        color = GREEN if prediction == "safe" else YELLOW
        symbol = "OK "
        detail = f"prediction={prediction}  conf={result.get('confidence', 0):.2f}  {elapsed_ms:.0f}ms"
    elif status in (422, 400):
        color = YELLOW
        symbol = "422"
        detail = f"format invalide (attendu)  {elapsed_ms:.0f}ms"
    elif status == 429:
        color = YELLOW
        symbol = "429"
        detail = f"rate limit nginx (attendu en burst)  {elapsed_ms:.0f}ms"
    elif status == 500:
        color = RED
        symbol = "500"
        detail = f"erreur serveur  {elapsed_ms:.0f}ms"
    elif status < 0:
        color = RED
        symbol = "ERR"
        detail = result.get("error", "connexion echouee")
    else:
        color = RED
        symbol = str(status)
        detail = f"{elapsed_ms:.0f}ms"

    print(f"{color}[{idx:>4}/{total}] {symbol} {sc['desc'][:50]:<50} {detail}{RESET}")
    return status


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Generateur de trafic de test - API Securisee")
    parser.add_argument("-n", "--num", type=int, default=100,
                        help="Nombre total de requetes (defaut: 100)")
    parser.add_argument("-d", "--delay", type=float, default=0.3,
                        help="Delai entre requetes en secondes (defaut: 0.3)")
    parser.add_argument("--burst", action="store_true",
                        help="Mode burst: envoie des rafales de 10 requetes sans delai (teste le rate-limiting)")
    parser.add_argument("--errors-only", action="store_true",
                        help="Envoie uniquement des requetes erronees (pour tester les panneaux d'erreurs)")
    args = parser.parse_args()

    print(f"\n{BOLD}{'=' * 65}{RESET}")
    print(f"{BOLD}  GENERATEUR DE TRAFIC - API Securisee{RESET}")
    print(f"{BOLD}{'=' * 65}{RESET}")
    print(f"  API securisee : {SECURED_URL}  (HTTPS via nginx)")
    print(f"  Requetes      : {args.num}   Delai : {args.delay}s   Burst : {args.burst}")
    print(f"{BOLD}{'=' * 65}{RESET}\n")

    print("Verification de l'API securisee...")
    ok = health_check(verify=VERIFY_SSL)
    print(f"  Secured API : {'OK' if ok else 'INACCESSIBLE'}")

    if not ok:
        print(f"\n{RED}API inaccessible. Verifiez que les conteneurs sont demarres.{RESET}")
        print(f"  docker-compose -f docker/docker-compose.prod.yml up -d")
        sys.exit(1)

    print()

    stats = {"200": 0, "422": 0, "429": 0, "500": 0, "error": 0, "other": 0}
    burst_size = 10

    for i in range(1, args.num + 1):
        if args.errors_only:
            sc = SCENARIOS["invalid"]
        else:
            sc = pick_scenario()

        status = run_scenario(sc, i, args.num)

        if status == 200:
            stats["200"] += 1
        elif status in (422, 400):
            stats["422"] += 1
        elif status == 429:
            stats["429"] += 1
        elif status == 500:
            stats["500"] += 1
        elif status < 0:
            stats["error"] += 1
        else:
            stats["other"] += 1

        if args.burst and i % burst_size != 0:
            time.sleep(0.05)
        elif args.burst and i % burst_size == 0:
            print(f"\n  {CYAN}--- Pause entre rafales ({args.delay}s) ---{RESET}\n")
            time.sleep(args.delay * 5)
        else:
            time.sleep(args.delay)

    total_done = sum(stats.values())
    print(f"\n{BOLD}{'=' * 65}{RESET}")
    print(f"{BOLD}  RESUME{RESET}")
    print(f"{BOLD}{'=' * 65}{RESET}")
    print(f"  {GREEN}200 OK           : {stats['200']:>5}{RESET}")
    print(f"  {YELLOW}422 Format KO    : {stats['422']:>5}{RESET}")
    print(f"  {YELLOW}429 Rate limited : {stats['429']:>5}{RESET}")
    print(f"  {RED}500 Erreur srv   : {stats['500']:>5}{RESET}")
    print(f"  {RED}Connexion KO     : {stats['error']:>5}{RESET}")
    print(f"  Autre            : {stats['other']:>5}")
    print(f"  {'-' * 30}")
    taux = (stats['200'] / total_done * 100) if total_done else 0
    print(f"  Total            : {total_done:>5}   Taux succes : {taux:.1f}%")
    print(f"\n{BOLD}{'=' * 65}{RESET}")
    print(f"  Grafana : {CYAN}http://localhost:3000{RESET}  (admin/admin)")
    print(f"{BOLD}{'=' * 65}{RESET}\n")


if __name__ == "__main__":
    main()
