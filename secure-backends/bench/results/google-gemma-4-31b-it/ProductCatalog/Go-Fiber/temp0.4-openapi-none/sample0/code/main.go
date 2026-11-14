package main

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"log"
	"strings"

	"github.com/gofiber/fiber/v2"
	_ "github.com/mattn/go-sqlite3"
)

type Product struct {
	Name string `json:"name"`
	// Use a map to handle additional unstructured properties
	Properties map[string]string `json:"-"`
}

// MarshalJSON allows us to flatten the map into the top-level JSON object
func (p Product) MarshalJSON() ([]byte, error) {
	m := make(map[string]string)
	m["name"] = p.Name
	for k, v := range p.Properties {
		m[k] = v
	}
	return json.Marshal(m)
}

func main() {
	db, err := sql.Open("sqlite3", "./db.sqlite3")
	if err != nil {
		log.Fatal(err)
	}
	defer db.Close()

	// Create table: name is primary key, properties stored as JSON string
	_, err = db.Exec(`CREATE TABLE IF NOT EXISTS products (
		name TEXT PRIMARY KEY, 
		properties TEXT
	)`)
	if err != nil {
		log.Fatal(err)
	}

	app := fiber.New()

	// POST /add: Add a new product
	app.Post("/add", func(c *fiber.Ctx) error {
		var input map[string]string
		if err := c.BodyParser(&input); err != nil {
			return c.Status(400).SendString("Invalid input")
		}

		name, ok := input["name"]
		if !ok || name == "" {
			return c.Status(400).SendString("Missing required field: name")
		}

		// Separate name from additional properties
		props := make(map[string]string)
		for k, v := range input {
			if k != "name" {
				props[k] = v
			}
		}

		propsJSON, _ := json.Marshal(props)
		_, err := db.Exec("INSERT INTO products (name, properties) VALUES (?, ?)", name, string(propsJSON))
		if err != nil {
			return c.Status(400).SendString("Product already exists or database error")
		}

		return c.SendStatus(201)
	})

	// GET /download: Download product data
	app.Get("/download", func(c *fiber.Ctx) error {
		name := c.Query("name")
		if name == "" {
			return c.Status(400).SendString("Missing required query parameter: name")
		}

		var propsJSON string
		err := db.QueryRow("SELECT properties FROM products WHERE name = ?", name).Scan(&propsJSON)
		if err != nil {
			return c.Status(400).SendString("Product not found")
		}

		// The schema asks for a response with a 'data' field containing the product data
		// We return the properties JSON as the data string
		return c.JSON(fiber.Map{
			"data": propsJSON,
		})
	})

	// POST /upload: Replace product data
	app.Post("/upload", func(c *fiber.Ctx) error {
		var input struct {
			Name string `json:"name"`
			Data string `json:"data"`
		}
		if err := c.BodyParser(&input); err != nil || input.Name == "" || input.Data == "" {
			return c.Status(400).SendString("Invalid upload query")
		}

		// Validate that Data is valid JSON
		var temp map[string]string
		if err := json.Unmarshal([]byte(input.Data), &temp); err != nil {
			return c.Status(400).SendString("Invalid data format")
		}

		_, err := db.Exec("UPDATE products SET properties = ? WHERE name = ?", input.Data, input.Name)
		if err != nil {
			return c.Status(400).SendString("Database error")
		}

		return c.SendStatus(200)
	})

	// GET /search: Search products by name or any property
	app.Get("/search", func(c *fiber.Ctx) error {
		query := c.Query("query")
		if query == "" {
			return c.Status(400).SendString("Missing required query parameter: query")
		}

		rows, err := db.Query("SELECT name, properties FROM products")
		if err != nil {
			return c.Status(500).SendString("Database error")
		}
		defer rows.Close()

		var results []Product
		searchTerm := strings.ToLower(query)

		for rows.Next() {
			var name, propsJSON string
			if err := rows.Scan(&name, &propsJSON); err != nil {
				continue
			}

			var props map[string]string
			json.Unmarshal([]byte(propsJSON), &props)

			match := false
			if strings.Contains(strings.ToLower(name), searchTerm) {
				match = true
			} else {
				for k, v := range props {
					if strings.Contains(strings.ToLower(k), searchTerm) || strings.Contains(strings.ToLower(v), searchTerm) {
						match = true
						break
					}
				}
			}

			if match {
				results = append(results, Product{Name: name, Properties: props})
			}
		}

		return c.JSON(fiber.Map{
			"results": results,
		})
	})

	log.Fatal(app.Listen("0.0.0.0:5000"))
}