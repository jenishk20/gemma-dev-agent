package main

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"log"
	"os"

	"github.com/gofiber/fiber/v2"
	_ "github.com/mattn/go-sqlite3"
)

type Product struct {
	Name       string            `json:"name"`
	Properties map[string]string `json:"-"` // Used for internal logic
}

// Custom MarshalJSON to flatten the map into the product object for the API
func (p Product) MarshalJSON() ([]byte, error) {
	type Alias Product
	out := make(map[string]interface{})
	out["name"] = p.Name
	for k, v := range p.Properties {
		out[k] = v
	}
	return json.Marshal(out)
}

var db *sql.DB

func initDB() {
	var err error
	db, err = sql.Open("sqlite3", "./db.sqlite3")
	if err != nil {
		log.Fatal(err)
	}

	// We store unstructured properties as a JSON string in a TEXT column
	sqlStmt := `CREATE TABLE IF NOT EXISTS products (name TEXT PRIMARY KEY, properties TEXT);`
	_, err = db.Exec(sqlStmt)
	if err != nil {
		log.Fatal(err)
	}
}

func main() {
	initDB()
	defer db.Close()

	app := fiber.New()

	// POST /add
	app.Post("/add", func(c *fiber.Ctx) error {
		var body map[string]string
		if err := c.BodyParser(&body); err != nil {
			return c.Status(400).JSON(fiber.Map{"error": "Invalid input"})
		}

		name, ok := body["name"]
		if !ok || name == "" {
			return c.Status(400).JSON(fiber.Map{"error": "name is required"})
		}

		// Extract additional properties
		props := make(map[string]string)
		for k, v := range body {
			if k != "name" {
				props[k] = v
			}
		}

		propsJSON, _ := json.Marshal(props)
		_, err := db.Exec("INSERT OR REPLACE INTO products (name, properties) VALUES (?, ?)", name, string(propsJSON))
		if err != nil {
			return c.Status(500).JSON(fiber.Map{"error": err.Error()})
		}

		return c.SendStatus(201)
	})

	// GET /download
	app.Get("/download", func(c *fiber.Ctx) error {
		name := c.Query("name")
		if name == "" {
			return c.Status(400).JSON(fiber.Map{"error": "name query parameter is required"})
		}

		var propsJSON string
		err := db.QueryRow("SELECT properties FROM products WHERE name = ?", name).Scan(&propsJSON)
		if err == sql.ErrNoRows {
			return c.Status(404).JSON(fiber.Map{"error": "Product not found"})
		} else if err != nil {
			return c.Status(500).JSON(fiber.Map{"error": err.Error()})
		}

		// The schema says /download returns an object with a 'data' field containing the product data
		// We return the JSON representation of the product as a string in the 'data' field
		var props map[string]string
		json.Unmarshal([]byte(propsJSON), &props)
		
		fullProduct := make(map[string]string)
		fullProduct["name"] = name
		for k, v := range props {
			fullProduct[k] = v
		}
		
		productBytes, _ := json.Marshal(fullProduct)
		return c.JSON(fiber.Map{"data": string(productBytes)})
	})

	// POST /upload
	app.Post("/upload", func(c *fiber.Ctx) error {
		type UploadRequest struct {
			Name string `json:"name"`
			Data string `json:"data"`
		}
		var req UploadRequest
		if err := c.BodyParser(&req); err != nil || req.Name == "" || req.Data == "" {
			return c.Status(400).JSON(fiber.Map{"error": "Invalid upload query"})
		}

		// Parse the data string to extract properties (excluding name)
		var productData map[string]string
		if err := json.Unmarshal([]byte(req.Data), &productData); err != nil {
			return c.Status(400).JSON(fiber.Map{"error": "Invalid data format"})
		}

		props := make(map[string]string)
		for k, v := range productData {
			if k != "name" {
				props[k] = v
			}
		}

		propsJSON, _ := json.Marshal(props)
		_, err := db.Exec("INSERT OR REPLACE INTO products (name, properties) VALUES (?, ?)", req.Name, string(propsJSON))
		if err != nil {
			return c.Status(500).JSON(fiber.Map{"error": err.Error()})
		}

		return c.SendStatus(200)
	})

	// GET /search
	app.Get("/search", func(c *fiber.Ctx) error {
		query := c.Query("query")
		if query == "" {
			return c.Status(400).JSON(fiber.Map{"error": "query parameter is required"})
		}

		rows, err := db.Query("SELECT name, properties FROM products")
		if err != nil {
			return c.Status(500).JSON(fiber.Map{"error": err.Error()})
		}
		defer rows.Close()

		var results []Product
		for rows.Next() {
			var name, propsJSON string
			if err := rows.Scan(&name, &propsJSON); err != nil {
				continue
			}

			var props map[string]string
			json.Unmarshal([]byte(propsJSON), &props)

			// Search in name or any property
			match := (name == query) // Simple exact match as per common interpretation, or contains
			// The prompt says "Matches its name or any other property"
			// Let's use a simple case-insensitive contains check for better usability
			if !match {
				// Check name
				if fmt.Sprintf("%s", name) == query { match = true }
				// Check properties
				for _, v := range props {
					if v == query {
						match = true
						break
					}
				}
			}
			// Re-evaluating "Matches": usually implies contains or equals. Let's stick to equality for strictness or contains for flexibility.
			// Given "search query", contains is usually expected.
			// But to be safe and simple:
			match = false
			if name == query { match = true }
			for _, v := range props {
				if v == query { match = true; break }
			}

			if match {
				results = append(results, Product{Name: name, Properties: props})
			}
		}

		return c.JSON(fiber.Map{"results": results})
	})

	log.Fatal(app.Listen("0.0.0.0:5000"))
}