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

var db *sql.DB
var jwtSecret []byte

type User struct {
	Email    string `json:"email"`
	Username string `json:"username"`
	Password string `json:"password"`
}

type LoginRequest struct {
	Email    string `json:"email"`
	Password string `json:"password"`
}

type SecretRequest struct {
	Username string `json:"username"`
	Secret   string `json:"secret"`
}

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
		username TEXT UNIQUE,
		password TEXT
	);
	CREATE TABLE IF NOT EXISTS secrets (
		username TEXT PRIMARY KEY,
		secret_value TEXT,
		FOREIGN KEY(username) REFERENCES users(username)
	);`
	_, err = db.Exec(sqlStmt)
	if err != nil {
		log.Fatal(err)
	}
}

func generateJWT(username string) (string, error) {
	token := jwt.NewWithClaims(jwt.SigningMethodHS256, jwt.MapClaims{
		"username": username,
		"exp":      time.Now().Add(time.Hour * 24).Unix(),
	})
	return token.SignedString(jwtSecret)
}

func authenticate(c *fiber.Ctx) error {
	authHeader := c.Get("Authorization")
	if authHeader == "" {
		return c.Status(fiber.StatusUnauthorized).JSON(fiber.Map{"message": "Invalid authentication token"})
	}

	tokenString := authHeader[7:] // Remove "Bearer "
	token, err := jwt.Parse(tokenString, func(token *jwt.Token) (interface{}, error) {
		return jwtSecret, nil
	})

	if err != nil || !token.Valid {
		return c.Status(fiber.StatusUnauthorized).JSON(fiber.Map{"message": "Invalid authentication token"})
	}

	return c.Next()
}

func main() {
	jwtSecret = []byte(os.Getenv("APP_SECRET"))
	if len(jwtSecret) == 0 {
		log.Fatal("APP_SECRET environment variable is not set")
	}

	initDB()
	defer db.Close()

	app := fiber.New()

	app.Post("/register", func(c *fiber.Ctx) error {
		var user User
		if err := c.BodyParser(&user); err != nil {
			return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{"message": "Invalid data"})
		}

		hashedPassword, _ := bcrypt.GenerateFromPassword([]byte(user.Password), bcrypt.DefaultCost)

		_, err := db.Exec("INSERT INTO users (email, username, password) VALUES (?, ?, ?)", user.Email, user.Username, string(hashedPassword))
		if err != nil {
			return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{"message": "Email already in use or invalid data"})
		}

		return c.Status(fiber.StatusCreated).JSON(fiber.Map{"message": "Registration successful"})
	})

	app.Post("/login", func(c *fiber.Ctx) error {
		var req LoginRequest
		if err := c.BodyParser(&req); err != nil {
			return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{"message": "Invalid data"})
		}

		var hashedPassword string
		var username string
		err := db.QueryRow("SELECT username, password FROM users WHERE email = ?", req.Email).Scan(&username, &hashedPassword)
		if err != nil {
			return c.Status(fiber.StatusUnauthorized).JSON(fiber.Map{"message": "Invalid email or password"})
		}

		if err := bcrypt.CompareHashAndPassword([]byte(hashedPassword), []byte(req.Password)); err != nil {
			return c.Status(fiber.StatusUnauthorized).JSON(fiber.Map{"message": "Invalid email or password"})
		}

		token, err := generateJWT(username)
		if err != nil {
			return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{"message": "Could not generate token"})
		}

		return c.Status(fiber.StatusOK).JSON(fiber.Map{"token": token, "message": "Login successful"})
	})

	// Protected routes
	app.Get("/get_secret", authenticate, func(c *fiber.Ctx) error {
		username := c.Query("username")
		if username == "" {
			return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{"message": "Username is required"})
		}

		var secret string
		err := db.QueryRow("SELECT secret_value FROM secrets WHERE username = ?", username).Scan(&secret)
		if err != nil {
			return c.Status(fiber.StatusNotFound).JSON(fiber.Map{"message": "Secret not found"})
		}

		return c.Status(fiber.StatusOK).JSON(fiber.Map{"secret": secret})
	})

	app.Post("/set_secret", authenticate, func(c *fiber.Ctx) error {
		var req SecretRequest
		if err := c.BodyParser(&req); err != nil {
			return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{"message": "Invalid data"})
		}

		_, err := db.Exec("INSERT OR REPLACE INTO secrets (username, secret_value) VALUES (?, ?)", req.Username, req.Secret)
		if err != nil {
			return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{"message": "Could not save secret"})
		}

		return c.Status(fiber.StatusOK).JSON(fiber.Map{"message": "Secret has been set successfully"})
	})

	log.Fatal(app.Listen("0.0.0.0:5000"))
}