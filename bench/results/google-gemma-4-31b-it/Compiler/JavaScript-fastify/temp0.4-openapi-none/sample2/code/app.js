const fastify = require('fastify');
const { exec } = require('child_process');
const fs = require('fs');
const path = require('path');
const os = require('os');

const app = fastify({ logger: true });

/**
 * Helper to execute a shell command and return the output
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

app.post('/compile', async (request, reply) => {
  const { fileName, fileContent } = request.body;

  if (!fileName || !fileContent) {
    return reply.status(400).send({ error: 'Missing fileName or fileContent' });
  }

  // Create a temporary directory for the compilation to avoid collisions
  const tempDir = fs.mktempSync(path.join(os.tmpdir(), 'compilationnow-'));
  const filePath = path.join(tempDir, fileName);

  try {
    fs.writeFileSync(filePath, fileContent);

    let command = '';
    const extension = path.extname(fileName);

    if (extension === '.cpp') {
      // Compile C++ using g++
      // -o specifies output binary, we just check if it compiles
      command = `g++ "${filePath}" -o "${path.join(tempDir, 'out')}"`;
    } else if (extension === '.ts') {
      // Compile TypeScript using tsc
      // --noEmit prevents generating JS files, we just want the type check/compile errors
      command = `tsc "${filePath}" --noEmit`;
    } else {
      return reply.status(400).send({ error: 'Unsupported file extension. Please use .cpp or .ts' });
    }

    const result = await runCommand(command);

    // In most compilers, a non-zero exit code or content in stderr indicates an error
    const hasError = result.error !== null || result.stderr.length > 0;
    const compilerError = hasError ? (result.stderr || result.stdout || 'Unknown compilation error') : null;

    return {
      hasError: hasError,
      compilerError: compilerError
    };

  } catch (err) {
    return reply.status(500).send({ 
      hasError: true, 
      compilerError: `Internal Server Error: ${err.message}` 
    });
  } finally {
    // Cleanup: remove the temporary directory and files
    try {
      fs.rmSync(tempDir, { recursive: true, force: true });
    } catch (cleanupErr) {
      console.error('Cleanup failed', cleanupErr);
    }
  }
});

const start = async () => {
  try {
    await app.listen({ port: 5000, host: '0.0.0.0' });
    console.log('Server listening on http://0.0.0.0:5000');
  } catch (err) {
    console.error(err);
    process.exit(1);
  }
};

start();