@echo off
echo ========================================
echo Push to GitHub - Ross Cameron Strategy
echo ========================================
echo.
echo This script will push your repository to GitHub.
echo.
echo BEFORE running this script:
echo 1. Go to: https://github.com/new
echo 2. Create repository: ross-cameron-trading-strategy
echo 3. Do NOT initialize with README
echo.
echo GitHub Username: woshishuaige2
echo Pushing to: https://github.com/woshishuaige2/ross-cameron-trading-strategy.git
echo.
pause

cd "C:\Users\china\OneDrive\Desktop\12 Week Plan\Algo trading\ibkr\ross-cameron-trading-strategy"
git remote add origin https://github.com/woshishuaige2/ross-cameron-trading-strategy.git
git branch -M main
git push -u origin main

echo.
echo ========================================
echo Push Complete!
echo ========================================
echo.
echo View your repository at:
echo https://github.com/woshishuaige2/ross-cameron-trading-strategy
echo.
pause
