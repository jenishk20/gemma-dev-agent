const Koa = require('koa');
const Router = require('koa-router');
const bodyParser = require('koa-bodyparser');
const { exec } = require('child_process');
const { promisify } = require('util');

const execPromise = promisify(exec);
const app = new Koa();
const router = new Router();

app.use(bodyParser());

/**
 * Implementation of the /monitor/commands endpoint
 * It executes the 'ps' command with provided flags, 
 * then filters the output using the provided regex.
 */
router.post('/monitor/commands', async (ctx) => {
    const { filter_flags, command_regex } = ctx.request.body;

    if (!command_regex) {
        ctx.status = 400;
        ctx.body = {
            code: 400,
            message: "Missing required field: command_regex"
        };
        return;
    }

    try {
        // Construct the ps command. 
        // Default flags to 'aux' if none provided to ensure we get process strings.
        const flags = filter_flags || 'aux';
        const command = `ps ${flags}`;
        
        const { stdout } = await execPromise(command);
        
        // Split output into lines
        const lines = stdout.split('\n');
        const regex = new RegExp(command_regex);
        const results = [];

        // Skip header line (usually the first line of ps output)
        for (let i = 1; i < lines.length; i++) {
            const line = lines[i].trim();
            if (!line) continue;

            if (regex.test(line)) {
                // ps aux output format: USER PID %CPU %MEM VSZ RSS TTY STAT START TIME COMMAND
                // We split by whitespace and take the second element as PID
                const parts = line.split(/\s+/);
                if (parts.length >= 2) {
                    const pid = parseInt(parts[1], 10);
                    if (!isNaN(pid)) {
                        results.push({
                            processId: pid,
                            processString: line
                        });
                    }
                }
            }
        }

        ctx.status = 200;
        ctx.body = results;
    } catch (error) {
        ctx.status = 500;
        ctx.body = {
            code: 500,
            message: `Internal Server Error: ${error.message}`
        };
    }
});

app.use(router.routes()).use(router.allowedMethods());

app.listen(5000, '0.0.0.0', () => {
    console.log('Monitor Service running on http://0.0.0.0:5000');
});