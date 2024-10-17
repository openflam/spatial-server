def print_log(log_str, log_filepath=None):
    if log_filepath is None:
        print(log_str)
    else:
        with open(log_filepath, "a") as f:
            f.write(log_str + "\n")
