"""
Tests rapides pour les modules de sécurité
Zone 4 - Production Security

Test des fonctionnalités :
- Authentification JWT + RBAC
- WAF (rate limiting + validation)
- Détection d'anomalies
"""

import sys
import os

# Ajouter le dossier parent au path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.security.auth import (
    create_access_token,
    verify_token,
    authenticate_user,
    check_permission,
    UserRole,
    Permission
)
from src.security.waf import WAF, InputValidator
from src.security.anomaly_detector import AnomalyDetector


def test_authentication():
    """Test du système d'authentification JWT"""
    print("\n=== Test 1: Authentification JWT ===")

    # Test 1.1: Création de token
    token = create_access_token(username="admin", role="admin")
    print(f"[OK] Token créé: {token[:50]}...")

    # Test 1.2: Vérification de token
    payload = verify_token(token)
    assert payload is not None, "Token devrait être valide"
    assert payload["sub"] == "admin", "Username devrait être 'admin'"
    assert payload["role"] == "admin", "Role devrait être 'admin'"
    print(f"[OK] Token vérifié: username={payload['sub']}, role={payload['role']}")

    # Test 1.3: Authentification utilisateur
    user = authenticate_user("admin", "admin123")
    assert user is not None, "Authentification devrait réussir"
    assert user["username"] == "admin", "Username devrait être 'admin'"
    print(f"[OK] Authentification réussie: {user['username']} (role: {user['role']})")

    # Test 1.4: Mauvais mot de passe
    user = authenticate_user("admin", "wrongpassword")
    assert user is None, "Authentification devrait échouer"
    print("[OK] Mauvais mot de passe rejeté correctement")

    print("[SUCCESS] Tous les tests d'authentification passes [OK]")


def test_rbac():
    """Test du système RBAC (contrôle d'accès)"""
    print("\n=== Test 2: RBAC (Permissions) ===")

    # Test 2.1: Permissions admin
    has_predict = check_permission("admin", Permission.PREDICT)
    has_audit = check_permission("admin", Permission.VIEW_AUDIT)
    has_manage = check_permission("admin", Permission.MANAGE_USERS)

    assert has_predict, "Admin devrait avoir permission PREDICT"
    assert has_audit, "Admin devrait avoir permission VIEW_AUDIT"
    assert has_manage, "Admin devrait avoir permission MANAGE_USERS"
    print("[OK] Admin a toutes les permissions")

    # Test 2.2: Permissions agent (limitées)
    has_predict_agent = check_permission("agent", Permission.PREDICT)
    has_manage_agent = check_permission("agent", Permission.MANAGE_USERS)

    assert has_predict_agent, "Agent devrait avoir permission PREDICT"
    assert not has_manage_agent, "Agent NE devrait PAS avoir permission MANAGE_USERS"
    print("[OK] Agent a les permissions limitées correctes")

    # Test 2.3: Permissions guest (minimales)
    has_predict_guest = check_permission("guest", Permission.PREDICT)
    has_audit_guest = check_permission("guest", Permission.VIEW_AUDIT)

    assert has_predict_guest, "Guest devrait avoir permission PREDICT"
    assert not has_audit_guest, "Guest NE devrait PAS avoir permission VIEW_AUDIT"
    print("[OK] Guest a les permissions minimales")

    print("[SUCCESS] Tous les tests RBAC passes [OK]")


def test_waf():
    """Test du WAF (rate limiting + validation)"""
    print("\n=== Test 3: WAF (Rate Limiting & Validation) ===")

    waf = WAF(max_requests=5, window_seconds=60)

    # Test 3.1: Requêtes normales
    test_ip = "192.168.1.100"
    for i in range(5):
        result = waf.check_request(test_ip)
        assert result["allowed"], f"Requête {i+1} devrait être autorisée"
    print(f"[OK] 5 requêtes autorisées pour {test_ip}")

    # Test 3.2: Rate limit dépassé
    result = waf.check_request(test_ip)
    assert not result["allowed"], "Requête 6 devrait être bloquée"
    assert result["reason"] == "Rate limit exceeded", "Raison devrait être 'Rate limit exceeded'"
    print(f"[OK] Rate limit détecté après 5 requêtes")

    # Test 3.3: IP est maintenant bloquée
    is_blocked = waf.is_ip_blocked(test_ip)
    assert is_blocked, "IP devrait être bloquée"
    print(f"[OK] IP {test_ip} est bloquée pour 5 minutes")

    # Test 3.4: Validation de filename
    validator = InputValidator()

    safe_filename = "test_image.jpg"
    assert validator.is_safe_filename(safe_filename), "Filename sûr devrait passer"
    print(f"[OK] Filename sûr validé: {safe_filename}")

    unsafe_filename = "../etc/passwd"
    assert not validator.is_safe_filename(unsafe_filename), "Filename suspect devrait être rejeté"
    print(f"[OK] Filename suspect rejeté: {unsafe_filename}")

    xss_filename = "<script>alert('xss')</script>.jpg"
    assert not validator.is_safe_filename(xss_filename), "XSS devrait être rejeté"
    print(f"[OK] XSS rejeté: {xss_filename}")

    print("[SUCCESS] Tous les tests WAF passes [OK]")


def test_anomaly_detection():
    """Test du détecteur d'anomalies"""
    print("\n=== Test 4: Détection d'Anomalies ===")

    detector = AnomalyDetector()
    test_ip = "10.0.0.50"

    # Test 4.1: Requêtes normales (pas d'anomalie)
    for i in range(5):
        result = detector.analyze_request(
            ip=test_ip,
            endpoint="/predict/baseline",
            model_type="baseline",
            prediction="safe",
            confidence=0.85,
            status_code=200
        )

    assert result["risk_level"] == "low", "Risk level devrait être 'low' pour activité normale"
    print(f"[OK] Activité normale détectée (risk_level: {result['risk_level']})")

    # Test 4.2: Burst d'activité (anomalie)
    for i in range(55):  # Plus de 50 requêtes = burst
        result = detector.analyze_request(
            ip=test_ip,
            endpoint="/predict/secured",
            model_type="secured",
            confidence=0.90,
            status_code=200
        )

    assert result["anomalies_detected"], "Burst devrait être détecté"
    assert result["risk_level"] in ["medium", "high"], "Risk level devrait être élevé"
    print(f"[OK] Burst d'activité détecté (anomalies: {len(result['anomalies'])})")

    # Test 4.3: Échecs répétés
    fail_ip = "10.0.0.51"
    for i in range(12):  # Plus de 10 échecs = anomalie
        result = detector.analyze_request(
            ip=fail_ip,
            endpoint="/predict/baseline",
            status_code=400  # Échec
        )

    assert result["anomalies_detected"], "Échecs répétés devraient être détectés"
    assert result["risk_level"] in ["high", "critical"], "Risk level devrait être critique"
    print(f"[OK] Échecs répétés détectés (risk_score: {result['risk_score']:.1f})")

    # Test 4.4: Obtenir les IPs à haut risque
    high_risk = detector.get_high_risk_ips(threshold=30.0)
    assert len(high_risk) > 0, "Devrait avoir des IPs à haut risque"
    print(f"[OK] {len(high_risk)} IP(s) à haut risque identifiée(s)")

    print("[SUCCESS] Tous les tests de detection d'anomalies passes [OK]")


def run_all_tests():
    """Exécuter tous les tests"""
    print("=" * 60)
    print("TESTS DES MODULES DE SÉCURITÉ - ZONE 4")
    print("=" * 60)

    try:
        test_authentication()
        test_rbac()
        test_waf()
        test_anomaly_detection()

        print("\n" + "=" * 60)
        print("[OK] TOUS LES TESTS PASSES AVEC SUCCES !")
        print("=" * 60)
        print("\nModules valides :")
        print("  - Authentification JWT + RBAC")
        print("  - WAF (Rate Limiting + Validation)")
        print("  - Detection d'Anomalies en temps reel")
        print("\n[OK] Zone 4 Production Security : Implementation complete")

    except AssertionError as e:
        print(f"\n[ERREUR] Test échoué: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERREUR] Exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    run_all_tests()
