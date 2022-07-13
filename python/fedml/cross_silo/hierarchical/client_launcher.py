# Script for running distributed clients using torchrun

from platform import node
import sys
from fedml.arguments import load_arguments
import subprocess
import os
from fedml.constants import (
    FEDML_CROSS_SILO_SCENARIO_HIERARCHICAL,
    FEDML_TRAINING_PLATFORM_CROSS_SILO,
)

# env_variables = {
#     'NCCL_DEBUG':'INFO',
#     'NCCL_MIN_NRINGS':1,
#     'NCCL_TREE_THRESHOLD':4294967296,
#     'OMP_NUM_THREADS':8,
#     'NCCL_NSOCKS_PERTHREAD':8,
#     'NCCL_SOCKET_NTHREADS':8,
#     'NCCL_BUFFSIZE':1048576,
#     'NCCL_IB_DISABLE'=1
#     'NCCL_SOCKET_IFNAME'='$NETWORK_INTERFACE'
#     'GLOO_SOCKET_IFNAME'=$'NETWORK_INTERFACE'
#     'TP_SOCKET_IFNAME'=$'NETWORK_INTERFACE'
# }


def launch_dist_trainers(torch_client_filename="torch_client.py"):
    print("SSSSSSSSSEEEEETTTTTTTTTTTEEE")
    inputs = sys.argv[1:]
    args = load_arguments(FEDML_TRAINING_PLATFORM_CROSS_SILO)
    if args.scenario == FEDML_CROSS_SILO_SCENARIO_HIERARCHICAL:
        run_cross_silo_hierarchical(torch_client_filename, args, inputs)
    else:
        run_cross_silo_horizontal(torch_client_filename, args, inputs)


def run_cross_silo_horizontal(torch_client_filename, args, inputs):
    python_path = subprocess.run(
        ["which", "python"], capture_output=True, text=True
    ).stdout.strip()
    process_arguments = [python_path, torch_client_filename] + inputs
    subprocess.run(process_arguments)


def run_cross_silo_hierarchical(torch_client_filename, args, inputs):

    def get_torchrun_arguments(node_rank):
            torchrun_path = subprocess.run(
                ["which", "torchrun"], capture_output=True, text=True
            ).stdout.strip()

            return [
                torchrun_path,
                f"--nnodes={args.n_node_in_silo}",
                f"--nproc_per_node={args.n_proc_per_node}",
                # "--rdzv_backend=c10d",
                f"--rdzv_endpoint={args.master_address}:{args.launcher_rdzv_port}",
                f"--node_rank={node_rank}",
                "--rdzv_id=hi_fl",
                torch_client_filename,
            ] + inputs


    network_interface = (
        None
        if not hasattr(args, "network_interface")
        else args.network_interface
    )
    print(
        f"Using network interface {network_interface} for process group and TRPC communication"
    )
    env_variables = {
        "OMP_NUM_THREADS": "4",
    }
    if network_interface:
        env_variables = {
            **env_variables,
            "NCCL_SOCKET_IFNAME": network_interface,
            "GLOO_SOCKET_IFNAME": network_interface,
        }

    if hasattr(args, "manual_launch") and args.manual_launch:
        print(f"Manual Clinent Launcher")
        node_rank = args.node_rank
        torchrun_cmd_arguments = get_torchrun_arguments(node_rank)
        process_args = torchrun_cmd_arguments
        print(f"Launching node {node_rank} of silo {args.rank}")
        print(process_args)
        subprocess.run(process_args,  env=dict(os.environ, **env_variables))

    else:
        print(f"Automatic Clinent Launcher")
        print(f"Launching nodes using pdsh")

        os.environ["PDSH_RCMD_TYPE"] = "ssh"
        node_addresses = ",".join(args.node_addresses)
        pdsh_cmd_aruments = ["pdsh", "-w", node_addresses]

        exports = ""
        for key, val in env_variables.items():
            exports += "export {}={}; ".format(key, val)
        prerun_args = [
            exports,
            f"cd {os.path.abspath('.')};",
        ]

        node_rank = "%n"    
        torchrun_cmd_arguments = get_torchrun_arguments(node_rank)
        process_args = pdsh_cmd_aruments + prerun_args + torchrun_cmd_arguments
        subprocess.run(process_args)

