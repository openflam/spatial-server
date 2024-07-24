import subprocess
import sys


def run_command(cmd, shell=False, verbose=False):
    """Runs a command and returns the output.

    Args:
        cmd: Command to run.
        verbose: If True, logs the output of the command.
    Returns:
        The output of the command if return_output is True, otherwise None.
    """
    out = subprocess.run(
        cmd, shell=shell, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
    )
    if out.returncode != 0:
        print(f"Error running command: {cmd}")
        print(out.stderr.decode("utf-8"))
        sys.exit(1)
    print("\nExecuted command: ", " ".join(cmd))
    if verbose:
        print(out.stdout.decode("utf-8"))
        print("\n\n")
    return out
