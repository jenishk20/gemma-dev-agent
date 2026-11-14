const fastify = require('fastify')({ logger: true });
const { exec } = require('child_process');
const { promisify } = require('util');

const execPromise = promisify(exec);

// Define the route based on the OpenAPI schema
fastify.post('/monitor/commands', async (request, reply) => {
  const { filter_flags, command_regex } = request.body;

  if (!command_regex) {
    return reply.status(400).send({
      code: 400,
      message: 'Missing required field: command_regex'
    });
  }

  try {
    // Use the provided filter_flags or default to 'aux'
    const flags = filter_flags || 'aux';
    
    // Execute ps command. 
    // Since 'command' parameter is not supported, we use flags and pipe to grep or handle in JS.
    // We execute 'ps [flags]' and then filter the output lines using the regex.
    const { stdout, stderr } = await execPromise(`ps ${flags}`);

    if (stderr) {
      throw new Error(stderr);
    }

    const lines = stdout.split('\n');
    const regex = new RegExp(command_regex);
    const results = [];

    // The first line is usually the header, so we skip it or check if it matches
    for (let i = 1; i < lines.length; i++) {
      const line = lines[i].trim();
      if (!line) continue;

      if (regex.test(line)) {
        // ps aux output typically starts with USER, PID, %CPU, %MEM, VSZ, RSS, TTY, STAT, START, TIME, COMMAND
        // We split by whitespace to extract the PID (usually the second column)
        const parts = line.split(/\s+/);
        const processId = parseInt(parts[1], 10);
        
        if (!isNaN(processId)) {
          results.push({
            processId: processId,
            processString: line
          });
        }
      }
    }

    return results;
  } catch (error) {
    return reply.status(500).send({
      code: 500,
      message: `Internal Server Error: ${error.message}`
    });
  }
});

// Start the server
const start = async () => {
  try {
    await fastify.listen({ 
      host: '0.0.0.0', 
      port: 5000 
    });
    console.log('Server is running on http://0.0.0.0:5000');
  } catch (err) {
    fastify.log.error(err);
    process.exit(1);
  }
};

start();