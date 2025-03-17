from html import escape
import os
import subprocess

from flask import Blueprint, render_template, request


bp = Blueprint("view_logs", __name__, url_prefix="/view_logs")


@bp.route("/", methods=["GET"])
def render_logs_map_select():
    map_names_list = os.listdir("data/map_data")
    return render_template("view_logs/select_map.html", map_names_list=map_names_list)


@bp.route("/<mapname>", methods=["GET"])
def render_logs_stream(mapname):
    return render_template("view_logs/logs_viewer.html", mapname=mapname)


@bp.route("/logs_stream", methods=["POST"])
def stream_logs():
    """
    Send logs to the client starting from log_line_number to the end of the log file.
    """
    print("stream_logs route")
    mapname = request.form.get("mapname")
    log_line_number = int(request.form.get("line_number"))

    log_filepath = f"data/map_data/{mapname}/log.txt"

    if not os.path.exists(log_filepath):
        return {"log": "Log file not found", "line_number": -1}, 500

    # Initial request. Send the last 50 lines of the log file along with the line number.
    if log_line_number == -1:
        count_lines_command_output = subprocess.run(
            ["wc", "-l", log_filepath],
            capture_output=True,
        )
        if count_lines_command_output.returncode != 0:
            return {
                "log": "Error counting lines in the log file. Error: "
                + count_lines_command_output.stderr.decode(),
                "line_number": -1,
            }, 500

        total_lines = int(count_lines_command_output.stdout.decode().split()[0])

        tail_command_output = subprocess.run(
            ["tail", "-n", "50", log_filepath],
            capture_output=True,
        )
        if tail_command_output.returncode != 0:
            return {
                "log": "Error reading the log file. Error: "
                + tail_command_output.stderr.decode(),
                "line_number": -1,
            }, 500

        line_number = total_lines
        last_lines_str = tail_command_output.stdout.decode()

    # If the log line number is provided, send the log from that line to the end of the file.
    else:
        tail_command_output = subprocess.run(
            ["tail", "-n", f"+{log_line_number+1}", log_filepath],
            capture_output=True,
        )
        if tail_command_output.returncode != 0:
            return {
                "log": "Error reading the log file. Error: "
                + tail_command_output.stderr.decode(),
                "line_number": -1,
            }
        last_lines_str = tail_command_output.stdout.decode()

        line_number = log_line_number + len(last_lines_str.split("\n")) - 1

    last_lines_str = escape(last_lines_str)
    last_lines_str = last_lines_str.replace("\n", "<br>")

    return {"log": last_lines_str, "line_number": line_number}, 200
