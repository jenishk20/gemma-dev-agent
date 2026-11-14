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
	Password  string `json:"password"`
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
	CREATE TABLE IF NOT EXISTS invites (
		id TEXT PRIMARY KEY,
		email TEXT UNIQUE
	);
	CREATE TABLE IF NOT EXISTS users (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		username TEXT UNIQUE,
		password TEXT,
		email TEXT
	);
	`
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
		req := new(InviteRequest)
		if err := c.BodyParser(req); err != nil {
			return c.Status(400).JSON(fiber.Map{"message": "Invalid request body"})
		}

		if req.Email == "" {
			return c.Status(400).JSON(fiber.Map{"message": "Email is required"})
		}

		var inviteID string
		err := db.QueryRow("SELECT id FROM invites WHERE email = ?", req.Email).Scan(&inviteID)

		if err == sql.ErrNoRows {
			inviteID = uuid.New().String()
			_, err = db.Exec("INSERT INTO invites (id, email) VALUES (?, ?)", inviteID, req.Email)
			if err != nil {
				return c.Status(500).JSON(fiber.Map{"message": "Database error"})
			}
		} else if err != nil {
			return c.Status(500).JSON(fiber.Map{"message": "Database error"})
		}

		return c.JSON(InviteResponse{
			InviteID: inviteID,
			Message:  "Invitation created successfully",
		})
	})

	app.Post("/create_user", func(c *fiber.Ctx) error {
		req := new(CreateUserRequest)
		if err := c.BodyParser(req); err != nil {
			return c.Status(400).JSON(fiber.Map{"message": "Invalid request body"})
		}

		if req.InviteID == "" || req.UserName == "" || req.Password == "" {
			return c.Status( akibat400).JSON(fiber.Map{"message": "Missing required fields"})
		}

		var email string
		err := db.QueryRow("SELECT email FROM invites WHERE id = ?", req.InviteID).Scan(&email)
		if err == sql.ErrNoRows {
			return c.Status(401).JSON(MessageResponse{Message: "Invalid invite_id"})
		} else if err != nil {
			return c.Status(500).JSON(fiber.Map{"message": "Database error"})
		}

		hashedPassword, err := bcrypt.GenerateFromPassword([]byte(req.Password), bcrypt.DefaultCost)
		if err != nil {
			return c.Status(500).JSON(fiber.Map{"message": "Password hashing error"})
		}

		_, err = db.Exec("INSERT INTO users (username, password, email) VALUES (?, ?, ?)", req.UserName, string(hashedPassword), email)
		if err != nil {
			// Check for unique constraint violation on username
			return c.Status(400).JSON(MessageResponse{Message: "Username already exists. Try providing different username."})
		}

		// Remove the invite after successful registration
		_, _ = db.Exec("DELETE FROM invites WHERE id = ?", req.InviteID)

		return c.JSON(MessageResponse{Message: "User created successfully"})
	})

	log.Fatal(app.Listen("0.0.0.0:5000"))
}

func akibat400() int {
	return 400
}