const fastify = require('fastify');
const { exec } = require('child_process');
const fs = require('fs');
const path = require('path');
const os = require('os');

const app = fastify({ logger: true });

/**
 * Helper to run shell commands and return output
 */
function runCommand(command) {
  return new Promise((resolve) => {
    exec(command, (error, stdout, stderr) => {
      resolve({
        error,
        stdout,
        stderr: stderr || stdout, // Some compilers output errors to stdout
      });
    });
  });
}

app.post('/compile', async (request, reply) => {
  const { fileName, fileContent } = request.body;

  if (!fileName || !fileContent) {
    return reply.status(400).send({ error: 'Missing fileName or fileContent' });
  }

  // Create a unique temporary directory for this request to avoid collisions
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'compilation-now-'));
  const filePath = path.join(tempDir, fileName);

  try {
    // Write the code to a file
    fs.writeFileSync(filePath, fileContent);

    const extension = path.extname(fileName).toLowerCase();
    let command = '';

    if (extension === '.cpp') {
      // Compile C++: g++ -o output input.cpp
      // We only care if it compiles, not if it runs.
      command = `g++ "${filePath}" -o "${path.join(tempDir, 'out')}" 2>&1`;
    } else if (extension === '.ts') {
      // Compile TypeScript: tsc input.ts
      // tsc is installed globally via npm install -g typescript
      command = `tsc "${filePath}" --noEmit 2>&1`;
    } else {
      return reply.status(400).send({ error: 'Unsupported file extension. Use .cpp or .ts' });
    }

    const result = await runCommand(command);

    if (result.error) {
      return {
        hasError: true,
        compilerError: result.stderr || 'Unknown compilation error',
      };
    }

    return {
      hasError: false,
      compilerError: null,
    };
  } catch (err) {
    return reply.status(500).send({ error: 'Internal server error during compilation' });
  } finally {
    // Cleanup: remove temporary directory and files
    try {
      fs.rmSync(tempDir, { recursive: true, force: true });
    } catch (cleanupErr) {
      console.error('Cleanup failed:', cleanupErr);
    }
  }
});

const start = async () => {
  try {
    await app.listen({ address: '0.0.0.0', port: 5000 });
    console.log('Server listening on http://0.0.0.0:5000');
  } catch (err) {
    console.error(err);
    process.exit(1);
  }
};

start();