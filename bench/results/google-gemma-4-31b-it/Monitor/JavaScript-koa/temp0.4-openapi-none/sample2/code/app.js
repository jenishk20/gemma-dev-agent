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
                // Extract PID. 
                // In 'ps aux', the PID is typically the second column.
                // We split by whitespace and attempt to find the first numeric value.
                const parts = line.split(/\s+/);
                
                // Depending on flags, the PID position changes. 
                // For 'aux', it's index 1.
                const pidMatch = line.match(/\d+/);
                const pid = pidMatch ? parseInt(pidMatch[0], 10) : null;

                results.push({
                    processId: pid,
                    processString: line
                });
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

const PORT = 5000;
const HOST = '0.0.0.0';

app.listen(PORT, HOST, () => {
    console.log(`Monitor Service running on http://${HOST}:${PORT}`);
});