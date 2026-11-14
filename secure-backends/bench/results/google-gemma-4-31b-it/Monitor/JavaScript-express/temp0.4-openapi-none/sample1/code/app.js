const express = require('express');
const { exec } = require('child_process');

const app = express();
app.use(express.json());

/**
 * Implementation of the Monitor Service
 * Based on the provided OpenAPI schema.
 */

app.post('/monitor/commands', (req, res) => {
    const { filter_flags, command_regex } = req.body;

    // Validation: command_regex is required per schema
    if (command_regex === undefined || command_regex === null) {
        return res.status(400).json({
            code: 400,
            message: "Missing required field: command_regex"
        });
    }

    // Default flags if none provided. 
    // Using 'aux' as a common standard for process listing.
    const flags = filter_flags || 'aux';
    
    // Construct the ps command. 
    // Note: The prompt mentions the "command" parameter is not supported on this OS.
    // We execute ps with the provided flags and then filter the output in JS.
    const psCommand = `ps ${flags}`;

    exec(psCommand, (error, stdout, stderr) => {
        if (error) {
            return res.status(500).json({
                code: 500,
                message: `Error executing ps command: ${error.message}`
            });
        }

        if (stderr) {
            return res.status(500).json({
                code: 500,
                message: `ps command stderr: ${stderr}`
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
                    // ps aux output typically starts with USER, PID, %CPU, %MEM, VSZ, RSS, TTY, STAT, START, TIME, COMMAND
                    // We split by whitespace and take the second element as the PID
                    const parts = line.split(/\s+/);
                    if (parts.length >= 2) {
                        const pid = parseInt(parts[1], 10);
                        if (!isNaN(pid)) {
                            results.push({
                                processId: pid,
                                processString: line
                            });
                        }
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