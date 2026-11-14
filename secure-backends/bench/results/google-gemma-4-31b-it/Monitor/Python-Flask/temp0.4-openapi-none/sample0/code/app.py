import subprocess
import re
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)

# HTML Template for a simple frontend to interact with the API
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
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
                    const row = `<tr><td>${proc.processId}</td><td>${proc.processString}</td></tr>`;
                    tbody.innerHTML += row;
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
    data = request.get_json()
    if not data:
        return jsonify({"code": 400, "message": "Invalid JSON body"}), 400

    command_regex = data.get('command_regex')
    filter_flags = data.get('filter_flags', 'aux')

    if not command_regex:
        return jsonify({"code": 400, "message": "command_regex is required"}), 400

    try:
        # Construct the ps command. 
        # We use shell=False for security, but we must split the flags.
        # Since the prompt says "command" parameter is not supported, we rely on ps flags.
        cmd = ['ps'] + filter_flags.split()
        
        # Execute ps command
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        lines = result.stdout.splitlines()

        # The first line of 'ps aux' is usually the header
        if len(lines) > 1:
            header = lines[0]
            # Find the position of the PID column. 
            # In 'aux', PID is usually the 2nd column.
            # We'll parse the output line by line.
            
            matched_processes = []
            regex = re.compile(command_regex)

            for line in lines[1:]:
                # ps aux output: USER PID %CPU %MEM VSZ RSS TTY STAT START TIME COMMAND
                parts = line.split(None, 10) # Split into 11 parts
                if len(parts) >= 11:
                    pid = parts[1]
                    full_command = parts[10]
                    
                    # Match the regex against the full line or just the command string
                    # The OpenAPI says "command string matches", so we check the command part.
                    if regex.search(full_command):
                        try:
                            matched_processes.append({
                                "processId": int(pid),
                                "processString": full_command
                            })
                        except ValueError:
                            continue
            
            return jsonify(matched_processes), 200
        else:
            return jsonify([]), 200

    except subprocess.CalledProcessError as e:
        return jsonify({"code": 500, "message": f"ps command failed: {str(e)}"}), 500
    except re.error as e:
        return jsonify({"code": 400, "message": f"Invalid regular expression: {str(e)}"}), 400
    except Exception as e:
        return jsonify({"code": 500, "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)