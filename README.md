# valkey-benchmark-tools

This repo contains workflows and tools for benchmarking unstable branch as well as compare different commits/versions of Valkey

### [DAILY VALKEY performance benchmarks](https://d5gk5hctlvf6n.cloudfront.net/)

## Workflows

The CI workflow runs nightly on a EC2 instance to run valkey-benchmarking and uploads the results to a S3 bucket. 
These daily results can be seen on [here](https://d5gk5hctlvf6n.cloudfront.net/) to compare the results daily.

## Tools:

The file [run_benchmark_tool.py](https://github.com/roshkhatri/valkey-benchmark-tools/blob/main/run_benchmark_tool.py) is a tool that can be used to get performance numbers for different commands as well as different modes of Valkey in a CSV format.
These csv files can be used to visualise and compare the results for versions/commits (2 for now) using the [page.html](https://github.com/roshkhatri/valkey-benchmark-tools/blob/main/page.html) file.
