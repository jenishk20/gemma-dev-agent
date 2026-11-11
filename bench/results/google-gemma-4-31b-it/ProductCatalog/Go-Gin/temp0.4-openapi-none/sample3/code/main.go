package main

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"strings"

	"github.com/gin-gonic/gin"
	_ "github.com/mattn/go-sqlite3"
)

type Product struct {
	Name       string            `json:"name"`
	Properties map[string]string `json:"-"`
}

// MarshalJSON customizes the JSON output to flatten the properties map into the root object
func (p Product) MarshalJSON() ([]byte, error) {
	m := make(map[string]interface{})
	m["name"] = p.Name
	for k, v := range p.Properties {
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

	// Create table to store product name and a JSON string of its unstructured properties
	statement := `CREATE TABLE IF NOT EXISTS products (
		name TEXT PRIMARY KEY, 
		properties TEXT
	);`
	_, err = db.Exec(statement)
	if err != nil {
		log.Fatal(err)
	}
}

func main() {
	initDB()
	defer db.Close()

	r := gin.Default()

	r.POST("/add", func(c *gin.Context) {
		var input map[string]string
		if err := c.ShouldBindJSON(&input); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid input"})
			return
		}

		name, ok := input["name"]
		if !ok || name == "" {
			c.JSON(http.StatusBadRequest, gin.H{"error": "name is required"})
			return
		}

		// Extract properties excluding the name
		props := make(map[string]string)
		for k, v := range input {
			if k != "name" {
				props[k] = v
			}
		}

		propsJSON, _ := json.Marshal(props)
		_, err := db.Exec("INSERT INTO products (name, properties) VALUES (?, ?)", name, string(propsJSON))
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Product already exists or database error"})
			return
		}

		c.Status(http.StatusCreated)
	})

	r.GET("/download", func(c *gin.Context) {
		name := c.Query("name")
		if name == "" {
			c.JSON(http.StatusBadRequest, gin.H{"error": "name query parameter is required"})
			return
		}

		var propsJSON string
		err := db.QueryRow("SELECT properties FROM products WHERE name = ?", name).Scan(&propsJSON)
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Product not found"})
			return
		}

		// The schema asks for a JSON object with a 'data' field containing the product data
		// Since the product data is unstructured, we return the properties JSON as the string value of 'data'
		c.JSON(http.StatusOK, gin.H{"data": propsJSON})
	})

	r.POST("/upload", func(c *gin.Context) {
		var input struct {
			Name string `json:"name"`
			Data string `json:"data"`
		}
		if err := c.ShouldBindJSON(&input); err != nil || input.Name == "" {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid upload query"})
			return
		}

		// Validate that Data is valid JSON
		var temp map[string]string
		if err := json.Unmarshal([]byte(input.Data), &temp); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid data format"})
			return
		}

		_, err := db.Exec("INSERT OR REPLACE INTO products (name, properties) VALUES (?, ?)", input.Name, input.Data)
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Database error"})
			return
		}

		c.JSON(http.StatusOK, gin.H{"message": "Product updated"})
	})

	r.GET("/search", func(c *gin.Context) {
		query := c.Query("query")
		if query == "" {
			c.JSON(http.StatusBadRequest, gin.H{"error": "query parameter is required"})
			return
		}

		rows, err := db.Query("SELECT name, properties FROM products")
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Database error"})
			return
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

			// Search in name or any property value
			match := false
			if strings.Contains(strings.ToLower(name), strings.ToLower(query)) {
				match = true
			} else {
				for _, v := range props {
					if strings.Contains(strings.ToLower(v), strings.ToLower(query)) {
						match = true
						break
					}
				}
			}

			if match {
				results = append(results, Product{Name: name, Properties: props})
			}
		}

		c.JSON(http.StatusOK, gin.H{"results": results})
	})

	r.Run("0.0.0.0:5000")
}