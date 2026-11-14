const fastify = require('fastify')({ logger: true });
const fs = require('fs');
const path = require('path');

const DATA_ROOT = '/data';

fastify.post('/search', async (request, reply) => {
  const { search_content, search_filename, search_dir } = request.body;

  // Basic validation for request body
  if (!request.body || typeof request.body !== 'object') {
    return reply.status(400).send({ error: 'Invalid input' });
  }

  // Determine the base directory to search in
  // If search_dir is provided, resolve it relative to /data
  let baseDir = DATA_ROOT;
  if (search_dir) {
    baseDir = path.join(DATA_ROOT, search_dir);
  }

  // Safety check: Ensure the resolved path is still within /data to prevent directory traversal
  const relative = path.relative(DATA_ROOT, baseDir);
  if (relative.startsWith('..') || path.isAbsolute(relative)) {
    return reply.status(400).send({ error: 'Invalid search directory' });
  }

  if (!fs.existsSync(baseDir)) {
    return reply.status(200).send({ files: [] });
  }

  const matchedFiles = [];

  async function walk(currentDir) {
    const entries = fs.readdirSync(currentDir, { withFileTypes: true });

    for (const entry of entries) {
      const fullPath = path.join(currentDir, entry.name);

      if (entry.isDirectory()) {
        await walk(fullPath);
      } else if (entry.isFile()) {
        let isMatch = false;

        // 1. Match by filename (starts with)
        if (search_filename && entry.name.startsWith(search_filename)) {
          isMatch = true;
        }

        // 2. Match by content
        if (!isMatch && search_content) {
          try {
            const content = fs.readFileSync(fullPath, 'utf8');
            if (content.includes(search_content)) {
              isMatch = true;
            }
          } catch (err) {
            // Skip files that cannot be read as utf8 (e.g. binaries)
          }
        }

        // If either criteria is met, or if both were null (though schema implies search), 
        // we only add if at least one search parameter was provided and matched.
        if (isMatch) {
          matchedFiles.push(fullPath);
        }
      }
    }
  }

  try {
    await walk(baseDir);
    return reply.status(200).send({ files: matchedFiles });
  } catch (error) {
    return reply.status(400).send({ error: 'Error accessing directory' });
  }
});

const start = async () => {
  try {
    await fastify.listen({ port: 5000, host: '0.0.0.0' });
    console.log('Server listening on http://0.0.0.0:5000');
  } catch (err) {
    fastify.log.error(err);
    process.exit(1);
  }
};

start();