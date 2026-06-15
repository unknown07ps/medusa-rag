@echo off
setlocal

set REPO_URL=https://github.com/unknown07ps/medusa-rag.git
set BRANCH=main

echo ============================================
echo  Medusa RAG - GitHub Push Script
echo ============================================
echo.
echo BEFORE RUNNING THIS SCRIPT:
echo   1. Go to https://github.com/new
echo   2. Create a NEW repo named: medusa-rag
echo   3. Set it to PUBLIC, NO README, NO .gitignore
echo   4. Then come back and press any key to continue
echo.
pause

echo Initializing git repo...
git init

echo Adding remote origin...
git remote remove origin 2>nul
git remote add origin %REPO_URL%

echo Staging all files...
git add .

echo Committing...
git commit -m "feat: initial commit - Medusa RAG API with observability stack"

echo Pushing to GitHub...
git branch -M %BRANCH%
git push -u origin %BRANCH%

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ============================================
    echo  ERROR: Push failed. Common fixes:
    echo ============================================
    echo  1. Repo not created yet on GitHub
    echo     Go to: https://github.com/new
    echo     Name it exactly: medusa-rag
    echo.
    echo  2. Not authenticated
    echo     Run: git config --global credential.helper manager
    echo     Then retry this script
    echo.
    echo  3. Using a PAT (Personal Access Token)
    echo     When prompted for password, paste your PAT
    echo     Generate at: https://github.com/settings/tokens
    echo ============================================
) else (
    echo.
    echo ============================================
    echo  SUCCESS!
    echo  Repo live at: https://github.com/unknown07ps/medusa-rag
    echo ============================================
)

pause
