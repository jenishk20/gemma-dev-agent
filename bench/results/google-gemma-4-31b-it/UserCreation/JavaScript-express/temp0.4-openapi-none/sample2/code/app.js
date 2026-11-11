const express = require('express');
const sqlite3 = require('sqlite3').verbose();
const bcrypt = require('bcrypt');
const { v4: uuidv4 } = require('uuid');
require('dotenv').config();

const app = express();
app.use(express.json());

const PORT = 5000;
const HOST = '0.0.0.0';
const APP_SECRET = process.env.APP_SECRET || 'default_secret_key';

// Database initialization
const db = new sqlite3.Database('db.sqlite3');

db.serialize(() => {
    // Table for invitations
    db.run(`CREATE TABLE IF NOT EXISTS invitations (
        invite_id TEXT PRIMARY KEY,
        email TEXT UNIQUE NOT NULL,
        used INTEGER DEFAULT 0
    )`);

    // Table for users
    db.run(`CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_name TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    )`);
});

/**
 * POST /invite_user
 * Creates an invitation for a specific email.
 */
app.post('/invite_user', (req, res) => {
    const { email } = req.body;

    if (!email) {
        return res.status(400).json({ message: "Email is required" });
    }

    // Check if invitation already exists for this email
    db.get('SELECT invite_id FROM invitations WHERE email = ?', [email], (err, row) => {
        if (err) {
            return res.status(500).json({ message: "Database error" });
        }

        if (row) {
            return res.status(200).json({
                invite_id: row.invite_id,
                message: "Invitation already exists for this email."
            });
        }

        // Create new invitation
        const invite_id = uuidv4();
        db.run('INSERT INTO invitations (invite_id, email) VALUES (?, ?)', [invite_id, email], function(err) {
            if (err) {
                return res.status(500).json({ message: "Database error" });
            }
            res.status(200).json({
                invite_id: invite_id,
                message: "Invitation created successfully."
            });
        });
    });
});

/**
 * POST /create_user
 * Creates a user account using a valid invitation ID.
 */
app.post('/create_user', async (req, res) => {
    const { invite_id, user_name, password } = req.body;

    if (!invite_id || !user_name || !password) {
        return res.status(400).json({ message: "Missing required fields: invite_id, user_name, or password" });
    }

    // 1. Validate invitation
    db.get('SELECT email FROM invitations WHERE invite_id = ? AND used = 0', [invite_id], async (err, invite) => {
        if (err) {
            return res.status(500).json({ message: "Database error" });
        }

        if (!invite) {
            return res.status(401).json({ message: "Invalid invite_id" });
        }

        const userEmail = invite.email;

        // 2. Check if username already exists
        db.get('SELECT id FROM users WHERE user_name = ?', [user_name], async (err, userExists) => {
            if (err) {
                return res.status(500).json({ message: "Database error" });
            }

            if (userExists) {
                return res.status(400).json({ message: "Username already exists. Try providing different username." });
            }

            try {
                // 3. Hash password and create user
                const hashedPassword = await bcrypt.hash(password, 10);
                
                db.run('BEGIN TRANSACTION');
                
                db.run('INSERT INTO users (user_name, email, password) VALUES (?, ?, ?)', 
                    [user_name, userEmail, hashedPassword], 
                    (err) => {
                        if (err) {
                            db.run('ROLLBACK');
                            return res.status(400).json({ message: "User creation failed." });
                        }

                        // 4. Mark invitation as used
                        db.run('UPDATE invitations SET used = 1 WHERE invite_id = ?', [invite_id], (err) => {
                            if (err) {
                                db.run('ROLLBACK');
                                return res.status(500).json({ message: "Database error updating invitation" });
                            }
                            db.run('COMMIT');
                            res.status(200).json({ message: "User created successfully" });
                        });
                    }
                );
            } catch (error) {
                res.status(500).json({ message: "Internal server error" });
            }
        });
    });
});

app.listen(PORT, HOST, () => {
    console.log(`Server running at http://${HOST}:${PORT}/`);
});