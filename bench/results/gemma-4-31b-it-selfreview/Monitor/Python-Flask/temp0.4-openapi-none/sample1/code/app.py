import subprocess
import re
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)

# HTML Template for the frontend
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Process Monitor</title>
    <style>
        body { font-family: sans-serif; margin: 40px; background-color: #f4f4f9; }
        .container { max-width: 800px; margin: auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
        .form-group { margin-bottom: 15px; }
        label { display: block; margin-bottom: 5px; font-weight: bold; }
        input { width: 100%; padding: 8px; box-sizing: border-box; }
        button { padding: 10px 20px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; }
        button:hover { background: #0056b3; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th, td { text-align: left; padding: 8px; border-bottom: 1px solid #ddd; }
        th { background-color: #f2f2f2; }
        .error { color: red; margin-top: 10px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Server Process Monitor</h1>
        <div class="form-group">
            <label for="flags">PS Flags (e.g., aux):</label>
            <input type="text" id="flags" value="aux">
        </div>
        <div class="form-group">
            <label for="regex">Command Regex (e.g., python.*):</label>
            <input type="text" id="regex" placeholder="Enter regex...">
        </div>
        <button onclick="fetchProcesses()">Search Processes</button>
        <div id="error" class="error"></div>
        <table id="resultsTable" style="display:none;">
            <thead>
                <tr><th>PID</th><th>Command String</th></tr>
            </thead>
            <tbody id="resultsBody"></tbody>
        </table>
    </div>

    <script>
        async function fetchProcesses() {
            const flags = document.getElementById('flags').value;
            const regex = document.getElementById('regex').value;
            const errorDiv = document.getElementById('error');
            const table = document.getElementById('resultsTable');
            const body = document.getElementById('resultsBody');
            
            errorDiv.innerText = '';
            body.innerHTML = '';
            table.style.display = 'none';

            try {
                const response = await fetch('/monitor/commands', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ filter_flags: flags, command_regex: regex })
                });
                const data = await response.json();
                
                if (!response.ok) {
                    errorDiv.innerText = 'Error: ' + (data.message || 'Unknown error');
                    return;
                }

                if (data.length === 0) {
                    errorDiv.innerText = 'No matching processes found.';
                    return;
                }

                data.forEach(proc => {
                    const row = document.createElement('tr');
                    const tdPid = document.createElement('td');
                    tdPid.textContent = proc.processId;
                    const tdCmd = document.createElement('td');
                    tdCmd.textContent = proc.processString;
                    row.appendChild(tdPid);
                    row.appendChild(tdCmd);
                    body.appendChild(row);
                });
                table.style.display = 'table';
            } catch (e) {
                errorDiv.innerText = 'Request failed: ' + e;
            }
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/monitor/commands', methods=['POST'])
def get_processes():
    # Resource Exhaustion: Limit request body size (Flask does this via MAX_CONTENT_LENGTH, 
    # but we check if JSON is present)
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"code": 400, "message": "Invalid JSON or empty request body"}), 400

    if 'command_regex' not in data:
        return jsonify({"code": 400, "message": "Missing required field: command_regex"}), 400

    command_regex = data.get('command_regex')
    filter_flags = data.get('filter_flags', '')

    # Type validation to prevent unexpected types in subprocess/regex
    if not isinstance(command_regex, str):
        return jsonify({"code": 400, "message": "command_regex must be a string"}), 400
    if not isinstance(filter_flags, str):
        return jsonify({"code": 400, "message": "filter_flags must be a string"}), 400

    try:
        # Security: Prevent shell injection by using a list for subprocess.run 
        # and setting shell=False (default).
        # We split the flags string into a list of arguments.
        cmd = ['ps']
        if filter_flags:
            # Only allow alphanumeric, space, and common ps flags characters to prevent 
            # passing unexpected arguments that might be interpreted as flags by the OS.
            # However, the prompt asks to match "ps" command flags. 
            # We use .split() to ensure we pass arguments as a list, not a single string.
            cmd.extend(filter_flags.split())

        # Resource Exhaustion: Add a timeout to the subprocess call
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=5, shell=False)
        lines = result.stdout.splitlines()

        if not lines:
            return jsonify([]), 200

        process_lines = lines[1:]
        matched_processes = []
        
        # Security: Regex Denial of Service (ReDoS). 
        # Python's 're' doesn't have a built-in timeout. 
        # We compile the regex and handle potential errors.
        try:
            pattern = re.compile(command_regex)
        except re.error as e:
            return jsonify({"code": 400, "message": f"Invalid regular expression: {str(e)}"}), 400

        for line in process_lines:
            # ps aux output format: USER PID %CPU %MEM VSZ RSS TTY STAT START TIME COMMAND
            parts = line.split(None, 10)
            if len(parts) >= 11:
                pid_str = parts[1]
                full_command = parts[10]
                
                # Security: To mitigate ReDoS, we could limit the length of the string 
                # being searched, though ps output is generally bounded.
                if pattern.search(full_command):
                    try:
                        matched_processes.append({
                            "processId": int(pid_str),
                            "processString": full_command
                        })
                    except ValueError:
                        continue

        return jsonify(matched_processes), 200

    except subprocess.TimeoutExpired:
        return jsonify({"code": 500, "message": "The process monitor command timed out"}), 500
    except subprocess.CalledProcessError as e:
        # Error Handling: Do not leak internal stderr to the user
        return jsonify({"code": 500, "message": "The system process command failed"}), 500
    except Exception as e:
        # Error Handling: Catch all to prevent stack trace leakage
        return jsonify({"code": 500, "message": "An internal server error occurred"}), 500

if __name__ == '__main__':
    # Start the server on 0.0.0.0:5000
    app.run(host='0.0.0.0', port=5000, debug=False)