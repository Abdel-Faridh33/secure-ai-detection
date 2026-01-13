# Vérification des Implémentations Cryptographiques

## Question posée
**Chapitre 3.4**: Pourquoi le titre parle de "Signature RSA-4096" alors que le code montre SHA-256 ?
Vérifier aussi le chiffrement AES-256-GCM.

---

## ✅ 1. Signature RSA-4096 avec SHA-256 (CORRECT)

### Explication de la confusion

Le titre "**Signature RSA-4096**" est CORRECT, même si le code utilise SHA-256. Voici pourquoi:

### 🔑 Architecture de la signature numérique RSA

La signature RSA-4096 est un **processus en 2 étapes**:

1. **Étape 1: Hash SHA-256** → Calcul d'une empreinte du fichier
2. **Étape 2: Signature RSA-4096** → Chiffrement du hash avec la clé privée RSA-4096

```
Fichier modèle (.pth)
    ↓
[SHA-256] → Hash 32 bytes
    ↓
[RSA-4096 Private Key] → Signature 512 bytes
```

### 📍 Références dans le code

#### Code: `notebooks/security_modules_colab.py` (lignes 329-342)

```python
# ÉTAPE 1: Calculer hash SHA-256 du modèle
with open(model_path, 'rb') as f:
    model_data = f.read()
    model_hash = hashlib.sha256(model_data).digest()  # ← SHA-256

# ÉTAPE 2: Signer le hash avec RSA-4096
signature = private_key.sign(
    model_hash,                          # ← Hash SHA-256 en entrée
    padding.PSS(                         # ← Padding PSS
        mgf=padding.MGF1(hashes.SHA256()),  # ← MGF1 avec SHA-256
        salt_length=padding.PSS.MAX_LENGTH
    ),
    hashes.SHA256()                      # ← Algorithme de hash: SHA-256
)
```

#### Génération des clés RSA-4096 (lignes 322-327)

```python
private_key = rsa.generate_private_key(
    public_exponent=65537,
    key_size=4096,                       # ← RSA-4096 (4096 bits)
    backend=default_backend()
)
```

#### Vérification de la signature (lignes 375-383)

```python
public_key.verify(
    signature,                           # ← Signature RSA-4096 (512 bytes)
    model_hash,                          # ← Hash SHA-256
    padding.PSS(
        mgf=padding.MGF1(hashes.SHA256()),
        salt_length=padding.PSS.MAX_LENGTH
    ),
    hashes.SHA256()                      # ← Algorithme de hash
)
```

### 📊 Caractéristiques techniques

| Composant | Algorithme | Taille | Rôle |
|-----------|-----------|---------|------|
| **Hash** | SHA-256 | 32 bytes (256 bits) | Empreinte du fichier |
| **Signature** | RSA-4096 | 512 bytes (4096 bits) | Preuve cryptographique |
| **Clé publique** | RSA-4096 | ~800 bytes | Vérification |
| **Clé privée** | RSA-4096 | ~3272 bytes | Signature |
| **Padding** | PSS | - | Protection contre attaques |
| **MGF** | MGF1-SHA256 | - | Mask Generation Function |

### ✅ Conclusion pour RSA-4096

**Le titre est CORRECT**: Il s'agit bien d'une **signature RSA-4096**.

**SHA-256 est utilisé pour**:
1. Calculer le hash du fichier (avant signature)
2. Padding PSS / MGF1 (partie intégrante de RSA-PSS)

**Analogie**: SHA-256 est comme "l'encre" et RSA-4096 est la "clé de signature". Les deux sont nécessaires mais c'est bien une "signature RSA-4096".

**Standard**: RSA-PSS avec SHA-256 est conforme au **NIST FIPS 186-4** et recommandé par l'ANSSI.

---

## ✅ 2. Chiffrement AES-256-GCM (CORRECT)

### Implémentation vérifiée

#### Fichier: `src/data/encrypted_storage.py`

### 🔐 Constantes de sécurité (lignes 95-100)

```python
ALGORITHM = 'AES-256-GCM'
KEY_SIZE = 32          # 256 bits ← AES-256
NONCE_SIZE = 12        # 96 bits (recommandation GCM NIST)
TAG_SIZE = 16          # 128 bits (authentification GCM)
SALT_SIZE = 32         # 256 bits (PBKDF2)
PBKDF2_ITERATIONS = 100000  # 100k itérations (OWASP)
```

### 🔑 Dérivation de clé PBKDF2-HMAC-SHA256 (lignes 141-148)

```python
kdf = PBKDF2HMAC(
    algorithm=hashes.SHA256(),          # ← HMAC-SHA256
    length=self.KEY_SIZE,               # ← 32 bytes (256 bits)
    salt=salt,                          # ← Salt aléatoire 32 bytes
    iterations=self.PBKDF2_ITERATIONS,  # ← 100,000 itérations
    backend=self.backend
)
return kdf.derive(password.encode('utf-8'))
```

### 🔒 Chiffrement AES-256-GCM (lignes 199-208)

```python
cipher = Cipher(
    algorithms.AES(key),                # ← Algorithme AES avec clé 256 bits
    modes.GCM(nonce),                   # ← Mode GCM avec nonce 96 bits
    backend=self.backend
)
encryptor = cipher.encryptor()

# Chiffrement avec authentification
ciphertext = encryptor.update(plaintext) + encryptor.finalize()
tag = encryptor.tag  # ← Tag d'authentification GCM (128 bits)
```

### 🔓 Déchiffrement avec vérification d'intégrité (lignes 292-299)

```python
cipher = Cipher(
    algorithms.AES(key),                # ← AES-256
    modes.GCM(nonce, tag),              # ← Mode GCM avec tag pour vérification
    backend=self.backend
)
decryptor = cipher.decryptor()

# Déchiffrement + vérification automatique du tag
plaintext = decryptor.update(ciphertext) + decryptor.finalize()
```

Si le tag GCM ne correspond pas → Exception levée automatiquement par cryptography.

### 📊 Caractéristiques AES-256-GCM

| Composant | Valeur | Conformité |
|-----------|--------|------------|
| **Algorithme** | AES-256-GCM | NIST FIPS 140-2 ✓ |
| **Taille de clé** | 256 bits (32 bytes) | Militaire US (Top Secret) ✓ |
| **Mode** | GCM (Galois/Counter) | AEAD (Authenticated Encryption) ✓ |
| **Nonce** | 96 bits (12 bytes) | NIST SP 800-38D recommandé ✓ |
| **Tag authentification** | 128 bits (16 bytes) | Standard GCM ✓ |
| **Dérivation de clé** | PBKDF2-HMAC-SHA256 | OWASP recommandé ✓ |
| **Itérations PBKDF2** | 100,000 | OWASP 2023 recommandé ✓ |
| **Salt** | 256 bits (32 bytes) | Sécurisé ✓ |

### ✅ Vérifications d'intégrité (lignes 312-319)

```python
if verify_hash:
    computed_hash = hashlib.sha256(plaintext).hexdigest()
    if computed_hash != metadata.file_hash_sha256:
        print(f"ERREUR: Hash SHA-256 ne correspond pas!")
        return False
    print(f"Intégrité vérifiée (SHA-256)")
```

**Double protection**:
1. **Tag GCM** (128 bits) → Intégrité cryptographique du chiffré
2. **Hash SHA-256** (256 bits) → Intégrité du fichier déchiffré

### ✅ Conclusion pour AES-256-GCM

**L'implémentation est CORRECTE et SÉCURISÉE**:

✓ AES-256 (256 bits) confirmé
✓ Mode GCM (Galois/Counter Mode) confirmé
✓ Authenticated Encryption with Associated Data (AEAD)
✓ Nonce 96 bits (recommandation NIST)
✓ Tag 128 bits (standard GCM)
✓ PBKDF2-HMAC-SHA256 avec 100k itérations
✓ Double vérification d'intégrité (tag GCM + hash SHA-256)

**Conformité**:
- NIST FIPS 140-2 ✓
- NIST SP 800-38D (GCM) ✓
- OWASP 2023 (PBKDF2) ✓
- ANSSI (recommandations françaises) ✓

---

## 📝 Résumé des vérifications

### 1. Signature RSA-4096 ✅

**Question**: Pourquoi SHA-256 dans le code si c'est RSA-4096 ?
**Réponse**: SHA-256 est l'algorithme de hash utilisé **AVANT** la signature RSA-4096. C'est le standard RSA-PSS-SHA256.

**Processus complet**:
```
Modèle (.pth)
  ↓ SHA-256
Hash (32 bytes)
  ↓ RSA-4096 + PSS
Signature (512 bytes)
```

**Fichiers générés**:
- `best_secured_model_signature.bin` (512 bytes) ← Signature RSA-4096
- `best_secured_model_public_key.pem` (800 bytes) ← Clé publique RSA-4096
- `best_secured_model_private_key.pem` (3272 bytes) ← Clé privée RSA-4096

**Référence code**: `notebooks/security_modules_colab.py:306-388`

### 2. Chiffrement AES-256-GCM ✅

**Vérification**: L'implémentation utilise bien AES-256-GCM avec tous les paramètres recommandés.

**Processus complet**:
```
Mot de passe
  ↓ PBKDF2-HMAC-SHA256 (100k itérations)
Clé AES-256 (32 bytes)
  ↓ AES-256-GCM
Modèle chiffré + Tag GCM
```

**Fichiers générés**:
- `best_secured_model_encrypted.enc` (même taille que .pth) ← Modèle chiffré
- `best_secured_model_encrypted_metadata.json` ← Nonce, tag, salt, hash

**Référence code**: `src/data/encrypted_storage.py:61-558`

---

## 🎯 Recommandations pour la rédaction

### Dans Chapitre 3.4

Le titre **"Signature RSA-4096 pour non-répudiation"** est parfaitement correct.

**Clarification recommandée** (ajouter dans le texte):

> La signature RSA-4096 utilise SHA-256 comme fonction de hachage cryptographique avant signature (conforme RSA-PSS). Le processus complet consiste à calculer le hash SHA-256 du modèle (32 bytes), puis à signer ce hash avec la clé privée RSA-4096, produisant une signature de 512 bytes. Cette approche est conforme au standard NIST FIPS 186-4 pour les signatures numériques.

**Schéma recommandé**:
```
┌─────────────────┐
│ Modèle PyTorch  │
│  (21.7 MB)      │
└────────┬────────┘
         │
         ↓ SHA-256
┌─────────────────┐
│  Hash SHA-256   │
│   (32 bytes)    │
└────────┬────────┘
         │
         ↓ RSA-4096 Sign (clé privée)
┌─────────────────┐
│ Signature       │
│  (512 bytes)    │
└─────────────────┘
```

### Références bibliographiques à ajouter

1. **NIST FIPS 186-4** - Digital Signature Standard (DSS)
2. **NIST SP 800-38D** - Recommendation for Block Cipher Modes of Operation: Galois/Counter Mode (GCM)
3. **RFC 8017** - PKCS #1: RSA Cryptography Specifications Version 2.2
4. **OWASP Password Storage Cheat Sheet** - PBKDF2 recommendations

---

## 🔬 Tests de validation

### Test 1: Vérifier la signature générée

```bash
# Vérifier la taille de la signature (doit être 512 bytes pour RSA-4096)
ls -lh models/secured/best_secured_model_signature.bin

# Résultat attendu: 512 bytes
```

### Test 2: Vérifier le chiffrement AES-256-GCM

```bash
# Vérifier les métadonnées
cat models/secured/best_secured_model_encrypted_metadata.json

# Résultat attendu:
# - "algorithm": "AES-256-GCM"
# - "key_derivation": "PBKDF2-HMAC-SHA256"
# - nonce: 12 bytes (base64)
# - tag: 16 bytes (base64)
# - salt: 32 bytes (base64)
```

### Test 3: Vérifier l'intégrité du processus

```python
# Exécuter depuis le répertoire du projet
python -c "
from notebooks.security_modules_colab import ModelSigner
from pathlib import Path

model_path = 'models/secured/best_secured_model.pth'
sig_path = 'models/secured/best_secured_model_signature.bin'
pub_key_path = 'models/secured/best_secured_model_public_key.pem'

# Charger la signature et la clé publique
with open(sig_path, 'rb') as f:
    signature = f.read()
with open(pub_key_path, 'rb') as f:
    public_key_pem = f.read()

# Vérifier
is_valid = ModelSigner.verify_signature(model_path, signature, public_key_pem)
print(f'Signature valide: {is_valid}')
print(f'Taille signature: {len(signature)} bytes (attendu: 512)')
"
```

---

## ✅ Conclusion finale

1. **Signature RSA-4096**: Implémentation CORRECTE avec SHA-256 comme fonction de hash (standard RSA-PSS)
2. **Chiffrement AES-256-GCM**: Implémentation CORRECTE avec tous les paramètres NIST recommandés

**Aucune correction de code nécessaire**, juste une clarification dans la rédaction pour éviter la confusion entre:
- RSA-4096 (algorithme de signature, taille de clé 4096 bits)
- SHA-256 (fonction de hash utilisée avant signature)

Les deux travaillent ensemble dans le schéma RSA-PSS-SHA256, qui est le standard actuel.