# 1. Create the .gitignore
cat > .gitignore << 'EOF'
########################################
# LLMLab — CORE EXCLUSIONS
########################################

.ollama/
models/
checkpoints/
*.gguf
*.ggml
*.bin
*.pt
*.pth
*.ckpt
*.safetensors

agents/*/memory/*
!agents/*/memory/.gitkeep
agents/*/tools/*
!agents/*/tools/.gitkeep
agents/*/prompts/*
!agents/*/prompts/.gitkeep
agents/*/configs/*
!agents/*/configs/.gitkeep
agents/*/tests/*
!agents/*/tests/.gitkeep

########################################
# PYTHON
########################################
venv/
.venv/
env/
venv312/
venv312_org/
__pycache__/
*.pyc
*.pyo
*.pyd
*.egg-info/
*.dist-info/
build/
dist/
pip-wheel-metadata/

########################################
# NODE / JAVASCRIPT
########################################
node_modules/
npm-debug.log*
yarn-debug.log*
yarn-error.log*
.pnpm-store/

########################################
# VS CODE
########################################
.vscode/
!.vscode/settings.json
!.vscode/keybindings.json
!.vscode/extensions.list
!.vscode/snippets/
!.vscode/snippets/.gitkeep

########################################
# OS / EDITOR NOISE
########################################
.DS_Store
.AppleDouble
.LSOverride
Thumbs.db
ehthumbs.db
Desktop.ini
*~
.cache/

########################################
# LOGS & RUNTIME OUTPUT
########################################
logs/
*.log
*.out
*.err

########################################
# ENVIRONMENT / SECRETS
########################################
.env
.env.*
*.secret
secrets.json
config.local.yaml

########################################
# TEMP FILES
########################################
*.swp
*.swo

########################################
# PROJECT-SPECIFIC
########################################
router/preprocessor/__pycache__/
router/repl/*.log
router/repl/*.tmp
tools/*/tmp/
tools/*/cache/

########################################
# SAFETY — Prevent accidental large binary commits
########################################
*.zip
*.tar
*.tar.gz
*.7z
*.iso
*.img
EOF

# 2. Initialize Git
git init

# 3. Add all files except ignored ones
git add .

# 4. First commit
git commit -m "Initial LLMLab commit"

# 5. Add GitHub remote (replace YOUR-URL)
git remote add origin https://github.com/randydarthur/LLMLab

# 6. Push to GitHub
git branch -M main
git push -u origin main

