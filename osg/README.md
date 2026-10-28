# Running on OSPool (ap40.uw.osg-htc.org)

Same workflow as the IPEDS project. Two jobs, run in order:

1. `pull_data.submit`  -  hits the World Bank API and caches every indicator
   for the 3 RQs to parquet.
2. `run_regression.submit`  -  queues one job per RQ with 1,000 bootstrap
   replicates.

## One-time setup (once, on your Mac)

```bash
ssh samah.alshrief@ap40.uw.osg-htc.org
mkdir -p ~/wb-analysis && exit
```

## Every run  -  sync, submit, sync back

```bash
cd "GitHub Tutorials/world-bank-country-panel-analysis"

# 1. Ship code up (excluding venv / cached data)
rsync -avz --delete \
  --exclude '.venv' --exclude '__pycache__' \
  --exclude 'data/*.parquet' --exclude 'results/*' \
  ./ samah.alshrief@ap40.uw.osg-htc.org:~/wb-analysis/

# 2. Submit the data pull
ssh samah.alshrief@ap40.uw.osg-htc.org
cd ~/wb-analysis/osg
mkdir -p logs
condor_submit pull_data.submit
condor_watch_q       # detach with Ctrl-C

# 3. When pull finishes (10-20 min), run the regressions
condor_submit run_regression.submit
condor_watch_q
exit
```

Pull results back:

```bash
rsync -avz samah.alshrief@ap40.uw.osg-htc.org:~/wb-analysis/osg/results/ ./results/
rsync -avz samah.alshrief@ap40.uw.osg-htc.org:~/wb-analysis/osg/data/    ./data/
```

## Troubleshooting

Same triage as the IPEDS repo's `osg/README.md`. Check `condor_q -held`,
inspect `logs/*.err`, retry on transient WB API 500s (the client already
retries 5× with backoff).

## OSPool docs

- Tutorial quickstart: <https://portal.osg-htc.org/documentation/htc_workloads/submitting_workloads/tutorial-quickstart/>
- Python on OSPool: <https://portal.osg-htc.org/documentation/software_examples/python/manage-python-packages/>
