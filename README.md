# World Bank Country-Panel Analysis

Country-year panel research on economic development using the World Bank
[Indicators API](https://api.worldbank.org/v2). Three research questions,
one per notebook, all runnable locally on a small slice and scalable to
the OSPool HTCondor cluster at `ap40.uw.osg-htc.org` for
full-panel + bootstrap runs.

## Author

Samah Alshrief · [github.com/Samah989](https://github.com/Samah989)

## Research questions

1. **Institutions & growth**  -  Do improvements in governance quality
   (rule of law, corruption control, government effectiveness) predict
   higher GDP per capita?
2. **Health spending, life expectancy & the gender gap**  -  Do increases in
   per-capita health expenditure translate into longer lives, and are the
   returns different for women vs men and across income groups?
3. **Environmental Kuznets Curve**  -  Is the relationship between
   per-capita income and CO2 emissions hump-shaped, where is the turning
   point, and does trade openness shift it?

Each question is answered with a documented Jupyter notebook and a
matching HTCondor submit file for OSPool execution.

## Repository layout

```
world-bank-country-panel-analysis/
├── notebooks/
│   ├── 00_wb_api_tutorial.ipynb           API from zero
│   ├── 01_rq1_institutions_growth.ipynb   Governance → GDP/capita
│   ├── 02_rq2_health_gender.ipynb         Health spending → life expectancy
│   └── 03_rq3_environmental_kuznets.ipynb CO2 vs income (EKC)
├── src/
│   ├── wb_client.py       WB API client with pagination + parquet caching
│   └── regression.py      Fixed-effects panel + Barro growth helpers
├── osg/
│   ├── README.md          SSH + condor_submit workflow
│   ├── pull_data.submit / pull_data.sh / pull_all_indicators.py
│   ├── run_regression.submit / run_regression.sh / run_regression.py
│   └── requirements-osg.txt
├── data/                  Parquet cache (gitignored)
├── results/               Regression tables + figures (gitignored)
├── setup_instructions.md  First-run commands (GitHub push, OSG sync)
├── requirements.txt
└── .gitignore
```

## Getting started (local, 15 minutes)

```bash
cd "GitHub Tutorials/world-bank-country-panel-analysis"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
jupyter lab
```

Open `notebooks/00_wb_api_tutorial.ipynb` first  -  it walks through the API
with tiny real queries so nothing waits on a huge download. Then run
`01`, `02`, `03` in any order.

## Scaling to OSPool

See [`osg/README.md`](osg/README.md) for the SSH + `rsync` + `condor_submit`
commands wired for `samah.alshrief@ap40.uw.osg-htc.org`.

## Data source

World Bank [Indicators API](https://api.worldbank.org/v2). No key needed.
Underlying series include World Development Indicators (WDI), Worldwide
Governance Indicators (WGI), and Climate Watch datasets, among others.

## License

Private research repository. Not for redistribution without author permission.
