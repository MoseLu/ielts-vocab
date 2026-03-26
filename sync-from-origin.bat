@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo === git fetch origin (all branches, prune stale) ===
git fetch origin --prune
if errorlevel 1 (
  echo.
  echo [失败] 无法连接远程。请检查网络、VPN、代理或 GitHub 访问，也可尝试将 origin 改为 SSH：
  echo   git remote set-url origin git@github.com:MoseLu/ielts-vocab.git
  exit /b 1
)

echo.
echo === 当前分支 ===
git branch --show-current

echo.
echo === dev 与 origin/dev 提交差异（左=仅本地，右=仅远程）===
git log --oneline --left-right --decorate dev...origin/dev

echo.
echo === 尚未合并进当前 dev 的远程分支（可能有额外提交）===
git branch -r --no-merged dev 2>nul

echo.
echo === 各远程分支最后一条提交（便于扫一眼）===
git for-each-ref refs/remotes/origin --format="%%(align:45)%%(refname:short)%%(end) %%(objectname:short) %%(subject)" --sort=refname

echo.
echo 后续可选操作（在看清差异后自行执行）：
echo   若远程 dev 有新提交需合并到本地: git merge origin/dev
echo   若要把本地 dev 推上去:            git push origin dev
echo   若要把某远程特性分支并进 dev:      git merge origin/分支名
echo.
