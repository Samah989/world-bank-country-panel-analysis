# First-run instructions  -  do this once, in your terminal

Every file is built. These are the commands **you** need to run  -  I can't
type into your Terminal (macOS blocks agents from typing there for safety),
so this last minute is yours.

## 1. Move to the project folder

```bash
cd world-bank-country-panel-analysis
ls
```

Expected: `README.md notebooks src osg data results requirements.txt .gitignore setup_instructions.md`

## 2. Python environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## 3. Push to the (already-created) private GitHub repo

The private repo `Samah989/world-bank-country-panel-analysis` already
exists on GitHub. Paste this whole block:

```bash
git init
git branch -M main
git add .
git commit -m "Initial commit: WB country-panel analysis (3 RQs) with OSG pipeline"
git remote add origin https://github.com/Samah989/world-bank-country-panel-analysis.git
git push -u origin main
```

If it's a fresh Mac, git may pop a browser window to authorize on the
first push.

## 4. Launch JupyterLab and start with the tutorial

```bash
jupyter lab
```

Open `notebooks/00_wb_api_tutorial.ipynb` and run cells top-to-bottom.
Then `01`, `02`, `03`.

## 5. Move to OSPool for the heavy runs

See [`osg/README.md`](osg/README.md).
