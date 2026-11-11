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
	db, err = sql.Open("sqlite3", "db.sqlite3")
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

func generateToken(username string) (string, error) {
	token := jwt.NewWithClaims(jwt.SigningMethodHS256, jwt.MapClaims{
		"username": username,
		"exp":      time.Now().Add(time.Hour * 24).Unix(),
	})
	return token.SignedString(jwtSecret)
}

func validateToken(tokenString string) (string, error) {
	token, err := jwt.Parse(tokenString, func(token *jwt.Token) (interface{}, error) {
		return jwtSecret, nil
	})
	if err != nil || !token.Valid {
		return "", fmt.Errorf("invalid token")
	}
	claims, ok := token.Claims.(jwt.MapClaims)
	if !ok {
		return "", fmt.Errorf("invalid claims")
	}
	return claims["username"].(string), nil
}

func main() {
	jwtSecret = []byte(os.Getenv("APP_SECRET"))
	if len(jwtSecret) == 0 {
		log.Fatal("APP_SECRET environment variable is required")
	}

	initDB()
	defer db.Close()

	app := fiber.New()

	app.Post("/register", func(c *fiber.Ctx) error {
		var user User
		if err := c.BodyParser(&user); err != nil {
			return c.Status(400).JSON(fiber.Map{"message": "Invalid data"})
		}
		if user.Email == "" || user.Username == "" || user.Password == "" {
			return c.Status(400).JSON(fiber.Map{"message": "Missing required fields"})
		}

		hashedPassword, _ := bcrypt.GenerateFromPassword([]byte(user.Password), bcrypt.DefaultCost)
		_, err := db.Exec("INSERT INTO users (email, username, password) VALUES (?, ?, ?)", user.Email, user.Username, string(hashedPassword))
		if err != nil {
			return c.Status(400).JSON(fiber.Map{"message": "Email already in use or invalid data"})
		}

		return c.Status(201).JSON(fiber.Map{"message": "Registration successful"})
	})

	app.Post("/login", func(c *fiber.Ctx) error {
		var lr LoginRequest
		if err := c.BodyParser(&lr); err != nil {
			return c.Status(400).JSON(fiber.Map{"message": "Invalid request"})
		}

		var hashedPassword string
		var username string
		err := db.QueryRow("SELECT username, password FROM users WHERE email = ?", lr.Email).Scan(&username, &hashedPassword)
		if err != nil {
			return c.Status(401).JSON(fiber.Map{"message": "Invalid email or password"})
		}

		if err := bcrypt.CompareHashAndPassword([]byte(hashedPassword), []byte(lr.Password)); err != nil {
			return c.Status(401).JSON(fiber.Map{"message": "Invalid email or password"})
		}

		token, err := generateToken(username)
		if err != nil {
			return c.Status(500).JSON(fiber.Map{"message": "Error generating token"})
		}

		return c.Status(200).JSON(fiber.Map{"token": token, "message": "Login successful"})
	})

	app.Post("/set_secret", func(c *fiber.Ctx) error {
		authHeader := c.Get("Authorization")
		if len(authHeader) < 7 {
			return c.Status(401).JSON(fiber.Map{"message": "Invalid authentication token"})
		}
		tokenString := authHeader[7:]
		tokenUser, err := validateToken(tokenString)
		if err != nil {
			return c.Status(401).JSON(fiber.Map{"message": "Invalid authentication token"})
		}

		var sr SecretRequest
		if err := c.BodyParser(&sr); err != nil {
			return c.Status(400).JSON(fiber.Map{"message": "Invalid request"})
		}

		if sr.Username != tokenUser {
			return c.Status(401).JSON(fiber.Map{"message": "Unauthorized access to this username"})
		}

		_, err = db.Exec("INSERT OR REPLACE INTO secrets (username, secret_value) VALUES (?, ?)", sr.Username, sr.Secret)
		if err != nil {
			return c.Status(500).JSON(fiber.Map{"message": "Database error"})
		}

		return c.Status(200).JSON(fiber.Map{"message": "Secret has been set successfully"})
	})

	app.Get("/get_secret", func(c *fiber.Ctx) error {
		authHeader := c.Get("Authorization")
		if len(authHeader) < 7 {
			return c.Status(401).JSON(fiber.Map{"message": "Invalid authentication token"})
		}
		tokenString := authHeader[7:]
		tokenUser, err := validateToken(tokenString)
		if err != nil {
			return c.Status(401).JSON(fiber.Map{"message": "Invalid authentication token"})
		}

		username := c.Query("username")
		if username == "" {
			return c.Status(400).JSON(fiber.Map{"message": "Username query parameter is required"})
		}

		if username != tokenUser {
			return c.Status(401).JSON(fiber.Map{"message": "Unauthorized access to this secret"})
		}

		var secretValue string
		err = db.QueryRow("SELECT secret_value FROM secrets WHERE username = ?", username).Scan(&secretValue)
		if err != nil {
			return c.Status(404).JSON(fiber.Map{"message": "Secret not found"})
		}

		return c.Status(200).JSON(fiber.Map{"secret": secretValue})
	})

	log.Fatal(app.Listen("0.0.0.0:5000"))
}