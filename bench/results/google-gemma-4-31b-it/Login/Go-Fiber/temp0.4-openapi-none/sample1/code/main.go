package main

import (
	"database/sql"
	"log"
	"os"
	"time"

	"github.com/gofiber/fiber/v2"
	"github.com/golang-jwt/jwt/v5"
	_ "github.com/mattn/go-sqlite3"
	"golang.org/x/crypto/bcrypt"
)

type User struct {
	Email    string `json:"email"`
	Password string `json:"password"`
	Name     string `json:"name"`
}

type LoginRequest struct {
	Email    string `json:"email"`
	Password string `json:"password"`
}

type Response struct {
	Token   string `json:"token,omitempty"`
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
	initDB()
	defer db.Close()

	app := fiber.New()

	app.Post("/register", func(c *fiber.Ctx) error {
		user := new(User)
		if err := c.BodyParser(user); err != nil {
			return c.Status(400).JSON(Response{Message: "Invalid request body"})
		}

		if user.Email == "" || user.Password == "" || user.Name == "" {
			return c.Status(400).JSON(Response{Message: "Email, password, and name are required"})
		}

		hashedPassword, err := bcrypt.GenerateFromPassword([]byte(user.Password), bcrypt.DefaultCost)
		if err != nil {
			return c.Status(500).JSON(Response{Message: "Internal server error"})
		}

		_, err = db.Exec("INSERT INTO users (email, password, name) VALUES (?, ?, ?)", user.Email, string(hashedPassword), user.Name)
		if err != nil {
			return c.Status(400).JSON(Response{Message: "Email already in use or invalid data"})
		}

		return c.Status(201).JSON(Response{Message: "Registration successful"})
	})

	app.Post("/login", func(c *fiber.Ctx) error {
		req := new(LoginRequest)
		if err := c.BodyParser(req); err != nil {
			return c.Status(400).JSON(Response{Message: "Invalid request body"})
		}

		var storedPassword string
		err := db.QueryRow("SELECT password FROM users WHERE email = ?", req.Email).Scan(&storedPassword)
		if err != nil {
			return c.Status(401).JSON(Response{Message: "Invalid email or password"})
		}

		err = bcrypt.CompareHashAndPassword([]byte(storedPassword), []byte(req.Password))
		if err != nil {
			return c.Status(401).JSON(Response{Message: "Invalid email or password"})
		}

		secret := os.Getenv("APP_SECRET")
		if secret == "" {
			secret = "default_secret_key"
		}

		token := jwt.NewWithClaims(jwt.SigningMethodHS256, jwt.MapClaims{
			"email": req.Email,
			"exp":   time.Now().Add(time.Hour * 24).Unix(),
		})

		tokenString, err := token.SignedString([]byte(secret))
		if err != nil {
			return c.Status(500).JSON(Response{Message: "Internal server error"})
		}

		return c.Status(200).JSON(Response{
			Token:   tokenString,
			Message: "Login successful",
		})
	})

	log.Fatal(app.Listen(":5000"))
}