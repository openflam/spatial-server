import subprocess


def run_command(command, verbose=False, log_filepath=None):
    try:
        # Execute the command
        result = subprocess.run(command, capture_output=True, text=True)

        # Combine stdout and stderr into output_str
        output_str = f"\nLog from command: {command}\n"
        output_str = output_str + result.stdout + result.stderr

        # If verbose is True, print the output
        if verbose and output_str:
            print(output_str)

        # If a log file path is specified, append output_str to the file
        if log_filepath and output_str:
            with open(log_filepath, "a") as log:
                log.write(output_str)

    except Exception as e:
        print(f"An error occurred while running the command: {e}")
