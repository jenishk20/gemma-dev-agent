const Koa = require('koa');
const Router = require('koa-router');
const bodyParser = require('koa-bodyparser');
const { exec } = require('child_process');
const { promisify } = require('util');

const execPromise = promisify(exec);
const app = new Koa();
const router = new Router();

app.use(bodyParser());

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
        // Use 'ps' command. Default flags if none provided.
        // We use 'aux' as a common default for process listing.
        const flags = filter_flags || 'aux';
        const command = `ps ${flags}`;
        
        const { stdout, stderr } = await execPromise(command);

        if (stderr) {
            throw new Error(stderr);
        }

        const regex = new RegExp(command_regex);
        const lines = stdout.split('\n');
        const results = [];

        // Skip the header line of ps output
        for (let i = 1; i < lines.length; i++) {
            const line = lines[i].trim();
            if (!line) continue;

            if (regex.test(line)) {
                // Extract PID. In 'ps aux', PID is typically the second column.
                // We split by whitespace and take the second element.
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
    console.log('Server running on http://0.0.0.0:5000');
});