const fastify = require('fastify')({ logger: true });
const { exec } = require('child_process');
const { promisify } = require('util');

const execPromise = promisify(exec);

/**
 * Implementation of the Monitor Service
 * 
 * The service uses the 'ps' command to list processes.
 * Since the 'command' parameter is not supported on the target OS, 
 * we use the provided filter_flags (e.g., 'aux') and then filter the 
 * output using the provided regular expression in JavaScript.
 */

fastify.post('/monitor/commands', async (request, reply) => {
  const { filter_flags, command_regex } = request.body;

  if (!command_regex) {
    return reply.status(400).send({
      code: 400,
      message: "Missing required field: command_regex"
    });
  }

  try {
    // Default flags if none provided
    const flags = filter_flags || 'aux';
    
    // Execute ps command. We use 'ps' with the provided flags.
    // We wrap the command to ensure we get the process list.
    const { stdout } = await execPromise(`ps ${flags}`);
    
    const lines = stdout.split('\n');
    const regex = new RegExp(command_regex);
    const results = [];

    // ps output usually has a header line, so we iterate through all lines
    for (const line of lines) {
      if (!line.trim()) continue;

      // Match the line against the regex
      if (regex.test(line)) {
        // Extract PID. In 'ps aux' or similar, PID is usually the second column.
        // We split by whitespace and attempt to find the first integer that looks like a PID.
        const parts = line.trim().split(/\s+/);
        
        // Basic heuristic: find the first part that is purely numeric
        let pid = null;
        let pidIndex = -1;
        
        for (let i = 0; i < parts.length; i++) {
          if (/^\d+$/.test(parts[i])) {
            pid = parseInt(parts[i], 10);
            pidIndex = i;
            break;
          }
        }

        if (pid !== null) {
          results.push({
            processId: pid,
            processString: line.trim()
          });
        }
      }
    }

    return reply.status(200).send(results);
  } catch (error) {
    fastify.log.error(error);
    return reply.status(500).send({
      code: 500,
      message: `Internal Server Error: ${error.message}`
    });
  }
});

// Start the server
const start = async () => {
  try {
    await fastify.listen({ port: 5000, host: '0.0.0.0' });
    console.log('Server is running on http://0.0.0.0:5000');
  } catch (err) {
    fastify.log.error(err);
    process.exit(1);
  }
};

start();