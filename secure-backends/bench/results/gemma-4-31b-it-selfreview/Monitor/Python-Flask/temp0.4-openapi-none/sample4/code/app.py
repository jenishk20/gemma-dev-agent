import subprocess
import re
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)

# HTML Template for the frontend
# Using Jinja2's auto-escaping via render_template_string to prevent XSS
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Process Monitor</title>
    <style>
        body { font-family: sans-serif; margin: 40px; background-color: #f4f4f9; }
        .container { max-width: 800px; margin: auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .form-group { margin-bottom: 15px; }
        label { display: block; margin-bottom: 5px; font-weight: bold; }
        input[type="text"] { width: 100%; padding: 8px; box-sizing: border-box; }
        button { padding: 10px 20px; background: #007bff; color: white; border: none; cursor: pointer; border-radius: 4px; }
        button:hover { background: #0056b3; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th, td { text-align: left; padding: 10px; border-bottom: 1px solid #ddd; }
        th { background-color: #f8f9fa; }
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
            <label for="regex">Command Regex:</label>
            <input type="text" id="regex" placeholder="e.g. python.*">
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
            const tbody = document.getElementById('resultsBody');
            
            errorDiv.innerText = '';
            tbody.innerHTML = '';
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
                    const row = tbody.insertRow();
                    const cellPid = row.insertCell(0);
                    const cellStr = row.insertCell(1);
                    cellPid.innerText = proc.processId;
                    cellStr.innerText = proc.processString;
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
    # Resource Exhaustion: Limit request body size to 1MB
    if request.content_length and request.content_length > 1024 * 1024:
        return jsonify({"code": 400, "message": "Request body too large"}), 400

    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"code": 400, "message": "Invalid JSON or missing request body"}), 400
    
    command_regex = data.get('command_regex')
    filter_flags = data.get('filter_flags', 'aux')

    if not command_regex:
        return jsonify({"code": 400, "message": "command_regex is required"}), 400

    # Input Validation: Ensure flags contain only safe characters to prevent argument injection
    # We only allow alphanumeric, spaces, and common ps flag characters (-, a-z, A-Z)
    if not re.match(r'^[a-zA-Z0-9\s\-]*$', str(filter_flags)):
        return jsonify({"code": 400, "message": "Invalid characters in filter_flags"}), 400

    try:
        # Security: Use a list for subprocess.run to avoid shell=True and shell injection.
        # We split the flags into a list.
        cmd = ['ps'] + filter_flags.split()
        
        # Resource Exhaustion: Set a strict timeout for the system call
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            check=True, 
            timeout=5
        )
        output = result.stdout
        
        # Regex Security: To prevent ReDoS (Regular Expression Denial of Service), 
        # we wrap the regex execution in a way that we can control. 
        # Python's 're' doesn't have a built-in timeout, but we can limit the input size.
        if len(command_regex) > 256:
            return jsonify({"code": 400, "message": "command_regex too long"}), 400
            
        pattern = re.compile(command_regex)
        
        processes = []
        lines = output.strip().split('\n')
        
        # Skip header line
        for line in lines[1:]:
            if not line.strip():
                continue
                
            # We use a simple search. To mitigate ReDoS, we limit the length of the line being checked.
            if len(line) > 1024:
                line = line[:1024]

            if pattern.search(line):
                parts = line.split()
                if len(parts) >= 2:
                    try:
                        pid = int(parts[1])
                        processes.append({
                            "processId": pid,
                            "processString": line.strip()
                        })
                    except ValueError:
                        continue
        
        return jsonify(processes), 200

    except subprocess.TimeoutExpired:
        return jsonify({"code": 500, "message": "Process monitoring timed out"}), 500
    except subprocess.CalledProcessError as e:
        # Error Handling: Do not leak internal stderr to the user
        return jsonify({"code": 500, "message": "The system process command failed"}), 500
    except re.error as e:
        return jsonify({"code": 400, "message": f"Invalid regular expression: {str(e)}"}), 400
    except Exception:
        # Error Handling: Generic error to avoid leaking stack traces
        return jsonify({"code": 500, "message": "An internal server error occurred"}), 500

if __name__ == '__main__':
    # Run on 0.0.0.0:5000 as requested
    app.run(host='0.0.0.0', port=5000)