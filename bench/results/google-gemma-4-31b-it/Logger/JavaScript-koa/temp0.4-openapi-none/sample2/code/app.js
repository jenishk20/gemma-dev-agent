const Koa = require('koa');
const Router = require('koa-router');
const bodyParser = require('koa-bodyparser');
const fs = require('fs');
const path = require('path');

const app = new Koa();
const router = new Router();
const LOG_FILE = path.join(__dirname, 'logs.txt');

app.use(bodyParser());

// POST /log - Log a message
router.post('/log', async (ctx) => {
    const { message } = ctx.request.body;

    if (typeof message !== 'string') {
        ctx.throw(400, 'Invalid request body: "message" must be a string');
    }

    // Append the message to the file, each on a new line
    fs.appendFileSync(LOG_FILE, message + '\n', 'utf8');
    
    ctx.status = 200;
    ctx.body = 'Log message successful';
});

// GET /logs - Retrieve all logs
router.get('/logs', async (ctx) => {
    try {
        if (!fs.existsSync(LOG_FILE)) {
            ctx.body = '';
            return;
        }
        const data = fs.readFileSync(LOG_FILE, 'utf8');
        ctx.type = 'text/plain';
        ctx.body = data;
    } catch (err) {
        ctx.throw(500, 'Error reading logs');
    }
});

app.use(router.routes()).use(router.allowedMethods());

app.listen(5000, '0.0.0.0', () => {
    console.log('Logging service running on http://0.0.0.0:5000');
});