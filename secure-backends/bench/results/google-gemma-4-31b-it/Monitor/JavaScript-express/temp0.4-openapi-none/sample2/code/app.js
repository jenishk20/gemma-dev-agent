const express = require('express');
const { exec } = require('child_process');

const app = express();
app.use(express.json());

/**
 * Implementation of the Monitor Service
 * 
 * The endpoint /monitor/commands takes a POST request with:
 * - filter_flags: optional flags for the 'ps' command (e.g., "aux")
 * - command_regex: a regex string to filter the process list
 */
app.post('/monitor/commands', (req, res) => {
    const { filter_flags, command_regex } = req.body;

    if (!command_regex) {
        return res.status(400).json({
            code: 400,
            message: "Missing required field: command_regex"
        });
    }

    // Sanitize filter_flags to prevent command injection
    // Only allow alphanumeric characters, spaces, and hyphens
    const sanitizedFlags = filter_flags ? filter_flags.replace(/[^a-zA-Z0-9\s-]/g, '') : '';
    
    // Construct the ps command. 
    // Since 'command' parameter is not supported, we use standard ps flags.
    const psCommand = `ps ${sanitizedFlags}`.trim();

    exec(psCommand, (error, stdout, stderr) => {
        if (error) {
            return res.status(500).json({
                code: 500,
                message: `Error executing ps command: ${error.message}`
            });
        }

        try {
            const regex = new RegExp(command_regex);
            const lines = stdout.split('\n');
            const results = [];

            // Skip the header line (usually the first line of ps output)
            for (let i = 1; i < lines.length; i++) {
                const line = lines[i].trim();
                if (!line) continue;

                if (regex.test(line)) {
                    // Extract PID. In most 'ps' outputs, the PID is the first or second column.
                    // We split by whitespace and assume the first numeric-looking block is the PID.
                    const parts = line.split(/\s+/);
                    let pid = null;
                    
                    // Look for the first part that is a valid integer (PID)
                    for (const part of parts) {
                        if (/^\d+$/.test(part)) {
                            pid = parseInt(part, 10);
                            break;
                        }
                    }

                    if (pid !== null) {
                        results.push({
                            processId: pid,
                            processString: line
                        });
                    }
                }
            }

            res.status(200).json(results);
        } catch (regexError) {
            res.status(400).json({
                code: 400,
                message: `Invalid regular expression: ${regexError.message}`
            });
        }
    });
});

const PORT = 5000;
const HOST = '0.0.0.0';

app.listen(PORT, HOST, () => {
    console.log(`Monitor Service running at http://${HOST}:${PORT}`);
});