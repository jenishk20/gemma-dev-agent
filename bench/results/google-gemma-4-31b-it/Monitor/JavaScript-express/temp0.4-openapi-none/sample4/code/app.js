const express = require('express');
const { exec } = require('child_process');

const app = express();
app.use(express.json());

/**
 * Implementation of the /monitor/commands endpoint.
 * It executes the 'ps' command with provided flags, 
 * then filters the output using the provided regex.
 */
app.post('/monitor/commands', (req, res) => {
    const { filter_flags, command_regex } = req.body;

    if (command_regex === undefined) {
        return res.status(400).json({
            code: 400,
            message: "Missing required field: command_regex"
        });
    }

    // Default flags if none provided
    const flags = filter_flags || 'aux';
    
    // Construct the ps command. 
    // We use 'ps' and pass the flags. 
    // Note: We avoid the '-c' or '--command' flag as per instructions.
    const command = `ps ${flags}`;

    exec(command, (error, stdout, stderr) => {
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
                    // ps aux output usually starts with USER, PID, %CPU, %MEM, VSZ, RSS, TTY, STAT, START, TIME, COMMAND
                    // We split by whitespace to extract the PID (usually the second column)
                    const parts = line.split(/\s+/);
                    const pid = parseInt(parts[1], 10);

                    if (!isNaN(pid)) {
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