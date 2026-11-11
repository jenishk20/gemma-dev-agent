package main

import (
	"database/sql"
	"fmt"
	"log"
	"strings"

	"github.com/gofiber/fiber/v2"
	_ "github.com/mattn/go-sqlite3"
)

type Product struct {
	Name string   `json:"product_name"`
	Tags []string `json:"tags"`
}

func main() {
	db, err := sql.Open("sqlite3", "./db.sqlite3")
	if err != nil {
		log.Fatal(err)
	}
	defer db.Close()

	// Initialize database schema
	initSQL := `
	CREATE TABLE IF NOT EXISTS products (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		name TEXT NOT NULL
	);
	CREATE TABLE IF NOT EXISTS tags (
		product_id INTEGER,
		tag TEXT NOT NULL,
		FOREIGN KEY(product_id) REFERENCES products(id)
	);`
	if _, err := db.Exec(initSQL); err != nil {
		log.Fatal(err)
	}

	app := fiber.New()

	app.Get("/recommender", func(c *fiber.Ctx) error {
		tagsQuery := c.Query("tags")
		if tagsQuery == "" {
			return c.Status(400).SendString("Missing tags parameter")
		}

		searchTags := strings.Split(tagsQuery, ",")
		
		// Query to find products that match at least one of the provided tags
		query := `
			SELECT DISTINCT p.name 
			FROM products p 
			JOIN tags t ON p.id = t.product_id 
			WHERE t.tag IN (%s)`
		
		placeholders := make([]string, len(searchTags))
		args := make([]interface{}, len(searchTags))
		for i, tag := range searchTags {
			placeholders[i] = "?"
			args[i] = strings.TrimSpace(tag)
		}
		
		finalQuery := fmt.Sprintf(query, strings.Join(placeholders, ","))
		rows, err := db.Query(finalQuery, args...)
		if err != nil {
			return c.Status(500).SendString("Database error")
		}
		defer rows.Close()

		var results []string
		for rows.Next() {
			var name string
			if err := rows.Scan(&name); err == nil {
				results = append(results, name)
			}
		}

		// Generate HTML response
		var html strings.Builder
		html.WriteString("<html><body><h1>Recommended Products</h1><ul>")
		if len(results) == 0 {
			html.WriteString("<li>No products found matching those tags.</li>")
		} else {
			for _, name := range results {
				html.WriteString(fmt.Sprintf("<li>%s</li>", name))
			}
		}
		html.WriteString("</ul></body></html>")

		c.Set("Content-Type", "text/html")
		return c.SendString(html.String())
	})

	app.Post("/recommender", func(c *fiber.Ctx) error {
		p := new(Product)
		if err := c.BodyParser(p); err != nil {
			return c.Status(400).SendString("Invalid input")
		}

		if p.Name == "" || len(p.Tags) == 0 {
			return c.Status(400).SendString("Invalid input: product_name and tags are required")
		}

		tx, err := db.Begin()
		if err != nil {
			return c.Status(500).SendString("Database error")
		}

		res, err := tx.Exec("INSERT INTO products (name) VALUES (?)", p.Name)
		if err != nil {
			tx.Rollback()
			return c.Status(500).SendString("Database error")
		}

		productID, _ := res.LastInsertId()
		for _, tag := range p.Tags {
			_, err := tx.Exec("INSERT INTO tags (product_id, tag) VALUES (?, ?)", productID, strings.TrimSpace(tag))
			if err != nil {
				tx.Rollback()
				return c.Status(500).SendString("Database error")
			}
		}

		if err := tx.Commit(); err != nil {
			return c.Status(500).SendString("Database error")
		}

		return c.SendStatus(200)
	})

	log.Fatal(app.Listen("0.0.0.0:5000"))
}