import subprocess
import csv
from datetime import datetime
import os
import signal
import time
import itertools
import json

valkey_cli = ["src/valkey-cli"]
valkey_benchmark = ["src/valkey-benchmark"]


def clean_value(value):
    """Remove extra quotes and whitespace from a value."""
    return value.strip().strip('"').strip()


def print_command(command):
    """Print the command being executed."""
    print(f">>>> Running command: {' '.join(command)} <<<<")


def run_subprocess(command, check=True):
    """Run a subprocess command and handle errors."""
    try:
        print_command(command)
        subprocess.run(command, text=True, check=check)
    except subprocess.CalledProcessError as e:
        print(f"Command failed with error: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")


def clean_and_make_valkey(version, tls):
    """Clean and build Valkey with the specified version."""
    run_subprocess(["make", "distclean"])
    run_subprocess(["git", "checkout", str(version)])
    if tls:
        run_subprocess(["make", "BUILD_TLS=yes", "-j"])
    else:
        run_subprocess(["make", "-j"])


def kill_process_by_name(process_name):
    """Terminate a process by its name using SIGKILL."""
    try:
        result = subprocess.run(["pgrep", process_name], capture_output=True, text=True)
        pids = result.stdout.strip().split("\n")
        for pid in pids:
            if pid:
                os.kill(int(pid), signal.SIGKILL)
                print(f"Process '{process_name}' with PID {pid} has been terminated.")
    except Exception as e:
        print(f"An error occurred while trying to kill the process: {e}")


def run_valkey_server(cluster_mode, tls, engine):
    """Start Valkey server with the specified cluster mode."""
    if tls:
        valkey_server_cmd = [
            "taskset",
            "-c",
            "0-1",
            "src/valkey-server",
            "--tls-port",
            "6379",
            "--port",
            "0",
            "--tls-cert-file",
            f"./tests/tls/{engine}.crt",
            "--tls-key-file",
            f"./tests/tls/{engine}.key",
            "--tls-ca-cert-file",
            "./tests/tls/ca.crt",
            "--daemonize",
            "yes",
            "--maxmemory-policy",
            "allkeys-lru",
            "--appendonly",
            "no",
            "--cluster-enabled",
            str(cluster_mode),
            "--logfile",
            f"valkey_log_cluster_{cluster_mode}",
            "--save",
            "''",
        ]
    else:
        valkey_server_cmd = [
            "taskset",
            "-c",
            "0-1",
            "src/valkey-server",
            "--daemonize",
            "yes",
            "--maxmemory-policy",
            "allkeys-lru",
            "--appendonly",
            "no",
            "--cluster-enabled",
            str(cluster_mode),
            "--logfile",
            f"valkey_log_cluster_{cluster_mode}",
            "--save",
            "''",
        ]
    run_subprocess(valkey_server_cmd)

    if cluster_mode == "yes":
        # Wait to ensure the server is fully started before issuing CLI commands
        time.sleep(5)
        cluster_cmd_reset = ["CLUSTER", "RESET", "HARD"]
        cluster_cmd_add_slots = ["CLUSTER", "ADDSLOTSRANGE", "0", "16383"]
        if tls:
            cluster_cmd_reset = valkey_cli + tls_cmd + cluster_cmd_reset
            cluster_cmd_add_slots = valkey_cli + tls_cmd + cluster_cmd_add_slots
        else:
            cluster_cmd_reset = valkey_cli + cluster_cmd_reset
            cluster_cmd_add_slots = valkey_cli + cluster_cmd_add_slots
        run_subprocess(cluster_cmd_reset)
        time.sleep(5)
        run_subprocess(cluster_cmd_add_slots)
        time.sleep(5)


def run_valkey_benchmark(combinations, cluster_mode, output_file, version, tls_cmd, tls, engine):
    """Run the Valkey benchmark and save results to a CSV file."""
    with open(output_file, mode="w", newline="") as csvfile:
        fieldnames = [
            "Version",
            "Timestamp",
            "ClusterMode",
            "Command",
            "Pipeline",
            "Data Size (Bytes)",
            "RPS",
            "avg_latency_ms",
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
            
        for i in range(3):
            time.sleep(2)
            print(f">>>> RUN NUMBER {i} for version: {version} <<<<")
            for combination in combinations:
                requests, keyspacelen, data_size, pipeline, command = combination
                if command in ["SET", "RPUSH", "LPUSH", "SADD"]:
                    flushall_cmd = ["FLUSHALL", "SYNC"]
                    if tls:
                        run_flushall_cmd = valkey_cli + tls_cmd + flushall_cmd
                    else:
                        run_flushall_cmd = valkey_cli + flushall_cmd
                    run_subprocess(run_flushall_cmd)
                    kill_process_by_name("valkey-server")
                    time.sleep(3)
                    run_valkey_server(cluster_mode, tls, engine)
                    time.sleep(3)
                    
                
                keyspace = ["info", "Keyspace"]
                if tls:
                    keyspace_cmd = valkey_cli + tls_cmd + keyspace
                else:
                    keyspace_cmd = valkey_cli + keyspace
                print_command(keyspace_cmd)
                keys_cmd_proc = subprocess.run(
                        keyspace_cmd, capture_output=True, text=True, check=True
                    )
                print(keys_cmd_proc.stdout)
                
                cmd = [
                    "-P",
                    str(pipeline),
                    "-r",
                    str(keyspacelen),
                    "-n",
                    str(requests),
                    "-d",
                    str(data_size),
                    "-t",
                    command,
                    "--csv",
                ]
                if tls:
                    cmd = valkey_benchmark + tls_cmd + cmd
                else:
                    cmd = valkey_benchmark + cmd
                print_command(cmd)

                try:
                    process = subprocess.run(
                        cmd, capture_output=True, text=True, check=True
                    )
                    output_lines = process.stdout.strip().split("\n")

                    if len(output_lines) == 2:
                        second_row = output_lines[1]
                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        values = [clean_value(value) for value in second_row.split(",")]

                        if len(values) >= 3:
                            writer.writerow(
                                {
                                    "Version": version,
                                    "Timestamp": timestamp,
                                    "ClusterMode": cluster_mode,
                                    "Command": values[0],
                                    "Pipeline": pipeline,
                                    "Data Size (Bytes)": data_size,
                                    "RPS": values[1],
                                    "avg_latency_ms": values[2],
                                }
                            )
                        else:
                            print(f"Unexpected output format: {second_row}")
                    else:
                        print(f"Insufficient output lines: {output_lines}")

                except subprocess.CalledProcessError as e:
                    print(f"Command failed with error: {e}")

                except Exception as e:
                    print(f"An error occurred: {e}")

# Parameters
versions = ["7.2.6"] #version/
requests = keyspacelen = 10000000
data_sizes = [16, 128, 1024]
pipelines = [10]
commands = ["SET", "GET", "RPUSH", "LPUSH", "LPOP", "SADD", "SPOP", "HSET"]
cluster_modes = ["no", "yes"]
output_file = "valkey_benchmark_results.csv"
bucket_name = "valkey-benchmark-results"
tls_modes = [False, True]

combinations = list(
    itertools.product([requests], [keyspacelen], data_sizes, pipelines, commands)
)

# Run the benchmark and save the results to CSV.
for tls in tls_modes:
    for version in versions:
        if version == "7.2.6":
            engine = "redis"
        else:
            engine = "valkey"
        tls_cmd = [
            "--tls",
            "--cert",
            f"./tests/tls/{engine}.crt",
            "--key",
            f"./tests/tls/{engine}.key",
            "--cacert",
            "./tests/tls/ca.crt",
        ]
        clean_and_make_valkey(version, tls)
        for cluster_mode in cluster_modes:
            kill_process_by_name("valkey-server")
            if tls:
                p = subprocess.Popen(["./utils/gen-test-certs.sh"], stdin=subprocess.PIPE)
                p.wait()
                output_file_versioned = (
                    f"{version}_cluster_{cluster_mode}_tls_{output_file}"
                )
            else:
                output_file_versioned = f"{version}_cluster_{cluster_mode}_{output_file}"
            run_valkey_server(cluster_mode, tls, engine)
            run_valkey_benchmark(combinations, cluster_mode, output_file_versioned, version, tls_cmd, tls, engine)
            kill_process_by_name("valkey-server")
            time.sleep(5)
