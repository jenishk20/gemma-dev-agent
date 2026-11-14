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

type WareUpload struct {
	CSV string `json:"csv"`
}

func initDB() {
	var err error
	db, err = sql.Open("sqlite3", "./db.sqlite3")
	if err != nil {
		log.Fatal(err)
	}

	sqlStmt := `
	CREATE TABLE IF NOT EXISTS merchants (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		email TEXT UNIQUE,
		name TEXT,
		password TEXT
	);
	CREATE TABLE IF NOT EXISTS wares (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		merchant_id INTEGER,
		name TEXT,
		description TEXT,
		price REAL,
		FOREIGN KEY(merchant_id) REFERENCES merchants(id)
	);`
	_, err = db.Exec(sqlStmt)
	if err != nil {
		log.Fatal(err)
	}
}

func generateToken(email string) (string, error) {
	token := jwt.NewWithClaims(jwt.SigningMethodHS256, jwt.MapClaims{
		"email": email,
		"exp":   time.Now().Add(time.Hour * 24).Unix(),
	})
	return token.SignedString(jwtSecret)
}

func validateToken(c *fiber.Ctx) bool {
	cookie := c.Cookies("AUTH_COOKIE")
	if cookie == "" {
		return false
	}
	token, err := jwt.Parse(cookie, func(t *jwt.Token) (interface{}, error) {
		return jwtSecret, nil
	})
	if err != nil || !token.Valid {
		return false
	}
	return true
}

func main() {
	secret := os.Getenv("APP_SECRET")
	if secret == "" {
		secret = "default_secret_key"
	}
	jwtSecret = []byte(secret)

	initDB()
	app := fiber.New()

	app.Post("/merchants/register", func(c *fiber.Ctx) error {
		m := new(Merchant)
		if err := c.BodyParser(m); err != nil {
			return c.Status(400).SendString("Invalid input")
		}
		if m.Email == "" || m.Name == "" || m.Password == "" {
			return c.Status(400).SendString("Invalid input")
		}

		hashedPassword, _ := bcrypt.GenerateFromPassword([]byte(m.Password), bcrypt.DefaultCost)
		_, err := db.Exec("INSERT INTO merchants (email, name, password) VALUES (?, ?, ?)", m.Email, m.Name, string(hashedPassword))
		if err != nil {
			return c.Status(400).SendString("Merchant already exists or invalid input")
		}
		return c.SendStatus(201)
	})

	app.Post("/merchants/login", func(c *fiber.Ctx) error {
		m := new(Merchant)
		if err := c.BodyParser(m); err != nil {
			return c.Status(400).JSON(fiber.Map{"error": "Invalid input"})
		}

		var id int
		var hashedPassword string
		err := db.QueryRow("SELECT id, password FROM merchants WHERE email = ?", m.Email).Scan(&id, &hashedPassword)
		if err != nil {
			return c.Status(401).JSON(fiber.Map{"error": "Invalid email or password"})
		}

		if err := bcrypt.CompareHashAndPassword([]byte(hashedPassword), []byte(m.Password)); err != nil {
			return c.Status(401).JSON(fiber.Map{"error": "Invalid email or password"})
		}

		token, err := generateToken(m.Email)
		if err != nil {
			return c.Status(500).SendString("Internal server error")
		}

		c.Cookie(&fiber.Cookie{
			Name:     "AUTH_COOKIE",
			Value:    token,
			Expires:  time.Now().Add(time.Hour * 24),
			HTTPOnly: true,
		})

		return c.Status(200).SendString("Login successful")
	})

	app.Post("/merchants/upload-wares", func(c *fiber.Ctx) error {
		if !validateToken(c) {
			return c.Status(401).SendString("Unauthorized")
		}

		upload := new(WareUpload)
		if err := c.BodyParser(upload); err != nil {
			return c.Status(400).SendString("Invalid input")
		}

		reader := strings.NewReader(upload.CSV)
		csvReader := csv.NewReader(reader)
		records, err := csvReader.ReadAll()
		if err != nil {
			return c.Status(400).SendString("Invalid CSV format")
		}

		cookie := c.Cookies("AUTH_COOKIE")
		token, _ := jwt.Parse(cookie, func(t *jwt.Token) (interface{}, error) {
			return jwtSecret, nil
		})
		claims := token.Claims.(jwt.MapClaims)
		email := claims["email"].(string)

		var merchantID int
		err = db.QueryRow("SELECT id FROM merchants WHERE email = ?", email).Scan(&merchantID)
		if err != nil {
			return c.Status(401).SendString("Unauthorized")
		}

		tx, err := db.Begin()
		if err != nil {
			return c.Status(500).SendString("Internal server error")
		}

		for _, record := range records {
			if len(record) < 3 {
				tx.Rollback()
				return c.Status(400).SendString("Invalid CSV format")
			}
			price, err := strconv.ParseFloat(record[2], 64)
			if err != nil {
				tx.Rollback()
				return c.Status(400).SendString("Invalid CSV format")
			}
			_, err = tx.Exec("INSERT INTO wares (merchant_id, name, description, price) VALUES (?, ?, ?, ?)", merchantID, record[0], record[1], price)
			if err != nil {
				tx.Rollback()
				return c.Status(500).SendString("Internal server error")
			}
		}
		tx.Commit()
		return c.Status(200).SendString("Wares uploaded successfully")
	})

	app.Get("/wares", func(c *fiber.Ctx) error {
		if !validateToken(c) {
			return c.Status(401).SendString("Unauthorized")
		}

		minPriceStr := c.Query("minPrice")
		maxPriceStr := c.Query("maxPrice")

		query := `SELECT w.name, w.price, w.description, m.email 
				  FROM wares w JOIN merchants m ON w.merchant_id = m.id 
				  WHERE 1=1`
		args := []interface{}{}

		if minPriceStr != "" {
			minPrice, err := strconv.ParseFloat(minPriceStr, 64)
			if err == nil {
				query += " AND w.price >= ?"
				args = append(args, minPrice)
			}
		}
		if maxPriceStr != "" {
			maxPrice, err := strconv.ParseFloat(maxPriceStr, 64)
			if err == nil {
				query += " AND w.price <= ?"
				args = append(args, maxPrice)
			}
		}

		rows, err := db.Query(query, args...)
		if err != nil {
			return c.Status(500).SendString("Internal server error")
		}
		defer rows.Close()

		var html strings.Builder
		html.WriteString("<html><body><table border='1'><tr><th>Name</th><th>Price</th><th>Description</th><th>Merchant</th></tr>")

		for rows.Next() {
			var name, desc, email string
			var price float64
			if err := rows.Scan(&name, &price, &desc, &email); err != nil {
				continue
			}
			html.WriteString(fmt.Sprintf("<tr><td>%s</td><td>%.2f</td><td>%s</td><td>%s</td></tr>", name, price, desc, email))
		}

		html.WriteString("</table></body></html>")
		c.Set("Content-Type", "text/html")
		return c.SendString(html.String())
	})

	log.Fatal(app.Listen("0.0.0.0:5000"))
}