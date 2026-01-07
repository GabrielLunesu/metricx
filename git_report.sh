#!/bin/bash
echo "===== GIT RAPPORT - METRICX/ADNAVI =====" > git_rapport.txt
echo "Gegenereerd: $(date)" >> git_rapport.txt
echo "" >> git_rapport.txt

echo "===== SAMENVATTING =====" >> git_rapport.txt
echo "Totaal commits: $(git rev-list --count HEAD --since='2025-09-01')" >> git_rapport.txt
echo "Eerste commit: $(git log --since='2025-09-01' --reverse --format='%ad' --date=short | head -1)" >> git_rapport.txt
echo "Laatste commit: $(git log -1 --format='%ad' --date=short)" >> git_rapport.txt
echo "" >> git_rapport.txt

echo "===== COMMITS PER MAAND =====" >> git_rapport.txt
git log --since="2025-09-01" --format="%ad" --date=format:"%Y-%m" | sort | uniq -c >> git_rapport.txt
echo "" >> git_rapport.txt

echo "===== ALLE MERGES (PRs) =====" >> git_rapport.txt
git log --oneline --merges --since="2025-09-01" >> git_rapport.txt
echo "" >> git_rapport.txt

echo "===== BRANCHES =====" >> git_rapport.txt
git branch -a >> git_rapport.txt
echo "" >> git_rapport.txt

echo "===== ALLE COMMITS =====" >> git_rapport.txt
git log --since="2025-09-01" --pretty=format:"%h | %ad | %s" --date=short >> git_rapport.txt

echo "Klaar! Check git_rapport.txt"
