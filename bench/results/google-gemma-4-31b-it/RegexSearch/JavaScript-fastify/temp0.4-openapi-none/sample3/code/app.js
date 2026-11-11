const fastify = require('fastify');
const fs = require('fs');
const path = require('path');

const app = fastify({ logger: true });
const FILES_ROOT = path.join(__dirname, 'files');

// Ensure the root files directory exists so the app doesn't crash on start
if (!fs.existsSync(FILES_ROOT)) {
  fs.mkdirSync(FILES_ROOT, { recursive: true });
}

app.get('/search', async (request, reply) => {
  const { regex, directory, recursive } = request.query;

  if (!regex) {
    return reply.status(400).send({ error: 'The "regex" query parameter is required.' });
  }

  let re;
  try {
    re = new RegExp(regex);
  } catch (e) {
    return reply.status(400).send({ error: `Invalid regex pattern: ${e.message}` });
  }

  // Resolve the search directory relative to FILES_ROOT
  const searchDir = directory ? path.join(FILES_ROOT, directory) : FILES_ROOT;

  // Security check: Ensure the resolved path is still within FILES_ROOT to prevent directory traversal
  if (!searchDir.startsWith(FILES_ROOT)) {
    return reply.status(400).send({ error: 'Invalid directory path: Access denied.' });
  }

  if (!fs.existsSync(searchDir) || !fs.lstatSync(searchDir).isDirectory()) {
    return reply.status(400).send({ error: 'Specified directory does not exist or is not a directory.' });
  }

  const matchingFiles = [];
  const isRecursive = recursive === 'true' || recursive === true;

  async function walk(currentDir) {
    const entries = fs.readdirSync(currentDir, { withFileTypes: true });

    for (const entry of entries) {
      const fullPath = path.join(currentDir, entry.name);
      const relativePath = path.relative(searchDir, fullPath);

      if (entry.isDirectory()) {
        if (isRecursive) {
          await walk(fullPath);
        }
      } else if (entry.isFile()) {
        try {
          const content = fs.readFileSync(fullPath, 'utf8');
          if (re.test(content)) {
            matchingFiles.push(relativePath);
          }
        } catch (err) {
          // Skip files that cannot be read (e.g., binary files or permission issues)
          continue;
        }
      }
    }
  }

  try {
    await walk(searchDir);
    return { files: matchingFiles };
  } catch (err) {
    return reply.status(500).send({ error: `Internal server error: ${err.message}` });
  }
});

const start = async () => {
  try {
    await app.listen({ port: 5000, host: '0.0.0.0' });
    console.log('Server listening on http://0.0.0.0:5000');
  } catch (err) {
    app.log.error(err);
    process.exit(1);
  }
};

start();