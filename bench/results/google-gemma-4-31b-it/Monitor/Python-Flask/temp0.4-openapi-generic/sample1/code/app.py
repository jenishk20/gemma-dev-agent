import subprocess
import re
from flask import Flask, request, jsonify

app = Flask(__name__)

def sanitize_flags(flags):
    """
    Prevents shell injection by restricting flags to a safe set of characters.
    Only allows alphanumeric characters, spaces, and common ps flags.
    """
    if not flags:
        return ""
    # Allow only letters, numbers, spaces, and common ps flags like -a, -u, -x, -T
    if not re.match(r'^[a-zA-Z0-9\s\-]+$', flags):
        raise ValueError("Invalid characters in filter_flags")
    return flags

@app.route('/monitor/commands', methods=['POST'])
def get_processes():
    data = request.get_json()
    
    if not data:
        return jsonify({"code": 400, "message": "Missing request body"}), 400

    command_regex = data.get('command_regex')
    filter_flags = data.get('filter_flags', "")

    if command_regex is None:
        return jsonify({"code": 400, "message": "command_regex is required"}), 400

    try:
        # Sanitize flags to prevent command injection
        safe_flags = sanitize_flags(filter_flags)
        
        # Construct the command. 
        # We use a list for subprocess.run to avoid shell=True and prevent injection.
        # The 'ps' command is called with the provided flags.
        cmd = ['ps']
        if safe_flags:
            cmd.extend(safe_flags.split())

        # Execute ps command
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        output = result.stdout

        # Compile the user-provided regex
        pattern = re.compile(command_regex)
        
        processes = []
        # ps output typically has a header line; we skip it or just let the regex handle it
        lines = output.strip().split('\n')
        
        for line in lines:
            if pattern.search(line):
                # Attempt to extract PID. 
                # In 'ps aux' or similar, PID is usually the first or second column.
                # We split by whitespace and try to find the first integer.
                parts = line.split()
                if not parts:
                    continue
                
                # Heuristic: find the first part that is purely numeric as the PID
                pid = None
                for part in parts:
                    if part.isdigit():
                        pid = int(part)
                        break
                
                if pid is not None:
                    processes.append({
                        "processId": pid,
                        "processString": line.strip()
                    })

        return jsonify(processes), 200

    except ValueError as ve:
        return jsonify({"code": 400, "message": str(ve)}), 400
    except subprocess.CalledProcessError as e:
        return jsonify({"code": 500, "message": f"Error executing ps: {str(e)}"}), 500
    except re.error as e:
        return jsonify({"code": 400, "message": f"Invalid regular expression: {str(e)}"}), 400
    except Exception as e:
        return jsonify({"code": 500, "message": f"Internal server error: {str(e)}"}), 500

if __name__ == '__main__':
    # Run on 0.0.0.0:5000 as requested
    app.run(host='0.0.0.0', port=5000)