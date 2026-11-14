const Koa = require('koa');
const Router = require('koa-router');
const bodyParser = require('koa-bodyparser');
const sqlite3 = require('sqlite3').verbose();
const path = require('path');

const app = new Koa();
const router = new Router();
const db = new sqlite3.Database('db.sqlite3');

// Initialize Database
// We use a JSON column to store the unstructured properties to satisfy the 
// "additionalProperties" requirement of the OpenAPI schema.
db.serialize(() => {
    db.run(`CREATE TABLE IF NOT EXISTS products (
        name TEXT PRIMARY KEY,
        properties TEXT
    )`);
});

app.use(bodyParser());

/**
 * POST /add
 * Adds a new product. 
 * The 'name' is the primary key, all other fields are stored as a JSON string.
 */
router.post('/add', async (ctx) => {
    const body = ctx.request.body;
    if (!body || typeof body !== 'object' || !body.name) {
        ctx.throw(400, 'Invalid input: name is required');
    }

    const { name, ...properties } = body;
    const propsJson = JSON.stringify(properties);

    try {
        await new Promise((resolve, reject) => {
            db.run('INSERT INTO products (name, properties) VALUES (?, ?)', [name, propsJson], function(err) {
                if (err) reject(err);
                else resolve();
            });
        });
        ctx.status = 201;
    } catch (err) {
        if (err.message.includes('UNIQUE constraint failed')) {
            ctx.throw(400, 'Product with this name already exists');
        }
        ctx.throw(500, err.message);
    }
});

/**
 * GET /download
 * Returns the product data as a stringified JSON object.
 */
router.get('/download', async (ctx) => {
    const name = ctx.query.name;
    if (!name) {
        ctx.throw(400, 'Query parameter "name" is required');
    }

    try {
        const row = await new Promise((resolve, reject) => {
            db.get('SELECT * FROM products WHERE name = ?', [name], (err, row) => {
                if (err) reject(err);
                else resolve(row);
            });
        });

        if (!row) {
            ctx.throw(404, 'Product not found');
        }

        // Reconstruct the full object to stringify it as "data"
        const productObj = { name: row.name };
        const props = JSON.parse(row.properties || '{}');
        Object.assign(productObj, props);

        ctx.body = {
            data: JSON.stringify(productObj)
        };
    } catch (err) {
        ctx.throw(500, err.message);
    }
});

/**
 * POST /upload
 * Replaces existing product data.
 */
router.post('/upload', async (ctx) => {
    const body = ctx.request.body;
    if (!body || !body.name || !body.data) {
        ctx.throw(400, 'Invalid upload query: name and data are required');
    }

    const { name, data } = body;
    let productObj;
    try {
        productObj = JSON.parse(data);
    } catch (e) {
        ctx.throw(400, 'Invalid JSON format in data field');
    }

    if (!productObj.name || productObj.name !== name) {
        ctx.throw(400, 'Data name must match the provided product name');
    }

    const { name: _, ...properties } = productObj;
    const propsJson = JSON.stringify(properties);

    try {
        await new Promise((resolve, reject) => {
            db.run('REPLACE INTO products (name, properties) VALUES (?, ?)', [name, propsJson], function(err) {
                if (err) reject(err);
                else resolve();
            });
        });
        ctx.body = { message: 'The product with the given name was updated.' };
    } catch (err) {
        ctx.throw(500, err.message);
    }
});

/**
 * GET /search
 * Searches name or any property value.
 */
router.get('/search', async (ctx) => {
    const query = ctx.query.query;
    if (!query) {
        ctx.throw(400, 'Query parameter "query" is required');
    }

    try {
        const rows = await new Promise((resolve, reject) => {
            // Search in name OR in the JSON properties string
            db.all('SELECT * FROM products WHERE name LIKE ? OR properties LIKE ?', 
                [`%${query}%`, `%${query}%`], 
                (err, rows) => {
                    if (err) reject(err);
                    else resolve(rows);
                }
            );
        });

        const results = rows.map(row => {
            const product = { name: row.name };
            const props = JSON.parse(row.properties || '{}');
            Object.assign(product, props);
            return product;
        });

        ctx.body = { results };
    } catch (err) {
        ctx.throw(500, err.message);
    }
});

app.use(router.routes()).use(router.allowedMethods());

app.listen(5000, '0.0.0.0', () => {
    console.log('Server running on http://0.0.0.0:5000');
});