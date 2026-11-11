const express = require('express');
const { exec } = require('child_process');
const util = require('util');

const execPromise = util.promisify(exec);
const app = express();
const port = 5000;

app.use(express.json());

/**
 * POST /monitor/commands
 * Returns a list of processes matching a regex based on the output of the 'ps' command.
 */
app.post('/monitor/commands', async (req, res) => {
    const { filter_flags, command_regex } = req.body;

    if (!command_regex) {
        return res.status(400).json({
            code: 400,
            message: "Missing required field: command_regex"
        });
    }

    try {
        // Construct the ps command. 
        // We use 'ps' with provided flags. Default to 'aux' if none provided.
        // Note: We must be careful about shell injection. 
        // Since this is a system monitor tool, we sanitize the flags to allow only common ps characters.
        const sanitizedFlags = filter_flags ? filter_flags.replace(/[^a-zA-Z0-9\s\-\.]/g, '') : 'aux';
        const command = `ps ${sanitizedFlags}`;

        const { stdout, stderr } = await execPromise(command);

        if (stderr) {
            throw new Error(stderr);
        }

        const regex = new RegExp(command_regex);
        const lines = stdout.split('\n');
        const results = [];

        // The first line of 'ps aux' is usually the header.
        for (let i = 1; i < lines.length; i++) {
            const line = lines[i].trim();
            if (!line) continue;

            if (regex.test(line)) {
                // ps aux output format: USER PID %CPU %MEM VSZ RSS TTY STAT START TIME COMMAND
                // We split by whitespace and take the second element as PID
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
    } catch (error) {
        res.status(500).json({
            code: 500,
            message: `Internal Server Error: ${error.message}`
        });
    }
});

app.listen(port, '0.0.0.0', () => {
    console.log(`Monitor Service listening at http://0.0.0.0:${port}`);
});