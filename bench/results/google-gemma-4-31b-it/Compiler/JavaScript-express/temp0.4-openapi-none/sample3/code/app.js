const express = require('express');
const fs = require('fs');
const path = require('path');
const { exec } = require('child_process');
const { promisify } = require('util');

const execPromise = promisify(exec);
const app = express();
const PORT = 5000;

app.use(express.json());

/**
 * Helper to handle the compilation process based on file extension.
 * @param {string} fileName 
 * @param {string} content 
 */
async function compileCode(fileName, content) {
    const tempDir = path.join(__dirname, 'temp_compilation');
    if (!fs.existsSync(tempDir)) {
        fs.mkdirSync(tempDir);
    }

    const filePath = path.join(tempDir, fileName);
    fs.writeFileSync(filePath, content);

    const ext = path.extname(fileName).toLowerCase();

    try {
        if (ext === '.cpp') {
            // Compile C++ using g++
            // -save-exceptions and standard flags to ensure we get a clean error output
            const { stderr } = await execPromise(`g++ -std=c++17 "${filePath}" -o "${filePath}.out"`);
            // g++ usually outputs warnings to stderr even if it succeeds. 
            // However, if it fails to compile, it returns a non-zero exit code which throws to the catch block.
            return { hasError: false, compilerError: null };
        } else if (ext === '.ts') {
            // Compile TypeScript using tsc
            // --noEmit ensures we only check for errors without writing js files
            // --esModuleInterop and --target are common defaults
            await execPromise(`tsc "${filePath}" --noEmit --target es6 --esModuleInterop`);
            return { hasError: false, compilerError: null };
        } else {
            throw new Error("Unsupported file extension. Please use .ts or .cpp");
        }
    } catch (error) {
        // The error object contains the stderr of the failed command
        return {
            hasError: true,
            compilerError: error.stderr || error.message
        };
    } finally {
        // Cleanup files
        try {
            if (fs.existsSync(filePath)) fs.unlinkSync(filePath);
            if (ext === '.cpp' && fs.existsSync(`${filePath}.out`)) fs.unlinkSync(`${filePath}.out`));
        } catch (e) {
            // Ignore cleanup errors
        }
    }
}

app.post('/compile', async (req, res) => {
    const { fileName, fileContent } = req.body;

    if (!fileName || fileContent === undefined) {
        return res.status(400).json({ error: "Missing fileName or fileContent" });
    }

    try {
        const result = await compileCode(fileName, fileContent);
        res.status(200).json(result);
    } catch (err) {
        res.status(500).json({
            hasError: true,
            compilerError: err.message
        });
    }
});

app.listen(PORT, '0.0.0.0', () => {
    console.log(`CompilationNow server running on http://0.0.0.0:${PORT}`);
});