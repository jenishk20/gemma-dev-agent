import subprocess
import re
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)

# HTML Template for a simple frontend to interact with the API
# Using Jinja2's automatic escaping via render_template_string for the dynamic content
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Process Monitor</title>
    <style>
        body { font-family: sans-serif; margin: 20px; }
        .container { max-width: 800px; margin: auto; }
        .form-group { margin-bottom: 15px; }
        label { display: block; margin-bottom: 5px; }
        input[type="text"] { width: 100%; padding: 8px; box-sizing: border-box; }
        button { padding: 10px 20px; cursor: pointer; background: #007bff; color: white; border: none; border-radius: 4px; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
        .error { color: red; margin-top: 10px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Server Process Monitor</h1>
        <div class="form-group">
            <label>Filter Flags (ps flags):</label>
            <input type="text" id="filter_flags" value="aux">
        </div>
        <div class="form-group">
            <label>Command Regex:</label>
            <input type="text" id="command_regex" placeholder="e.g. python.*">
        </div>
        <button onclick="fetchProcesses()">Search Processes</button>
        <div id="error" class="error"></div>
        <table id="results" style="display:none;">
            <thead>
                <tr>
                    <th>PID</th>
                    <th>Command String</th>
                </tr>
            </thead>
            <tbody id="results_body"></tbody>
        </table>
    </div>

    <script>
        async function fetchProcesses() {
            const flags = document.getElementById('filter_flags').value;
            const regex = document.getElementById('command_regex').value;
            const errorDiv = document.getElementById('error');
            const table = document.getElementById('results');
            const tbody = document.getElementById('results_body');

            errorDiv.innerText = '';
            tbody.innerHTML = '';
            table.style.display = 'none';

            if (!regex) {
                errorDiv.innerText = 'Command regex is required';
                return;
            }

            try {
                const response = await fetch('/monitor/commands', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ filter_flags: flags, command_regex: regex })
                });
                
                const data = await response.json();
                
                if (!response.ok) {
                    errorDiv.innerText = `Error ${data.code}: ${data.message}`;
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
                    tbody.appendChild(row);
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
def monitor_commands():
    # Resource Exhaustion: Bound request size (Flask default is usually 16MB, 
    # but we can check content length for specific endpoints if needed).
    # We ensure the JSON body is not excessively large.
    if request.content_length and request.content_length > 1024 * 10: # 10KB limit for this API
        return jsonify({"code": 400, "message": "Request body too large"}), 400

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

    try:
        # Security: Prevent Shell Injection. 
        # We use a list for subprocess.run and shell=False (default).
        # However, we must validate that 'filter_flags' doesn't contain malicious 
        # arguments that could be interpreted as flags by 'ps' to execute other logic.
        # We only allow alphanumeric characters, spaces, and a few safe symbols.
        if not re.match(r'^[a-zA-Z0-9\s\-\.,]*$', filter_flags):
            return jsonify({"code": 400, "message": "Invalid characters in filter flags"}), 400

        cmd = ['ps'] + filter_flags.split()
        
        # Resource Exhaustion: Add a timeout to the subprocess call
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            check=True, 
            shell=False, 
            timeout=5
        )
        lines = result.stdout.splitlines()

        if len(lines) > 1:
            matched_processes = []
            # Security: Regex Denial of Service (ReDoS).
            # While we can't fully prevent ReDoS without a specialized engine, 
            # we use a timeout for the overall process and ensure the regex is compiled.
            try:
                regex = re.compile(command_regex)
            except re.error as e:
                return jsonify({"code": 400, "message": f"Invalid regular expression: {str(e)}"}), 400

            for line in lines[1:]:
                # ps aux output: USER PID %CPU %MEM VSZ RSS TTY STAT START TIME COMMAND
                parts = line.split(None, 10)
                if len(parts) >= 11:
                    pid_str = parts[1]
                    full_command = parts[10]
                    
                    if regex.search(full_command):
                        try:
                            matched_processes.append({
                                "processId": int(pid_str),
                                "processString": full_command
                            })
                        except ValueError:
                            continue
            
            return jsonify(matched_processes), 200
        else:
            return jsonify([]), 200

    except subprocess.TimeoutExpired:
        return jsonify({"code": 500, "message": "The ps command timed out"}), 500
    except subprocess.CalledProcessError as e:
        # Error Handling: Return documented error codes, do not leak internal stderr
        return jsonify({"code": 500, "message": "Internal server error executing process monitor"}), 500
    except Exception as e:
        # Error Handling: Catch-all to prevent stack trace leakage
        return jsonify({"code": 500, "message": "An unexpected error occurred"}), 500

if __name__ == '__main__':
    # Running on 0.0.0.0:5000 as requested
    app.run(host='0.0.0.0', port=5000)