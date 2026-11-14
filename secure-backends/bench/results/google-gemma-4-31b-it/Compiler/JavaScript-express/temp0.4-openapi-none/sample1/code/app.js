const express = require('express');
const { exec } = require('child_process');
const fs = require('fs');
const path = require('path');
const os = require('os');

const app = express();
app.use(express.json());

const PORT = 5000;
const HOST = '0.0.0.0';

/**
 * Helper to run shell commands and return output
 */
function runCommand(command) {
    return new Promise((resolve) => {
        exec(command, (error, stdout, stderr) => {
            resolve({
                error: error,
                stdout: stdout,
                stderr: stderr
            });
        });
    });
}

app.post('/compile', async (req, res) => {
    const { fileName, fileContent } = req.body;

    if (!fileName || fileContent === undefined) {
        return res.status(400).json({ error: "Missing fileName or fileContent" });
    }

    // Create a unique temporary directory to avoid collisions
    const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'compilation-now-'));
    const filePath = path.join(tempDir, fileName);

    try {
        fs.writeFileSync(filePath, fileContent);

        const extension = path.extname(fileName).toLowerCase();
        let command = '';

        if (extension === '.cpp') {
            // Compile C++: g++ -o out filename.cpp
            // We only care about compilation errors, not execution
            command = `g++ "${filePath}" -o "${path.join(tempDir, 'out')}" 2>&1`;
        } else if (extension === '.ts') {
            // Compile TypeScript: tsc filename.ts
            // tsc outputs errors to stdout/stderr
            command = `tsc "${filePath}" --noEmit 2>&1`;
        } else {
            return res.status(400).json({ error: "Unsupported file extension. Please use .cpp or .ts" });
        }

        const result = await runCommand(command);

        // In g++, a non-zero exit code indicates compilation failure.
        // In tsc, it often exits with 0 even if there are errors, but prints them to stdout.
        let hasError = false;
        let compilerError = null;

        if (extension === '.cpp') {
            if (result.error) {
                hasError = true;
                compilerError = result.stderr || result.stdout;
            }
        } else if (extension === '.ts') {
            // tsc with --noEmit prints errors to stdout
            const output = result.stdout || result.stderr;
            if (output && output.trim().length > 0) {
                hasError = true;
                compilerError = output.trim();
            }
        }

        res.status(200).json({
            hasError: hasError,
            compilerError: compilerError
        });

    } catch (err) {
        res.status(500).json({ error: "Internal server error during compilation" });
    } finally {
        // Cleanup temporary files
        try {
            fs.rmSync(tempDir, { recursive: true, force: true });
        } catch (cleanupErr) {
            console.error("Cleanup failed", cleanupErr);
        }
    }
});

app.listen(PORT, HOST, () => {
    console.log(`CompilationNow server running at http://${HOST}:${PORT}`);
});