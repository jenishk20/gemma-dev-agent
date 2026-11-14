package main

import (
	"database/sql"
	"fmt"
	"html/template"
	"log"
	"strings"

	"github.com/gofiber/fiber/v2"
	_ "github.com/mattn/go-sqlite3"
)

type Product struct {
	ID   int
	Name string
	Tags string
}

var db *sql.DB

func initDB() {
	var err error
	db, err = sql.Open("sqlite3", "./db.sqlite3")
	if err != nil {
		log.Fatal(err)
	}

	sqlStmt := `
	CREATE TABLE IF NOT EXISTS products (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		product_name TEXT,
		tags TEXT
	);`
	_, err = db.Exec(sqlStmt)
	if err != nil {
		log.Fatal(err)
	}
}

type PostRequest struct {
	ProductName string   `json:"product_name"`
	Tags        []string `json:"tags"`
}

func main() {
	initDB()
	defer db.Close()

	app := fiber.New()

	// HTML Template for recommendations
	tmpl := template.Must(template.New("recommender").Parse(`
		<!DOCTYPE html>
		<html>
		<head><title>Recommendations</title></head>
		<body>
			<h1>Recommended Products</h1>
			<ul>
			{{range .}}
				<li><strong>{{.Name}}</strong> (Tags: {{.Tags}})</li>
			{{else}}
				<li>No products found matching those tags.</li>
			{{end}}
			</ul>
		</body>
		</html>
	`))

	app.Get("/recommender", func(c *fiber.Ctx) error {
		tagsQuery := c.Query("tags")
		if tagsQuery == "" {
			return c.Status(400).SendString("Missing tags parameter")
		}

		searchTags := strings.Split(tagsQuery, ",")
		var products []Product

		// We fetch all products and filter in Go for simplicity with the comma-separated tags storage
		rows, err := db.Query("SELECT id, product_name, tags FROM products")
		if err != nil {
			return c.Status(500).SendString("Database error")
		}
		defer rows.Close()

		for rows.Next() {
			var p Product
			if err := rows.Scan(&p.ID, &p.Name, &p.Tags); err != nil {
				continue
			}

			productTags := strings.Split(p.Tags, ",")
			match := false
			for _, st := range searchTags {
				st = strings.TrimSpace(st)
				for _, pt := range productTags {
					if strings.TrimSpace(pt) == st {
						match = true
						break
					}
				}
				if match {
					break
				}
			}
			if match {
				products = append(products, p)
			}
		}

		// Render HTML
		c.Set("Content-Type", "text/html")
		return c.WriteBuffer(renderTemplate(tmpl, products))
	})

	app.Post("/recommender", func(c *fiber.Ctx) error {
		req := new(PostRequest)
		if err := c.BodyParser(req); err != nil {
			return c.Status(400).SendString("Invalid input")
		}

		if req.ProductName == "" || len(req.Tags) == 0 {
			return c.Status(400).SendString("Invalid input: name and tags are required")
		}

		tagsString := strings.Join(req.Tags, ",")
		_, err := db.Exec("INSERT INTO products (product_name, tags) VALUES (?, ?)", req.ProductName, tagsString)
		if err != nil {
			return c.Status(500).SendString("Database error")
		}

		return c.SendStatus(200)
	})

	log.Fatal(app.Listen("0.0.0.0:5000"))
}

func renderTemplate(tmpl *template.Template, data interface{}) []byte {
	var buf strings.Builder
	err := tmpl.Execute(&buf, data)
	if err != nil {
		return []byte("Error rendering template")
	}
	return []byte(buf.String())
}