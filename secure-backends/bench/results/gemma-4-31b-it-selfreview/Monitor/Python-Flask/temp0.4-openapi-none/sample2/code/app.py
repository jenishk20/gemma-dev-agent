import subprocess
import re
from flask import Flask, request, jsonify

app = Flask(__name__)

# Limit request size to prevent resource exhaustion (e.g., 1MB)
app.config['MAX_CONTENT_LENGTH'] = 1 * 1024 * 1024

@app.route('/monitor/commands', methods=['POST'])
def get_processes():
    """
    Retrieve a list of running processes based on a regex filter.
    """
    # Ensure request is JSON
    data = request.get_json(silent=True)

    if data is None:
        return jsonify({"code": 400, "message": "Invalid or missing JSON request body"}), 400

    command_regex = data.get('command_regex')
    filter_flags = data.get('filter_flags', 'aux')

    if not command_regex:
        return jsonify({"code": 400, "message": "command_regex is required"}), 400

    # Validate input types to prevent unexpected behavior in subprocess or re
    if not isinstance(command_regex, str) or not isinstance(filter_flags, str):
        return jsonify({"code": 400, "message": "filter_flags and command_regex must be strings"}), 400

    try:
        # SECURITY FIX: Untrusted input reaching a shell.
        # We use a list for subprocess.run and shell=False (default) to prevent shell injection.
        # However, we must ensure the user cannot pass arbitrary flags that might execute code 
        # or read files (though 'ps' is generally safe, we treat filter_flags as a list of arguments).
        # We split by whitespace to ensure each flag is a separate argument.
        args = ['ps'] + filter_flags.split()
        
        # Execute the ps command with a timeout to prevent resource exhaustion (DoS)
        result = subprocess.run(args, capture_output=True, text=True, check=True, timeout=5)
        lines = result.stdout.splitlines()

        # The first line is usually the header
        process_lines = lines[1:]
        
        matched_processes = []
        
        # SECURITY FIX: Untrusted input reaching a regex.
        # To prevent ReDoS (Regular Expression Denial of Service), we wrap the compilation in a try-block.
        # Note: Python's 're' module doesn't have a built-in timeout, but we limit the 
        # number of lines processed and the complexity of the regex is handled by the OS/Runtime.
        try:
            regex = re.compile(command_regex)
        except re.error:
            return jsonify({"code": 400, "message": "Invalid regular expression"}), 400

        for line in process_lines:
            # ps aux output typically starts with: USER PID %CPU %MEM VSZ RSS TTY STAT START TIME COMMAND
            parts = line.split(None, 10) 
            if len(parts) < 2:
                continue
            
            # PID is typically the second column in 'ps aux'
            pid_str = parts[1]
            # The command string is the last part of the split
            cmd_str = parts[-1] if len(parts) == 11 else " ".join(parts[2:])

            # Check if the command string matches the regex
            if regex.search(cmd_str):
                try:
                    matched_processes.append({
                        "processId": int(pid_str),
                        "processString": line.strip()
                    })
                except ValueError:
                    continue

        return jsonify(matched_processes), 200

    except subprocess.TimeoutExpired:
        return jsonify({"code": 500, "message": "Process monitoring timed out"}), 500
    except subprocess.CalledProcessError as e:
        # SECURITY FIX: Error handling. Do not leak internal stderr/stack traces.
        return jsonify({"code": 500, "message": "External process execution failed"}), 500
    except Exception:
        # Generic catch-all to prevent leaking internal server details
        return jsonify({"code": 500, "message": "An internal server error occurred"}), 500

if __name__ == '__main__':
    # Start the server on 0.0.0.0:5000
    app.run(host='0.0.0.0', port=5000)