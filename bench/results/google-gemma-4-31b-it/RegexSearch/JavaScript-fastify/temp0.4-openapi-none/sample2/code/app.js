const fastify = require('fastify')({ logger: false });
const fs = require('fs');
const path = require('path');

const ROOT_DIR = path.join(__dirname, 'files');

// Ensure the root files directory exists for the app to function
if (!fs.existsSync(ROOT_DIR)) {
  fs.mkdirSync(ROOT_DIR, { recursive: true });
}

fastify.get('/search', async (request, reply) => {
  const { regex, directory, recursive } = request.query;

  if (!regex) {
    return reply.status(400).send({ error: 'The "regex" query parameter is required.' });
  }

  let re;
  try {
    re = new RegExp(regex);
  } catch (e) {
    return reply.status(400).send({ error: `Invalid regular expression: ${e.message}` });
  }

  // Resolve the base search path
  const searchBase = directory ? path.join(ROOT_DIR, directory) : ROOT_DIR;

  // Security check: Ensure the search path is within the ROOT_DIR to prevent directory traversal
  if (!searchBase.startsWith(ROOT_DIR)) {
    return reply.status(400).send({ error: 'Invalid directory path: access denied.' });
  }

  if (!fs.existsSync(searchBase)) {
    return reply.status(400).send({ error: 'Specified directory does not exist.' });
  }

  const matchingFiles = [];

  async function walk(currentDir) {
    let entries;
    try {
      entries = fs.readdirSync(currentDir, { withFileTypes: true });
    } catch (e) {
      throw new Error(`Unable to read directory ${currentDir}: ${e.message}`);
    }

    for (const entry of entries) {
      const fullPath = path.join(currentDir, entry.name);
      
      if (entry.isDirectory()) {
        if (recursive === 'true' || recursive === true) {
          await walk(fullPath);
        }
      } else if (entry.isFile()) {
        try {
          const content = fs.readFileSync(fullPath, 'utf8');
          if (re.test(content)) {
            // Calculate path relative to the requested directory or ROOT_DIR
            const relativePath = path.relative(searchBase, fullPath);
            matchingFiles.push(relativePath);
          }
        } catch (e) {
          // Skip files that cannot be read as utf8 (e.g. binary files)
        }
      }
    }
  }

  try {
    await walk(searchBase);
    return { files: matchingFiles };
  } catch (e) {
    return reply.status(500).send({ error: e.message });
  }
});

const start = async () => {
  try {
    await fastify.listen({ address: '0.0.0.0', port: 5000 });
    console.log('Server is running on http://0.0.0.0:5000');
  } catch (err) {
    console.error(err);
    process.exit(1);
  }
};

start();