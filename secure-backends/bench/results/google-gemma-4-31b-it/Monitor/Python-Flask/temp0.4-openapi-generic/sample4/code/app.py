import re
import subprocess
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
        th { background-color: #f2 f2 f2; }
        .error { color: red; margin-top: 10px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Server Process Monitor</h1>
        <div class="form-group">
            <label>Command Regex (Required):</label>
            <input type="text" id="regex" placeholder="e.g. python.*" value=".*">
        </div>
        <div class="form-group">
            <label>PS Flags:</label>
            <input type="text" id="flags" placeholder="e.g. aux" value="aux">
        </div>
        <button onclick="fetchProcesses()">Search Processes</button>
        <div id="error" class="error"></div>
        <table id="resultsTable" style="display:none;">
            <thead>
                <tr><th>PID</th><th>Process String</th></tr>
            </thead>
            <tbody id="resultsBody"></tbody>
        </table>
    </div>

    <script>
        async function fetchProcesses() {
            const regex = document.getElementById('regex').value;
            const flags = document.getElementById('flags').value;
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
                    body: JSON.stringify({ command_regex: regex, filter_flags: flags })
                });
                
                const data = await response.json();
                if (!response.ok) {
                    throw new Error(data.message || 'Server error');
                }

                if (data.length === 0) {
                    errorDiv.innerText = 'No matching processes found.';
                    return;
                }

                data.forEach(proc => {
                    const row = `<tr><td>${proc.processId}</td><td>${proc.processString}</td></tr>`;
                    body.innerHTML += row;
                });
                table.style.display = 'table';
            } catch (e) {
                errorDiv.innerText = 'Error: ' + e.message;
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
        # Security: Validate filter_flags to prevent command injection.
        # We only allow alphanumeric characters, spaces, and hyphens.
        if not re.match(r'^[a-zA-Z0-9\s\-]+$', filter_flags):
            return jsonify({"code": 400, "message": "Invalid characters in filter_flags"}), 400

        # Construct the ps command. 
        # We use a list for subprocess.run to avoid shell=True vulnerabilities.
        # Since 'command' param is not supported, we use flags and grep/regex in Python.
        cmd = ['ps'] + filter_flags.split()
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        
        if result.returncode != 0:
            return jsonify({"code": 500, "message": f"ps command failed: {result.stderr}"}), 500

        # Parse the output of ps
        lines = result.stdout.strip().split('\n')
        if not lines:
            return jsonify([]), 200

        # The first line is usually the header
        header = lines[0]
        process_lines = lines[1:]

        # Compile the regex for filtering
        try:
            pattern = re.compile(command_regex)
        except re.error:
            return jsonify({"code": 400, "message": "Invalid regular expression"}), 400

        matching_processes = []
        for line in process_lines:
            if pattern.search(line):
                # Extract PID. In 'aux' output, PID is typically the first column.
                # We split by whitespace and take the first element.
                parts = line.split()
                if parts:
                    try:
                        pid = int(parts[0]) # This assumes the first column is PID (common in aux)
                        # If the flags change, the PID position might change. 
                        # For a generic implementation, we try to find the first integer.
                        for part in parts:
                            if part.isdigit():
                                pid = int(part)
                                break
                        
                        matching_processes.append({
                            "processId": pid,
                            "processString": line.strip()
                        })
                    except (ValueError, IndexError):
                        continue

        return jsonify(matching_processes), 200

    except subprocess.TimeoutExpired:
        return jsonify({"code": 504, "message": "Process lookup timed out"}), 504
    except Exception as e:
        return jsonify({"code": 500, "message": str(e)}), 500

if __name__ == '__main__':
    # Run on 0.0.0.0:5000 as requested
    app.run(host='0.0.0.0', port=5000, debug=False)