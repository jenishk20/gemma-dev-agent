package main

import (
	"database/sql"
	"encoding/csv"
	"fmt"
	"log"
	"net/http"
	"os"
	"strconv"
	"strings"
	"time"

	"github.com/gofiber/fiber/v2"
	"github.com/golang-jwt/jwt/v5"
	_ "github.com/mattn/go-sqlite3"
	"golang.org/x/crypto/bcrypt"
)

var db *sql.DB
var jwtSecret []byte

type Merchant struct {
	Email    string `json:"email"`
	Name     string `json:"name"`
	Password string `json:"password"`
}

type Ware struct {
	ID          int
	Name        string
	Description string
	Price       float64
	MerchantEmail string
}

func initDB() {
	var err error
	db, err = sql.Open("sqlite3", "./db.sqlite3")
	if err != nil {
		log.Fatal(err)
	}

	sqlStmt := `
	CREATE TABLE IF NOT EXISTS merchants (
		email TEXT PRIMARY KEY,
		name TEXT,
		password TEXT
	);
	CREATE TABLE IF NOT EXISTS wares (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		name TEXT,
		description TEXT,
		price REAL,
		merchant_email TEXT,
		FOREIGN KEY(merchant_email) REFERENCES merchants(email)
	);`
	_, err = db.Exec(sqlStmt)
	if err != nil {
		log.Fatal(err)
	}
}

func createToken(email string) (string, error) {
	token := jwt.NewWithClaims(jwt.SigningMethodHS256, jwt.MapClaims{
		"email": email,
		"exp":   time.Now().Add(time.Hour * 24).Unix(),
	})
	return token.SignedString(jwtSecret)
}

func verifyToken(tokenString string) (string, error) {
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
	return claims["email"].(string), nil
}

func main() {
	secret := os.Getenv("APP_SECRET")
	if secret == "" {
		secret = "default_secret_key"
	}
	jwtSecret = []byte(secret)

	initDB()
	defer db.Close()

	app := fiber.New()

	app.Post("/merchants/register", func(c *fiber.Ctx) error {
		m := new(Merchant)
		if err := c.BodyParser(m); err != nil {
			return c.Status(400).SendString("Invalid input")
		}
		if m.Email == "" || m.Name == "" || m.Password == "" {
			return c.Status(400).SendString("Missing required fields")
		}

		hashedPassword, _ := bcrypt.GenerateFromPassword([]byte(m.Password), bcrypt.DefaultCost)
		_, err := db.Exec("INSERT INTO merchants (email, name, password) VALUES (?, ?, ?)", m.Email, m.Name, string(hashedPassword))
		if err != nil {
			return c.Status(400).SendString("Merchant already exists or database error")
		}
		return c.SendStatus(201)
	})

	app.Post("/merchants/login", func(c *fiber.Ctx) error {
		var input struct {
			Email    string `json:"email"`
			Password string `json:"password"`
		}
		if err := c.BodyParser(&input); err != nil {
			return c.Status(400).SendString("Invalid input")
		}

		var hashedPassword string
		err := db.QueryRow("SELECT password FROM merchants WHERE email = ?", input.Email).Scan(&hashedPassword)
		if err != nil {
			return c.Status(401).JSON(fiber.Map{"error": "Invalid email or password"})
		}

		if err := bcrypt.CompareHashAndPassword([]byte(hashedPassword), []byte(input.Password)); err != nil {
			return c.Status(401).JSON(fiber.Map{"error": "Invalid email or password"})
		}

		token, err := createToken(input.Email)
		if err != nil {
			return c.Status(500).SendString("Internal server error")
		}

		c.Cookie(&fiber.Cookie{
			Name:     "AUTH_COOKIE",
			Value:    token,
			HTTPOnly: true,
		})
		return c.SendString("Login successful")
	})

	app.Post("/merchants/upload-wares", func(c *fiber.Ctx) error {
		cookie := c.Cookies("AUTH_COOKIE")
		email, err := verifyToken(cookie)
		if err != nil {
			return c.Status(401).SendString("Unauthorized")
		}

		var body struct {
			CSV string `json:"csv"`
		}
		if err := c.BodyParser(&body); err != nil {
			return c.Status(400).SendString("Invalid input")
		}

		reader := csv.NewReader(strings.NewReader(body.CSV))
		records, err := reader.ReadAll()
		if err != nil {
			return c.Status(400).SendString("Invalid CSV format")
		}

		tx, err := db.Begin()
		if err != nil {
			return c.Status(500).SendString("DB Error")
		}

		for _, record := range records {
			if len(record) < 3 {
				tx.Rollback()
				return c.Status(400).SendString("Invalid CSV format")
			}
			price, err := strconv.ParseFloat(record[2], 64)
			if err != nil {
				tx.Rollback()
				return c.Status(400).SendString("Invalid price format")
			}
			_, err = tx.Exec("INSERT INTO wares (name, description, price, merchant_email) VALUES (?, ?, ?, ?)", record[0], record[1], price, email)
			if err != nil {
				tx.Rollback()
				return c.Status(500).SendString("DB Error")
			}
		}
		tx.Commit()
		return c.SendStatus(200)
	})

	app.Get("/wares", func(c *fiber.Ctx) error {
		cookie := c.Cookies("AUTH_COOKIE")
		_, err := verifyToken(cookie)
		if err != nil {
			return c.Status(401).SendString("Unauthorized")
		}

		minPriceStr := c.Query("minPrice")
		maxPriceStr := c.Query("maxPrice")

		query := "SELECT name, description, price, merchant_email FROM wares WHERE 1=1"
		var args []interface{}

		if minPriceStr != "" {
			if p, err := strconv.ParseFloat(minPriceStr, 64); err == nil {
				query += " AND price >= ?"
				args = append(args, p)
			}
		}
		if maxPriceStr != "" {
			if p, err := strconv.ParseFloat(maxPriceStr, 64); err == nil {
				query += " AND price <= ?"
				args = append(args, p)
			}
		}

		rows, err := db.Query(query, args...)
		if err != nil {
			return c.Status(500).SendString("DB Error")
		}
		defer rows.Close()

		var html strings.Builder
		html.WriteString("<html><body><table border='1'><tr><th>Name</th><th>Price</th><th>Description</th><th>Merchant</th></tr>")
		for rows.Next() {
			var w Ware
			if err := rows.Scan(&w.Name, &w.Description, &w.Price, &w.MerchantEmail); err != nil {
				continue
			}
			html.WriteString(fmt.Sprintf("<tr><td>%s</td><td>%.2f</td><td>%s</td><td>%s</td></tr>", w.Name, w.Price, w.Description, w.MerchantEmail))
		}
		html.WriteString("</table></body></html>")

		c.Set("Content-Type", "text/html")
		return c.SendString(html.String())
	})

	log.Fatal(app.Listen("0.0.0.0:5000"))
}