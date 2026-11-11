import re
import subprocess
import shlex
from flask import Flask, request, jsonify

app = Flask(__name__)

def get_running_processes(filter_flags, command_regex):
    """
    Retrieves processes using the 'ps' command and filters them based on a regex.
    """
    # Security: We must strictly validate filter_flags to prevent command injection.
    # Since the user provides flags for 'ps', we only allow alphanumeric characters, 
    # spaces, and a specific set of safe characters common in ps flags (like - or ,).
    # We do NOT allow shell metacharacters like ;, &, |, $, >, <, `, etc.
    if filter_flags:
        if not re.match(r'^[a-zA-Z0-9\s\-,]+$', filter_flags):
            raise ValueError("Invalid characters in filter_flags")

    # Construct the command. 
    # We use a list for subprocess.run to avoid shell=True and prevent injection.
    # We split the filter_flags string into a list of arguments.
    cmd = ['ps']
    if filter_flags:
        cmd.extend(shlex.split(filter_flags))

    try:
        # Run the ps command and capture output
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        if result.returncode != 0:
            return None, f"ps command failed: {result.stderr}"
        
        output = result.stdout
        
        # Compile the regex for filtering
        try:
            pattern = re.compile(command_regex)
        except re.error:
            return None, "Invalid regular expression"

        processes = []
        # ps output usually has a header line. We iterate through lines.
        lines = output.strip().split('\n')
        if not lines:
            return [], None

        # The first line is typically the header (PID, TTY, TIME, CMD etc)
        # We iterate through the lines and try to extract the PID and the full string.
        for line in lines[1:]:
            if pattern.search(line):
                # Extract PID: usually the first column of numeric data
                parts = line.split(None, 1)
                if len(parts) >= 2:
                    pid_str = parts[0]
                    if pid_str.isdigit():
                        processes.append({
                            "processId": int(pid_str),
                            "processString": line.strip()
                        })
        
        return processes, None

    except subprocess.TimeoutExpired:
        return None, "ps command timed out"
    except Exception as e:
        return None, str(e)

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
        processes, error = get_running_processes(filter_flags, command_regex)
        
        if error:
            # Distinguish between validation errors and system errors
            if "Invalid characters" in error or "Invalid regular expression" in error:
                return jsonify({"code": 400, "message": error}), 400
            return jsonify({"code": 500, "message": error}), 500
            
        return jsonify(processes), 200

    except Exception as e:
        return jsonify({"code": 500, "message": str(e)}), 500

if __name__ == '__main__':
    # Start the server on 0.0.0.0:5000
    app.run(host='0.0.0.0', port=5000)