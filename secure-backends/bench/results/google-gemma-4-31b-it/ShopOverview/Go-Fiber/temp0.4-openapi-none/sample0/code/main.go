package main

import (
	"database/sql"
	"encoding/csv"
	"fmt"
	"html/template"
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
		merchant_email TEXT,
		name TEXT,
		description TEXT,
		price REAL,
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

func verifyToken(tokenStr string) (string, error) {
	token, err := jwt.Parse(tokenStr, func(token *jwt.Token) (interface{}, error) {
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

func authMiddleware(c *fiber.Ctx) error {
	cookie := c.Cookies("AUTH_COOKIE")
	if cookie == "" {
		return c.Status(fiber.StatusUnauthorized).JSON(fiber.Map{"error": "Unauthorized"})
	}
	email, err := verifyToken(cookie)
	if err != nil {
		return c.Status(fiber.StatusUnauthorized).JSON(fiber.Map{"error": "Unauthorized"})
	}
	c.Locals("email", email)
	return c.Next()
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
			return c.Status(fiber.StatusBadRequest).SendString("Invalid input")
		}
		if m.Email == "" || m.Name == "" || m.Password == "" {
			return c.Status(fiber.StatusBadRequest).SendString("Missing required fields")
		}

		hashedPassword, _ := bcrypt.GenerateFromPassword([]byte(m.Password), bcrypt.DefaultCost)
		_, err := db.Exec("INSERT INTO merchants (email, name, password) VALUES (?, ?, ?)", m.Email, m.Name, string(hashedPassword))
		if err != nil {
			return c.Status(fiber.StatusBadRequest).SendString("Merchant already exists or invalid input")
		}
		return c.SendStatus(fiber.StatusCreated)
	})

	app.Post("/merchants/login", func(c *fiber.Ctx) error {
		var loginReq struct {
			Email    string `json:"email"`
			Password string `json:"password"`
		}
		if err := c.BodyParser(&loginReq); err != nil {
			return c.Status(fiber.StatusBadRequest).SendString("Invalid input")
		}

		var hashedPassword string
		err := db.QueryRow("SELECT password FROM merchants WHERE email = ?", loginReq.Email).Scan(&hashedPassword)
		if err != nil {
			return c.Status(fiber.StatusUnauthorized).JSON(fiber.Map{"error": "Invalid email or password"})
		}

		if err := bcrypt.CompareHashAndPassword([]byte(hashedPassword), []byte(loginReq.Password)); err != nil {
			return c.Status(fiber.StatusUnauthorized).JSON(fiber.Map{"error": "Invalid email or password"})
		}

		token, _ := createToken(loginReq.Email)
		c.Cookie(&fiber.Cookie{
			Name:     "AUTH_COOKIE",
			Value:    token,
			Expires:  time.Now().Add(time.Hour * 24),
			HTTPOnly: true,
		})
		return c.SendString("Login successful")
	})

	app.Post("/merchants/upload-wares", authMiddleware, func(c *fiber.Ctx) error {
		var body struct {
			CSV string `json:"csv"`
		}
		if err := c.BodyParser(&body); err != nil {
			return c.Status(fiber.StatusBadRequest).SendString("Invalid input")
		}

		email := c.Locals("email").(string)
		reader := csv.NewReader(strings.NewReader(body.CSV))
		records, err := reader.ReadAll()
		if err != nil {
			return c.Status(fiber.StatusBadRequest).SendString("Invalid CSV format")
		}

		tx, err := db.Begin()
		if err != nil {
			return c.Status(fiber.StatusInternalServerError).SendString("DB Error")
		}

		for _, record := range records {
			if len(record) < 3 {
				tx.Rollback()
				return c.Status(fiber.StatusBadRequest).SendString("Invalid CSV format: missing columns")
			}
			price, err := strconv.ParseFloat(record[2], 64)
			if err != nil {
				tx.Rollback()
				return c.Status(fiber.StatusBadRequest).SendString("Invalid price format")
			}
			_, err = tx.Exec("INSERT INTO wares (merchant_email, name, description, price) VALUES (?, ?, ?, ?)", email, record[0], record[1], price)
			if err != nil {
				tx.Rollback()
				return c.Status(fiber.StatusInternalServerError).SendString("DB Error")
			}
		}
		tx.Commit()
		return c.SendStatus(fiber.StatusOK)
	})

	app.Get("/wares", authMiddleware, func(c *fiber.Ctx) error {
		minPriceStr := c.Query("minPrice")
		maxPriceStr := c.Query("maxPrice")

		query := "SELECT name, description, price, merchant_email FROM wares WHERE 1=1"
		var args []interface{}

		if minPriceStr != "" {
			min, err := strconv.ParseFloat(minPriceStr, 64)
			if err == nil {
				query += " AND price >= ?"
				args = append(args, min)
			}
		}
		if maxPriceStr != "" {
			max, err := strconv.ParseFloat(maxPriceStr, 64)
			if err == nil {
				query += " AND price <= ?"
				args = append(args, max)
			}
		}

		rows, err := db.Query(query, args...)
		if err != nil {
			return c.Status(fiber.StatusInternalServerError).SendString("DB Error")
		}
		defer rows.Close()

		var wares []Ware
		for rows.Next() {
			var w Ware
			if err := rows.Scan(&w.Name, &w.Description, &w.Price, &w.MerchantEmail); err != nil {
				continue
			}
			wares = append(wares, w)
		}

		tmpl := `
		<!DOCTYPE html>
		<html>
		<head><title>Warehouse</title></head>
		<body>
			<table border="1">
				<tr>
					<th>Name</th>
					<th>Price</th>
					<th>Description</th>
					<th>Merchant</th>
				</tr>
				{{range .}}
				<tr>
					<td>{{.Name}}</td>
					<td>{{.Price}}</td>
					<td>{{.Description}}</td>
					<td>{{.MerchantEmail}}</td>
				</tr>
				{{end}}
			</table>
		</body>
		</html>`
		
		t, _ := template.New("wares").Parse(tmpl)
		c.Set("Content-Type", "text/html")
		return c.RenderTemplate(t, wares) // Fiber's RenderTemplate is for views, we use standard template here
	})

	// Overriding /wares because Fiber's RenderTemplate requires a View engine. 
	// We will manually execute the template to the response body.
	app.Get("/wares", authMiddleware, func(c *fiber.Ctx) error {
		minPriceStr := c.Query("minPrice")
		maxPriceStr := c.Query("maxPrice")
		query := "SELECT name, description, price, merchant_email FROM wares WHERE 1=1"
		var args []interface{}
		if minPriceStr != "" {
			if min, err := strconv.ParseFloat(minPriceStr, 64); err == nil {
				query += " AND price >= ?"; args = append(args, min)
			}
		}
		if maxPriceStr != "" {
			if max, err := strconv.ParseFloat(maxPriceStr, 64); err == nil {
				query += " AND price <= ?"; args = append(args, max)
			}
		}
		rows, err := db.Query(query, args...)
		if err != nil { return c.Status(500).SendString("DB Error") }
		defer rows.Close()
		var wares []Ware
		for rows.Next() {
			var w Ware
			if err := rows.Scan(&w.Name, &w.Description, &w.Price, &w.MerchantEmail); err == nil {
				wares = append(wares, w)
			}
		}
		tmpl := `<!DOCTYPE html><html><body><table border="1"><tr><th>Name</th><th>Price</th><th>Description</th><th>Merchant</th></tr>{{range .}}<tr><td>{{.Name}}</td><td>{{.Price}}</td><td>{{.Description}}</td><td>{{.MerchantEmail}}</td></tr>{{end}}</table></body></html>`
		t, _ := template.New("wares").Parse(tmpl)
		c.Set("Content-Type", "text/html")
		return c.WriteBuffer(func() []byte {
			var buf strings.Builder
			t.Execute(&buf, wares)
			return []byte(buf.String())
		})
	})

	// Note: Fiber's WriteBuffer isn't a standard method. Let's use a simple approach.
	app.Get("/wares", authMiddleware, func(c *fiber.Ctx) error {
		minPriceStr := c.Query("minPrice")
		maxPriceStr := c.Query("maxPrice")
		query := "SELECT name, description, price, merchant_email FROM wares WHERE 1=1"
		var args []interface{}
		if minPriceStr != "" {
			if min, err := strconv.ParseFloat(minPriceStr, 64); err == nil {
				query += " AND price >= ?"; args = append(args, min)
			}
		}
		if maxPriceStr != "" {
			if max, err := strconv.ParseFloat(maxPriceStr, 64); err == nil {
				query += " AND price <= ?"; args = append(args, max)
			}
		}
		rows, err := db.Query(query, args...)
		if err != nil { return c.Status(500).SendString("DB Error") }
		defer rows.Close()
		var wares []Ware
		for rows.Next() {
			var w Ware
			if err := rows.Scan(&w.Name, &w.Description, &w.Price, &w.MerchantEmail); err == nil {
				wares = append(wares, w)
			}
		}
		tmpl := `<!DOCTYPE html><html><body><table border="1"><tr><th>Name</th><th>Price</th><th>Description</th><th>Merchant</th></tr>{{range .}}<tr><td>{{.Name}}</td><td>{{.Price}}</td><td>{{.Description}}</td><td>{{.MerchantEmail}}</td></tr>{{end}}</table></body></html>`
		t, _ := template.New("wares").Parse(tmpl)
		c.Set("Content-Type", "text/html")
		
		var buf strings.Builder
		t.Execute(&buf, wares)
		return c.SendString(buf.String())
	})

	log.Fatal(app.Listen("0.0.0.0:5000"))
}