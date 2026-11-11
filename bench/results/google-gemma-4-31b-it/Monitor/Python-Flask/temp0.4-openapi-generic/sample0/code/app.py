import subprocess
import re
from flask import Flask, request, jsonify

app = Flask(__name__)

def sanitize_flags(flags):
    """
    Sanitize filter flags to prevent command injection.
    Only allows alphanumeric characters, spaces, and hyphens.
    """
    if not flags:
        return ""
    # Strict whitelist: only allow characters typically found in ps flags
    return "".join(c for c in flags if c.isalnum() or c in " -")

@app.route('/monitor/commands', methods=['POST'])
def get_processes():
    data = request.get_json()
    
    if not data:
        return jsonify({"code": 400, "message": "Missing request body"}), 400

    command_regex = data.get('command_regex')
    filter_flags = data.get('filter_flags', "")

    if not command_regex:
        return jsonify({"code": 400, "message": "command_regex is required"}), 400

    try:
        # Sanitize flags to prevent shell injection
        safe_flags = sanitize_flags(filter_flags)
        
        # Construct the command. 
        # We use a list for subprocess.run to avoid shell=True vulnerabilities.
        # 'ps' is the base command, followed by the sanitized flags.
        cmd = ["ps"]
        if safe_flags:
            # Split flags by space to pass as individual arguments to ps
            cmd.extend(safe_flags.split())

        # Execute ps command
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        ps_output = result.stdout

        # Compile the regex provided by the user
        # We wrap it in a try-except block in case the regex is invalid
        try:
            pattern = re.compile(command_regex)
        except re.error as e:
            return jsonify({"code": 400, "message": f"Invalid regular expression: {str(e)}"}), 400

        processes = []
        lines = ps_output.splitlines()
        
        # The first line is usually the header, we skip it if it exists
        if lines:
            # We iterate through lines and check if the regex matches the line content
            for line in lines[1:]:
                if pattern.search(line):
                    # ps output typically starts with PID. 
                    # We attempt to extract the first integer found in the line as the PID.
                    parts = line.split()
                    if parts:
                        try:
                            pid = int(parts[0])
                            processes.append({
                                "processId": pid,
                                "processString": line.strip()
                            })
                        except ValueError:
                            # If the first column isn't an integer, this line doesn't match our PID expectation
                            continue

        return jsonify(processes), 200

    except subprocess.CalledProcessError as e:
        return jsonify({"code": 500, "message": f"Error executing ps command: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"code": 500, "message": f"Internal server error: {str(e)}"}), 500

if __name__ == '__main__':
    # Run on 0.0.0.0:5000 as requested
    app.run(host='0.0.0.0', port=5000)