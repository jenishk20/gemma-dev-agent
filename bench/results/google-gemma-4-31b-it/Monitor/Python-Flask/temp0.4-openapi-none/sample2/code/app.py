import subprocess
import re
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/monitor/commands', methods=['POST'])
def get_processes():
    """
    Retrieve a list of running processes based on a regex filter.
    """
    data = request.get_json()

    if not data:
        return jsonify({"code": 400, "message": "Missing request body"}), 400

    command_regex = data.get('command_regex')
    filter_flags = data.get('filter_flags', 'aux')

    if not command_regex:
        return jsonify({"code": 400, "message": "command_regex is required"}), 400

    try:
        # We use 'ps' with the provided flags. 
        # Since 'command' parameter is not supported, we rely on standard output parsing.
        # We split the filter_flags to pass them as separate arguments to subprocess.
        args = ['ps'] + filter_flags.split()
        
        # Execute the ps command
        result = subprocess.run(args, capture_output=True, text=True, check=True)
        lines = result.stdout.splitlines()

        # The first line is usually the header
        process_lines = lines[1:]
        
        matched_processes = []
        regex = re.compile(command_regex)

        for line in process_lines:
            # ps aux output typically starts with: USER PID %CPU %MEM VSZ RSS TTY STAT START TIME COMMAND
            # We split by whitespace. The first few columns are metadata, the rest is the command string.
            parts = line.split(None, 10) # Split into 11 parts max
            if len(parts) < 11:
                # If the line doesn't have enough columns, it might be a short output or different flag set
                # We'll try to find the PID (usually 2nd column) and treat the rest as the command string
                if len(parts) >= 2:
                    pid_str = parts[1]
                    cmd_str = " ".join(parts[2:])
                else:
                    continue
            else:
                pid_str = parts[1]
                cmd_str = parts[10]

            # Check if the command string matches the regex
            if regex.search(cmd_str):
                try:
                    matched_processes.append({
                        "processId": int(pid_str),
                        "processString": line.strip()
                    })
                except ValueError:
                    # Skip if PID is not an integer
                    continue

        return jsonify(matched_processes), 200

    except subprocess.CalledProcessError as e:
        return jsonify({"code": 500, "message": f"Error executing ps command: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"code": 500, "message": str(e)}), 500

if __name__ == '__main__':
    # Start the server on 0.0.0.0:5000
    app.run(host='0.0.0.0', port=5000)