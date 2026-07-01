@echo off
REM ========================================
REM Commandes Rapides - Secure AI Detection
REM ========================================

echo.
echo ============================================
echo   SECURE AI DETECTION - MOBILENETV2
echo ============================================
echo.

:MENU
echo.
echo Choisissez une action:
echo.
echo [1] Preparer le dataset (deja fait)
echo [2] Entraîner modele SECURED (~1-2h GPU)
echo [3] Evaluer la robustesse adversariale
echo [4] Verifier le dataset
echo [5] Afficher les resultats
echo [Q] Quitter
echo.

set /p choice="Votre choix: "

if /i "%choice%"=="1" goto DATASET
if /i "%choice%"=="2" goto SECURED
if /i "%choice%"=="3" goto EVALUATE
if /i "%choice%"=="4" goto CHECK_DATASET
if /i "%choice%"=="5" goto SHOW_RESULTS
if /i "%choice%"=="Q" goto END

echo Choix invalide!
goto MENU

:DATASET
echo.
echo ======================================
echo   PREPARATION DU DATASET
echo ======================================
echo.
python data/prepare_dataset.py
echo.
pause
goto MENU

:SECURED
echo.
echo ======================================
echo   ENTRAINEMENT SECURED
echo ======================================
echo.
echo Temps estime: 1-2h (GPU) / 4-8h (CPU)
echo Inclus: Zone 1 (verification donnees), Zone 2 (adversarial training FGSM+PGD)
echo.
python src/experiments/secured/train_mobilenet_secured.py
echo.
pause
goto MENU

:EVALUATE
echo.
echo ======================================
echo   EVALUATION ROBUSTESSE ADVERSARIALE
echo ======================================
echo.
echo Temps estime: 10-20 min
echo Tests: FGSM (epsilon=0.08), PGD (3 iterations)
echo.
python src/experiments/secured/attack_secured.py
echo.
pause
goto MENU

:CHECK_DATASET
echo.
echo ======================================
echo   VERIFICATION DU DATASET
echo ======================================
echo.
if exist "data\prepared\dataset_stats.json" (
    type data\prepared\dataset_stats.json
) else (
    echo Dataset non prepare!
    echo Utilisez l'option [1] pour le preparer.
)
echo.
pause
goto MENU

:SHOW_RESULTS
echo.
echo ======================================
echo   AFFICHAGE DES RESULTATS
echo ======================================
echo.
if exist "results\secured_results.json" (
    type results\secured_results.json
) else (
    echo Pas encore de resultats.
    echo Entraînez d'abord le modele [2] puis evaluez [3].
)
echo.
pause
goto MENU

:END
echo.
echo Au revoir!
exit
