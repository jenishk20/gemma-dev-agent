package main

import (
	"database/sql"
	"fmt"
	"log"
	"os"
	"time"

	"github.com/gofiber/fiber/v2"
	"github.com/golang-jwt/jwt/v5"
	_ "github.com/mattn/go-sqlite3"
	"golang.org/x/crypto/bcrypt"
)

type User struct {
	ID       int    `json:"id"`
	Email    string `json:"email"`
	Password string `json:"password"`
	Name     string `json:"name"`
}

type LoginRequest struct {
	Email    string `json:"email"`
	Password string `json:"password"`
}

type RegisterRequest struct {
	Email    string `json:"email"`
	Password string `json:"password"`
	Name     string `json:"name"`
}

var db *sql.DB
var appSecret string

func initDB() {
	var err error
	db, err = sql.Open("sqlite3", "./db.sqlite3")
	if err != nil {
		log.Fatal(err)
	}

	sqlStmt := `
	CREATE TABLE IF NOT EXISTS users (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		email TEXT UNIQUE,
		password TEXT,
		name TEXT
	);`
	_, err = db.Exec(sqlStmt)
	if err != nil {
		log.Fatal(err)
	}
}

func main() {
	appSecret = os.Getenv("APP_SECRET")
	if appSecret == "" {
		appSecret = "default_secret_key"
	}

	initDB()
	defer db.Close()

	app := fiber.New()

	app.Post("/register", func(c *fiber.Ctx) error {
		var req RegisterRequest
		if err := c.BodyParser(&req); err != nil {
			return c.Status(400).JSON(fiber.Map{"message": "Invalid request body"})
		}

		if req.Email == "" || req.Password == "" || req.Name == "" {
			return c.Status(400).JSON(fiber.Map{"message": "Email, password, and name are required"})
		}

		hashedPassword, err := bcrypt.GenerateFromPassword([]byte(req.Password), bcrypt.DefaultCost)
		if err != nil {
			return c.Status(500).JSON(fiber.Map{"message": "Internal server error"})
		}

		_, err = db.Exec("INSERT INTO users (email, password, name) VALUES (?, ?, ?)", req.Email, string(hashedPassword), req.Name)
		if err != nil {
			return c.Status(400).JSON(fiber.Map{"message": "Email already in use or invalid data"})
		}

		return c.Status(201).JSON(fiber.Map{"message": "Registration successful"})
	})

	app.Post("/login", func(c *fiber.Ctx) error {
		var req LoginRequest
		if err := c.BodyParser(&req); err != nil {
			return c.Status(400).JSON(fiber.Map{"message": "Invalid request body"})
		}

		var storedPassword string
		err := db.QueryRow("SELECT password FROM users WHERE email = ?", req.Email).Scan(&storedPassword)
		if err != nil {
			return c.Status(401).JSON(fiber.Map{"message": "Invalid email or password"})
		}

		err = bcrypt.CompareHashAndPassword([]byte(storedPassword), []byte(req.Password))
		if err != nil {
			return c.Status(401).JSON(fiber.Map{"message": "Invalid email or password"})
		}

		token := jwt.NewWithClaims(jwt.SigningMethodHS256, jwt.MapClaims{
			"email": req.Email,
			"exp":   time.Now().Add(time.Hour * 24).Unix(),
		})

		tokenString, err := token.SignedString([]byte(appSecret))
		if err != nil {
			return c.Status(500).JSON(fiber.Map{"message": "Internal server error"})
		}

		return c.Status(200).JSON(fiber.Map{
			"token":   tokenString,
			"message": "Login successful",
		})
	})

	fmt.Println("Server starting on 0.0.0.0:5000")
	log.Fatal(app.Listen("0.0.0.0:5000"))
}