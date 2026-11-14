const fastify = require('fastify')({ logger: true });
const { exec } = require('child_process');
const { promisify } = require('util');

const execPromise = promisify(exec);

/**
 * Implementation of the Monitor Service
 * Based on the provided OpenAPI schema.
 */

fastify.post('/monitor/commands', {
  schema: {
    body: {
      type: 'object',
      required: ['command_regex'],
      properties: {
        filter_flags: { type: 'string' },
        command_regex: { type: 'string' }
      }
    },
    response: {
      200: {
        type: 'array',
        items: {
          type: 'object',
          properties: {
            processId: { type: 'integer' },
            processString: { type: 'string' }
          }
        }
      }
    }
  }
}, async (request, reply) => {
  const { filter_flags, command_regex } = request.body;

  try {
    // Sanitize filter_flags to prevent command injection. 
    // Only allow alphanumeric characters, spaces, and dashes.
    const sanitizedFlags = filter_flags ? filter_flags.replace(/[^a-zA-Z0-9\s-]/g, '') : 'aux';
    
    // Execute the ps command. 
    // Note: "command" parameter is not supported as per instructions, so we use flags.
    const { stdout } = await execPromise(`ps ${sanitizedFlags}`);
    
    // Create a regular expression from the provided command_regex
    const regex = new RegExp(command_regex);
    
    const lines = stdout.split('\n');
    const results = [];

    // The first line of ps aux is usually the header
    for (let i = 1; i < lines.length; i++) {
      const line = lines[i].trim();
      if (!line) continue;

      if (regex.test(line)) {
        // ps aux output format: USER PID %CPU %MEM VSZ RSS TTY STAT START TIME COMMAND
        // We split by whitespace and take the second element as PID
        const parts = line.split(/\s+/);
        const pid = parseInt(parts[1], 10);

        if (!isNaN(pid)) {
          results.push({
            processId: pid,
            processString: line
          });
        }
      }
    }

    return results;
  } catch (error) {
    fastify.log.error(error);
    return reply.status(500).send({
      code: 500,
      message: 'Internal Server Error while retrieving processes'
    });
  }
});

// Start the server
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