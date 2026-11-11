import re
import subprocess
import shlex
from flask import Flask, request, jsonify

app = Flask(__name__)

def get_processes(filter_flags, command_regex):
    """
    Retrieves processes using the ps command and filters them based on a regex.
    """
    # Security: We must be extremely careful with filter_flags to avoid shell injection.
    # Since the OpenAPI spec allows "flags of the ps command", we validate that 
    # the flags contain only safe characters (alphanumeric, spaces, and common ps flags).
    # We explicitly forbid characters like ';', '&', '|', '>', '<', '`', '$'
    if filter_flags:
        if not re.match(r'^[a-zA-Z0-9\s\-\.]+$', filter_flags):
            raise ValueError("Invalid characters in filter_flags")

    # Construct the command. We use a list for subprocess.run to avoid shell=True.
    # We split the filter_flags into a list of arguments.
    args = ["ps"]
    if filter_flags:
        args.extend(shlex.split(filter_flags))

    try:
        # Execute ps command
        result = subprocess.run(args, capture_output=True, text=True, check=True)
        output = result.stdout
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"ps command failed: {e.stderr}")

    # Compile the regex for filtering
    try:
        pattern = re.compile(command_regex)
    except re.error:
        raise ValueError("Invalid regular expression provided")

    processes = []
    # ps output usually has a header line; we iterate through lines
    lines = output.strip().split('\n')
    if not lines:
        return processes

    # We attempt to extract the PID (usually the first or second column) 
    # and the full command string. Since flags change the output format,
    # we treat the whole line as the process string and use regex to find the PID.
    for line in lines[1:]:  # Skip header
        if pattern.search(line):
            # Extract PID: Look for the first integer in the line
            pid_match = re.search(r'\b(\d+)\b', line)
            if pid_match:
                processes.append({
                    "processId": int(pid_match.group(1)),
                    "processString": line.strip()
                })

    return processes

@app.route('/monitor/commands', methods=['POST'])
def monitor_commands():
    data = request.get_json()
    
    if not data:
        return jsonify({"code": 400, "message": "Missing request body"}), 400

    command_regex = data.get('command_regex')
    filter_flags = data.get('filter_flags', "")

    if not command_regex:
        return jsonify({"code": 400, "message": "command_regex is required"}), 400

    try:
        results = get_processes(filter_flags, command_regex)
        return jsonify(results), 200
    except ValueError as ve:
        return jsonify({"code": 400, "message": str(ve)}), 400
    except Exception as e:
        return jsonify({"code": 500, "message": f"Internal server error: {str(e)}"}), 500

if __name__ == '__main__':
    # Run on 0.0.0.0:5000 as requested
    app.run(host='0.0.0.0', port=5000)