package main

import (
	"database/sql"
	"fmt"
	"log"
	"os"

	"github.com/gofiber/fiber/v2"
	"github.com/google/uuid"
	_ "github.com/mattn/go-sqlite3"
	"golang.org/x/crypto/bcrypt"
)

type InviteRequest struct {
	Email string `json:"email"`
}

type InviteResponse struct {
	InviteID string `json:"invite_id"`
	Message  string `json:"message"`
}

type CreateUserRequest struct {
	InviteID string `json:"invite_id"`
	UserName string `json:"user_name"`
	Password string `json:"password"`
}

type MessageResponse struct {
	Message string `json:"message"`
}

var db *sql.DB

func initDB() {
	var err error
	db, err = sql.Open("sqlite3", "./db.sqlite3")
	if err != nil {
		log.Fatal(err)
	}

	sqlStmt := `
	CREATE TABLE IF NOT EXISTS invitations (
		id TEXT PRIMARY KEY,
		email TEXT UNIQUE NOT NULL
	);
	CREATE TABLE IF NOT EXISTS users (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		username TEXT UNIQUE NOT NULL,
		password TEXT NOT NULL,
		email TEXT NOT NULL
	);`
	_, err = db.Exec(sqlStmt)
	if err != nil {
		log.Fatal(err)
	}
}

func main() {
	initDB()
	defer db.Close()

	app := fiber.New()

	app.Post("/invite_user", func(c *fiber.Ctx) error {
		var req InviteRequest
		if err := c.BodyParser(&req); err != nil {
			return c.Status(400).JSON(fiber.Map{"message": "Invalid request body"})
		}

		if req.Email == "" {
			return c.Status(400).JSON(fiber.Map{"message": "Email is required"})
		}

		var inviteID string
		err := db.QueryRow("SELECT id FROM invitations WHERE email = ?", req.Email).Scan(&inviteID)

		if err == sql.ErrNoRows {
			inviteID = uuid.New().String()
			_, err = db.Exec("INSERT INTO invitations (id, email) VALUES (?, ?)", inviteID, req.Email)
			if err != nil {
				return c.Status(500).JSON(fiber.Map{"message": "Database error"})
			}
		} else if err != nil {
			return c.Status(500).JSON(fiber.Map{"message": "Database error"})
		}

		return c.Status(200).JSON(InviteResponse{
			InviteID: inviteID,
			Message:  "Invitation created successfully",
		})
	})

	app.Post("/create_user", func(c *fiber.Ctx) error {
		var req CreateUserRequest
		if err := c.BodyParser(&req); err != nil {
			return c.Status(400).JSON(fiber.Map{"message": "Invalid request body"})
		}

		if req.InviteID == "" || req.UserName == "" || req.Password == "" {
			return c.Status(400).JSON(fiber.Map{"message": "Missing required fields"})
		}

		var email string
		err := db.QueryRow("SELECT email FROM invitations WHERE id = ?", req.InviteID).Scan(&email)
		if err == sql.ErrNoRows {
			return c.Status(401).JSON(MessageResponse{Message: "Invalid invite_id"})
		} else if err != nil {
			return c.Status(500).JSON(fiber.Map{"message": "Database error"})
		}

		hashedPassword, err := bcrypt.GenerateFromPassword([]byte(req.Password), bcrypt.DefaultCost)
		if err != nil {
			return c.Status(500).JSON(fiber.Map{"message": "Error hashing password"})
		}

		_, err = db.Exec("INSERT INTO users (username, password, email) VALUES (?, ?, ?)", req.UserName, string(hashedPassword), email)
		if err != nil {
			// Check for unique constraint violation on username
			return c.Status(400).JSON(MessageResponse{Message: "Username already exists. Try providing different username."})
		}

		// Delete the invitation after use
		_, _ = db.Exec("DELETE FROM invitations WHERE id = ?", req.InviteID)

		return c.Status(200).JSON(MessageResponse{Message: "User created"})
	})

	log.Fatal(app.Listen("0.0.0.0:5000"))
}