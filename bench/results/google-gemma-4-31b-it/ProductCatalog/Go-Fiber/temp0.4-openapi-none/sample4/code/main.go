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
	Name string            `json:"name"`
	Data map[string]string `json:"-"` // Internal use for DB
}

// Custom JSON marshaling to flatten the map into the product object
func (p Product) MarshalJSON() ([]byte, error) {
	m := make(map[string]interface{})
	m["name"] = p.Name
	for k, v := range p.Data {
		m[k] = v
	}
	return json.Marshal(m)
}

var db *sql.DB

func initDB() {
	var err error
	db, err = sql.Open("sqlite3", "./db.sqlite3")
	if err != nil {
		log.Fatal(err)
	}

	// Create table to store product name and a JSON string of its properties
	sqlStmt := `CREATE TABLE IF NOT EXISTS products (
		name TEXT PRIMARY KEY, 
		properties TEXT
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

		// Remove name from properties to avoid duplication in the JSON blob
		props := make(map[string]string)
		for k, v := range body {
			if k != "name" {
				props[k] = v
			}
		}

		propsJSON, _ := json.Marshal(props)
		_, err := db.Exec("INSERT OR REPLACE INTO products (name, properties) VALUES (?, ?)", name, string(propsJSON))
		if err != nil {
			return c.Status(500).JSON(fiber.Map{"error": "Database error"})
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
			return c.Status(500).JSON(fiber.Map{"error": "Database error"})
		}

		// The schema requires a response with a "data" field containing the product info
		// We return the full object (name + props) as a stringified JSON inside "data"
		var propsMap map[string]string
		json.Unmarshal([]byte(propsJSON), &propsMap)
		
		fullProduct := make(map[string]string)
		fullProduct["name"] = name
		for k, v := range propsMap {
			fullProduct[k] = v
		}
		
		fullProductJSON, _ := json.Marshal(fullProduct)
		return c.JSON(fiber.Map{"data": string(fullProductJSON)})
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
		var fullProduct map[string]string
		if err := json.Unmarshal([]byte(req.Data), &fullProduct); err != nil {
			return c.Status(400).JSON(fiber.Map{"error": "Invalid data format"})
		}

		props := make(map[string]string)
		for k, v := range fullProduct {
			if k != "name" {
				props[k] = v
			}
		}

		propsJSON, _ := json.Marshal(props)
		_, err := db.Exec("INSERT OR REPLACE INTO products (name, properties) VALUES (?, ?)", req.Name, string(propsJSON))
		if err != nil {
			return c.Status(500).JSON(fiber.Map{"error": "Database error"})
		}

		return c.Status(200).JSON(fiber.Map{"message": "Product updated"})
	})

	// GET /search
	app.Get("/search", func(c *fiber.Ctx) error {
		query := c.Query("query")
		if query == "" {
			return c.Status(400).JSON(fiber.Map{"error": "query parameter is required"})
		}

		// SQLite search: name matches OR properties JSON contains the query string
		rows, err := db.Query("SELECT name, properties FROM products WHERE name LIKE ? OR properties LIKE ?", "%"+query+"%", "%"+query+"%")
		if err != nil {
			return c.Status(500).JSON(fiber.Map{"error": "Database error"})
		}
		defer rows.Close()

		var results []Product
		for rows.Next() {
			var name, propsJSON string
			if err := rows.Scan(&name, &propsJSON); err != nil {
				continue
			}
			var propsMap map[string]string
			json.Unmarshal([]byte(propsJSON), &propsMap)
			results = append(results, Product{Name: name, Data: propsMap})
		}

		return c.JSON(fiber.Map{"results": results})
	})

	log.Fatal(app.Listen("0.0.0.0:5000"))
}