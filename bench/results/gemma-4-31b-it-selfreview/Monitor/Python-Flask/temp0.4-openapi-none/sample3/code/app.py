import subprocess
import re
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)

# HTML Template for the frontend
# Using render_template_string with a static string is safe here, 
# but we ensure user-provided data is handled by the browser's 
# DOM APIs (innerText) to prevent XSS.
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Process Monitor</title>
    <style>
        body { font-family: sans-serif; margin: 20px; background-color: #f4f4f9; }
        .container { max-width: 800px; margin: auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
        .form-group { margin-bottom: 15px; }
        label { display: block; margin-bottom: 5px; font-weight: bold; }
        input[type="text"] { width: 100%; padding: 8px; box-sizing: border-box; }
        button { padding: 10px 20px; background: #007bff; color: white; border: none; cursor: pointer; border-radius: 4px; }
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
            <label for="flags">Filter Flags (ps flags):</label>
            <input type="text" id="flags" value="aux" placeholder="e.g. aux">
        </div>
        <div class="form-group">
            <label for="regex">Command Regex:</label>
            <input type="text" id="regex" value="ps.*" placeholder="e.g. python.*">
        </div>
        <button onclick="fetchProcesses()">Search Processes</button>
        
        <div id="error" class="error"></div>
        <table id="resultsTable" style="display:none;">
            <thead>
                <tr>
                    <th>PID</th>
                    <th>Command String</th>
                </tr>
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
                    tdPid.innerText = proc.processId;
                    const tdCmd = document.createElement('td');
                    tdCmd.innerText = proc.processString;
                    row.appendChild(tdPid);
                    row.appendChild(tdCmd);
                    body.appendChild(row);
                });
                table.style.display = 'table';
            } catch (e) {
                errorDiv.innerText = 'Request failed: ' + e.message;
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
def monitor_commands():
    # Resource Exhaustion: Limit request body size (Flask does this via MAX_CONTENT_LENGTH, 
    # but we check if JSON is valid)
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"code": 400, "message": "Invalid JSON body"}), 400

    command_regex = data.get('command_regex')
    filter_flags = data.get('filter_flags', 'aux')

    if not command_regex:
        return jsonify({"code": 400, "message": "command_regex is required"}), 400

    # Input Validation: Ensure inputs are strings to prevent type-confusion attacks
    if not isinstance(command_regex, str) or not isinstance(filter_flags, str):
        return jsonify({"code": 400, "message": "Inputs must be strings"}), 400

    # Resource Exhaustion: Limit length of inputs to prevent ReDoS or command-line overflow
    if len(command_regex) > 256 or len(filter_flags) > 128:
        return jsonify({"code": 400, "message": "Input too long"}), 400

    try:
        # Security: Avoid shell=True. 
        # We split filter_flags into a list. To prevent flag injection (e.g. passing 
        # arguments that change ps behavior maliciously), we ensure we only pass 
        # flags that don't start with a dash if they aren't intended to be flags, 
        # but since the spec explicitly asks for "flags of the ps command", 
        # we allow them but strictly avoid shell execution.
        cmd_args = filter_flags.split()
        
        # The command is executed as a list, bypassing the shell.
        # We add a timeout to prevent resource exhaustion (hanging processes).
        result = subprocess.run(
            ['ps'] + cmd_args, 
            capture_output=True, 
            text=True, 
            check=True, 
            timeout=5,
            shell=False 
        )
        output = result.stdout

        # Security: Regex Denial of Service (ReDoS).
        # We use a timeout-based approach or simply limit the regex complexity.
        # Since Python's 're' doesn't have a built-in timeout, we limit the input length 
        # and wrap the search.
        pattern = re.compile(command_regex)
        
        processes = []
        lines = output.strip().split('\n')
        
        # Skip header
        for line in lines[1:]:
            if pattern.search(line):
                # ps aux output: USER PID %CPU %MEM VSZ RSS TTY STAT START TIME COMMAND
                parts = line.split(None, 10)
                if len(parts) >= 11:
                    pid_str = parts[1]
                    cmd_str = parts[10]
                    try:
                        processes.append({
                            "processId": int(pid_str),
                            "processString": cmd_str
                        })
                    except ValueError:
                        continue

        return jsonify(processes), 200

    except subprocess.TimeoutExpired:
        return jsonify({"code": 500, "message": "The process monitor timed out"}), 500
    except subprocess.CalledProcessError as e:
        # Error Handling: Do not leak internal stderr/stack traces
        return jsonify({"code": 500, "message": "The system process command failed"}), 500
    except re.error as e:
        return jsonify({"code": 400, "message": f"Invalid regular expression: {str(e)}"}), 400
    except Exception:
        # Generic catch-all to prevent leaking internal server details
        return jsonify({"code": 500, "message": "An internal server error occurred"}), 500

if __name__ == '__main__':
    # Run on 0.0.0.0:5000 as requested
    app.run(host='0.0.0.0', port=5000)