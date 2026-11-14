const fastify = require('fastify')({ logger: true });
const fs = require('fs').promises;
const path = require('path');

const ROOT_FILES_DIR = path.join(__dirname, 'files');

// Ensure the root files directory exists for the app to be runnable
async function ensureRootDirectory() {
  try {
    await fs.mkdir(ROOT_FILES_DIR, { recursive: true });
  } catch (err) {
    console.error('Could not create root files directory', err);
  }
}

async function getFiles(dir, recursive) {
  let results = [];
  const list = await fs.readdir(dir, { withFileTypes: true });

  for (const entry of list) {
    const res = path.resolve(dir, entry.name);
    if (entry.isDirectory()) {
      if (recursive) {
        results = results.concat(await getFiles(res, recursive));
      }
    } else {
      results.push(res);
    }
  }
  return results;
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

  // Resolve the search directory relative to the root files directory
  const searchDir = directory 
    ? path.join(ROOT_FILES_DIR, directory) 
    : ROOT_FILES_DIR;

  // Security check: Ensure the resolved path is still within the ROOT_FILES_DIR to prevent directory traversal
  if (!searchDir.startsWith(ROOT_FILES_DIR)) {
    return reply.status(400).send({ error: 'Invalid directory path provided.' });
  }

  try {
    const isRecursive = recursive === 'true' || recursive === true;
    const allFiles = await getFiles(searchDir, isRecursive);
    const matchedFiles = [];

    for (const filePath of allFiles) {
      try {
        const content = await fs.readFile(filePath, 'utf8');
        if (re.test(content)) {
          // Calculate path relative to the searchDir as per OpenAPI spec
          const relativePath = path.relative(searchDir, filePath);
          matchedFiles.push(relativePath);
        }
      } catch (readErr) {
        // Skip files that cannot be read (e.g. binary files or permission issues)
        continue;
      }
    }

    return { files: matchedFiles };
  } catch (err) {
    if (err.code === 'ENOENT') {
      return reply.status(400).send({ error: 'Specified directory not found.' });
    }
    return reply.status(500).send({ error: `Internal server error: ${err.message}` });
  }
});

const start = async () => {
  await ensureRootDirectory();
  try {
    await fastify.listen({ port: 5000, host: '0.0.0.0' });
  } catch (err) {
    fastify.log.error(err);
    process.exit(1);
  }
};

start();