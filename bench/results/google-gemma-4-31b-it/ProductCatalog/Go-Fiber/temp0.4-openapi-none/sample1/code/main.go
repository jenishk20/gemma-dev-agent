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

var db *sql.DB

func main() {
	var err error
	db, err = sql.Open("sqlite3", "./db.sqlite3")
	if err != nil {
		log.Fatal(err)
	}
	defer db.Close()

	// Create table to store product name and a JSON string of its properties
	statement := `CREATE TABLE IF NOT EXISTS products (name TEXT PRIMARY KEY, properties TEXT);`
	_, err = db.Exec(statement)
	if err != nil {
		log.Fatal(err)
	}

	app := fiber.New()

	// POST /add: Add a new product
	app.Post("/add", func(c *fiber.Ctx) error {
		var product map[string]string
		if err := c.BodyParser(&product); err != nil {
			return c.Status(400).JSON(fiber.Map{"error": "Invalid input"})
		}

		name, ok := product["name"]
		if !ok || name == "" {
			return c.Status(400).JSON(fiber.Map{"error": "name is required"})
		}

		// Store the entire map as a JSON string in the properties column
		propsJSON, err := json.Marshal(product)
		if err != nil {
			return c.Status(500).JSON(fiber.Map{"error": "Internal server error"})
		}

		_, err = db.Exec("INSERT OR REPLACE INTO products (name, properties) VALUES (?, ?)", name, string(propsJSON))
		if err != nil {
			return c.Status(500).JSON(fiber.Map{"error": err.Error()})
		}

		return c.SendStatus(201)
	})

	// GET /download: Download product data
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

		return c.JSON(fiber.Map{"data": propsJSON})
	})

	// POST /upload: Replace product data
	app.Post("/upload", func(c *fiber.Ctx) error {
		type UploadRequest struct {
			Name string `json:"name"`
			Data string `json:"data"`
		}
		var req UploadRequest
		if err := c.BodyParser(&req); err != nil || req.Name == "" || req.Data == "" {
			return c.Status(400).JSON(fiber.Map{"error": "Invalid upload query"})
		}

		// Validate that Data is valid JSON
		var check map[string]interface{}
		if err := json.Unmarshal([]byte(req.Data), &check); err != nil {
			return c.Status(400).JSON(fiber.Map{"error": "Data must be a valid JSON string"})
		}

		_, err := db.Exec("INSERT OR REPLACE INTO products (name, properties) VALUES (?, ?)", req.Name, req.Data)
		if err != nil {
			return c.Status(500).JSON(fiber.Map{"error": err.Error()})
		}

		return c.Status(200).JSON(fiber.Map{"message": "Product updated"})
	})

	// GET /search: Search for products
	app.Get("/search", func(c *fiber.Ctx) error {
		query := c.Query("query")
		if query == "" {
			return c.Status(400).JSON(fiber.Map{"error": "query parameter is required"})
		}

		rows, err := db.Query("SELECT properties FROM products")
		if err != nil {
			return c.Status(500).JSON(fiber.Map{"error": err.Error()})
		}
		defer rows.Close()

		var results []map[string]string
		for rows.Next() {
			var propsJSON string
			if err := rows.Scan(&propsJSON); err != nil {
				continue
			}

			var product map[string]string
			if err := json.Unmarshal([]byte(propsJSON), &product); err != nil {
				continue
			}

			// Search in name or any property value
			match := false
			for k, v := range product {
				if strings.Contains(strings.ToLower(k), strings.ToLower(query)) || 
				   strings.Contains(strings.ToLower(v), strings.ToLower(query)) {
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

	log.Println("Server starting on 0.0.0.0:5000")
	log.Fatal(app.Listen("0.0.0.0:5000"))
}