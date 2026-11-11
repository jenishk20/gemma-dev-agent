const fastify = require('fastify')({ logger: true });
const fs = require('fs');
const path = require('path');

const DATA_ROOT = '/data';

/**
 * Recursively searches for files based on the provided criteria.
 * @param {string} dir Current directory to search
 * @param {string|null} content Content to look for inside files
 * @param {string|null} filename Filename to match (starts with)
 * @param {string[]} results Array to accumulate matching file paths
 */
function searchFilesRecursive(dir, content, filename, results) {
    let files;
    try {
        files = fs.readdirSync(dir);
    } catch (err) {
        // Handle cases where directory might not exist or be accessible
        return;
    }

    for (const file of files) {
        const fullPath = path.join(dir, file);
        let stats;
        try {
            stats = fs.statSync(fullPath);
        } catch (err) {
            continue;
        }

        if (stats.isDirectory()) {
            searchFilesRecursive(fullPath, content, filename, results);
        } else if (stats.isFile()) {
            let match = false;

            // 1. Match by filename (starts with)
            if (filename && file.startsWith(filename)) {
                match = true;
            }

            // 2. Match by content
            if (!match && content) {
                try {
                    const fileContent = fs.readFileSync(fullPath, 'utf8');
                    if (fileContent.includes(content)) {
                        match = true;
                    }
                } catch (err) {
                    // Skip files that cannot be read as utf8
                }
            }

            // If both are null, the schema implies we don't match everything, 
            // but usually, if at least one criteria is provided and matches, we add it.
            if (match) {
                results.push(fullPath);
            }
        }
    }
}

fastify.post('/search', async (request, reply) => {
    const { search_content, search_filename, search_dir } = request.body;

    // Basic validation: if both search terms are null/undefined, it's an invalid request based on logic
    if (search_content === null && search_filename === null && 
        search_content === undefined && search_filename === undefined) {
        return reply.status(400).send({ error: 'Invalid input: provide search_content or search_filename' });
    }

    // Resolve the starting directory
    // If search_dir is provided, join it with DATA_ROOT. 
    // We use path.resolve and check if it starts with DATA_ROOT to prevent directory traversal attacks.
    let targetDir = DATA_ROOT;
    if (search_dir) {
        targetDir = path.join(DATA_ROOT, search_dir);
        if (!targetDir.startsWith(DATA_ROOT)) {
            return reply.status(400).send({ error: 'Invalid search_dir: path must be within /data' });
        }
    }

    const matchedFiles = [];
    searchFilesRecursive(targetDir, search_content, search_filename, matchedFiles);

    return { files: matchedFiles };
});

const start = async () => {
    try {
        await fastify.listen({ host: '0.0.0.0', port: 5000 });
    } catch (err) {
        fastify.log.error(err);
        process.exit(1);
    }
};

start();