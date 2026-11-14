const fastify = require('fastify')({ logger: true });
const { exec } = require('child_process');
const util = require('util');
const execPromise = util.promisify(exec);

/**
 * Implementation of the Monitor Service
 * This service uses the 'ps' command to list processes and filters them
 * based on a regular expression provided in the request body.
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
    }
  }
}, async (request, reply) => {
  const { filter_flags, command_regex } = request.body;

  try {
    // Validate the regex to prevent server crashes on invalid input
    new RegExp(command_regex);

    // Construct the ps command. 
    // We use 'aux' as a default if no flags are provided.
    // Note: The prompt mentions 'command' parameter is not supported, 
    // so we rely on standard flags and pipe to grep/filter in JS.
    const flags = filter_flags || 'aux';
    const { stdout } = await execPromise(`ps ${flags}`);

    const lines = stdout.split('\n');
    const regex = new RegExp(command_regex);
    const results = [];

    // The first line of 'ps aux' is usually the header
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
    if (error instanceof SyntaxError) {
      return reply.status(400).send({
        code: 400,
        message: 'Invalid regular expression provided.'
      });
    }
    
    return reply.status(500).send({
      code: 500,
      message: `Internal Server Error: ${error.message}`
    });
  }
});

// Start the server
const start = async () => {
  try {
    await fastify.listen({ address: '0.0.0.0', port: 5000 });
    console.log('Server is running on http://0.0.0.0:5000');
  } catch (err) {
    fastify.log.error(err);
    process.exit(1);
  }
};

start();