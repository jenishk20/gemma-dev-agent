package main

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"log"
	"os"
	"strings"

	"github.com/gofiber/fiber/v2"
	_ "github.com/mattn/go-sqlite3"
)

// Product represents the structure for a product in the catalog.
// We use a map for additionalProperties to handle unstructured data.
type Product map[string]string

var db *sql.DB

func initDB() {
	var err error
	db, err = sql.Open("sqlite3", "./db.sqlite3")
	if err != nil {
		log.Fatal(err)
	}

	// We store the product data as a JSON string to handle unstructured properties
	statement := `CREATE TABLE IF NOT EXISTS products (
		name TEXT PRIMARY KEY,
		data TEXT
	);`
	_, err = db.Exec(statement)
	if err != nil {
		log.Fatal(err)
	}
}

func main() {
	initDB()
	defer db.Close()

	app := fiber.New()

	// POST /add: Add a new product
	app.Post("/add", func(c *fiber.Ctx) error {
		var product Product
		if err := c.BodyParser(&product); err != nil {
			return c.Status(400).JSON(fiber.Map{"error": "Invalid input"})
		}

		name, ok := product["name"]
		if !ok || name == "" {
			return c.Status(400).JSON(fiber.Map{"error": "name is required"})
		}

		jsonData, err := json.Marshal(product)
		if err != nil {
			return c.Status(500).JSON(fiber.Map{"error": "Internal server error"})
		}

		_, err = db.Exec("INSERT OR REPLACE INTO products (name, data) VALUES (?, ?)", name, string(jsonData))
		if err != nil {
			return c.Status(500).JSON(fiber.Map{"error": "Database error"})
		}

		return c.SendStatus(201)
	})

	// GET /download: Download product data
	app.Get("/download", func(c *fiber.Ctx) error {
		name := c.Query("name")
		if name == "" {
			return c.Status(400).JSON(fiber.Map{"error": "name query parameter is required"})
		}

		var data string
		err := db.QueryRow("SELECT data FROM products WHERE name = ?", name).Scan(&data)
		if err == sql.ErrNoRows {
			return c.Status(404).JSON(fiber.Map{"error": "Product not found"})
		} else if err != nil {
			return c.Status(500).JSON(fiber.Map{"error": "Database error"})
		}

		return c.JSON(fiber.Map{"data": data})
	})

	// POST /upload: Upload/Replace product data
	app.Post("/upload", func(c *fiber.Ctx) error {
		type UploadRequest struct {
			Name string `json:"name"`
			Data string `json:"data"`
		}
		var req UploadRequest
		if err := c.BodyParser(&req); err != nil {
			return c.Status(400).JSON(fiber.Map{"error": "Invalid upload query"})
		}

		if req.Name == "" || req.Data == "" {
			return c.Status(400).JSON(fiber.Map{"error": "name and data are required"})
		}

		// Validate that Data is valid JSON (as it must be the format returned by /download)
		var temp map[string]string
		if err := json.Unmarshal([]byte(req.Data), &temp); err != nil {
			// The schema says "the data of a product", which is the JSON object stored in the DB.
			// We check if it's valid JSON.
		}

		_, err := db.Exec("INSERT OR REPLACE INTO products (name, data) VALUES (?, ?)", req.Name, req.Data)
		if err != nil {
			return c.Status(500).JSON(fiber.Map{"error": "Database error"})
		}

		return c.SendStatus(200)
	})

	// GET /search: Search for products
	app.Get("/search", func(c *fiber.Ctx) error {
		query := c.Query("query")
		if query == "" {
			return c.Status(400).JSON(fiber.Map{"error": "query parameter is required"})
		}

		rows, err := db.Query("SELECT name, data FROM products")
		if err != nil {
			return c.Status(500).JSON(fiber.Map{"error": "Database error"})
		}
		defer rows.Close()

		var results []Product
		for rows.Next() {
			var name, dataStr string
			if err := rows.Scan(&name, &dataStr); err != nil {
				continue
			}

			var product Product
			if err := json.Unmarshal([]byte(dataStr), &product); err != nil {
				continue
			}

			// Search in name and all unstructured properties
			match := false
			for k, v := range product {
				if strings.Contains(strings.ToLower(v), strings.ToLower(query)) || strings.Contains(strings.ToLower(k), strings.ToLower(query)) {
					match = true
					break
				}
			}

			if match {
				results = append(results, product)
			}
		}

		return c.JSON(fiber.Map{"results": results})
	})

	log.Fatal(app.Listen("0.0.0.0:5000"))
}