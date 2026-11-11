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
        // Use provided flags or default to 'aux'
        const flags = filter_flags || 'aux';
        
        // Execute ps command. 
        // We use 'ps' and filter the output in JS to avoid shell injection 
        // and because the prompt mentions 'command' parameter is not supported.
        const { stdout } = await execPromise(`ps ${flags}`);
        
        const lines = stdout.split('\n');
        const regex = new RegExp(command_regex);
        const results = [];

        // Skip header line (usually the first line)
        for (let i = 1; i < lines.length; i++) {
            const line = lines[i].trim();
            if (!line) continue;

            if (regex.test(line)) {
                // ps aux output typically starts with USER, PID, %CPU, %MEM, VSZ, RSS, TTY, STAT, START, TIME, COMMAND
                // We split by whitespace to extract the PID (usually the 2nd column)
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
    console.log('Monitor Service running on http://0.0.0.0:5000');
});