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
  // If search_dir is provided, append it to /data, otherwise use /data
  let baseDir = DATA_ROOT;
  if (search_dir) {
    baseDir = path.join(DATA_ROOT, search_dir);
  }

  // Security check: Ensure the resolved path is still within /data to prevent directory traversal
  if (!baseDir.startsWith(DATA_ROOT)) {
    return reply.status(400).send({ error: 'Invalid search directory' });
  }

  if (!fs.existsSync(baseDir)) {
    return reply.status(200).send({ files: [] });
  }

  const matchedFiles = [];

  async function walk(dir) {
    const entries = fs.readdirSync(dir, { withFileTypes: true });

    for (const entry of entries) {
      const fullPath = path.join(dir, entry.name);
      
      if (entry.isDirectory()) {
        await walk(fullPath);
      } else if (entry.isFile()) {
        let isMatch = false;

        // 1. Match by filename if provided
        if (search_filename && entry.name.includes(search_filename)) {
          isMatch = true;
        }

        // 2. Match by content if provided (and not already matched by filename)
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

        // If either search_content or search_filename was provided and matched, or if both were null (which we treat as no match)
        if (isMatch) {
          matchedFiles.push(fullPath);
        }
      }
    }
  }

  try {
    await walk(baseDir);
    return { files: matchedFiles };
  } catch (error) {
    return reply.status(400).send({ error: 'Error searching files' });
  }
});

const start = async () => {
  try {
    await fastify.listen({ address: '0.0.0.0', port: 5000 });
    console.log('Server listening on 0.0.0.0:5000');
  } catch (err) {
    fastify.log.error(err);
    process.exit(1);
  }
};

start();