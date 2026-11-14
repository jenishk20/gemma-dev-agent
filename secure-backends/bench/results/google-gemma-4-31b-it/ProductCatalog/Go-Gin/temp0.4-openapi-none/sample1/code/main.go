package main

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"strings"

	"github.com/gin-gonic/gin"
	_ "github.com/mattn/go-sqlite3"
)

// Product represents the structure of a product in the catalog.
// We use a map for additionalProperties to handle unstructured data.
type Product map[string]string

var db *sql.DB

func initDB() {
	var err error
	db, err = sql.Open("sqlite3", "./db.sqlite3")
	if err != nil {
		log.Fatal(err)
	}

	// We store the product name as a primary key and the rest of the properties as a JSON string.
	sqlStmt := `
	CREATE TABLE IF NOT EXISTS products (
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

	r := gin.Default()

	// POST /add
	r.POST("/add", func(c *gin.Context) {
		var input Product
		if err := c.ShouldBindJSON(&input); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid input"})
			return
		}

		name, ok := input["name"]
		if !ok || name == "" {
			c.JSON(http.StatusBadRequest, gin.H{"error": "name is required"})
			return
		}

		// Separate name from properties for storage
		props := make(map[string]string)
		for k, v := range input {
			if k != "name" {
				props[k] = v
			}
		}

		propsJSON, err := json.Marshal(props)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Internal server error"})
			return
		}

		_, err = db.Exec("INSERT OR REPLACE INTO products (name, properties) VALUES (?, ?)", name, string(propsJSON))
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
			return
		}

		c.Status(http.StatusCreated)
	})

	// GET /download
	r.GET("/download", func(c *gin.Context) {
		name := c.Query("name")
		if name == "" {
			c.JSON(http.StatusBadRequest, gin.H{"error": "name query parameter is required"})
			return
		}

		var propsJSON string
		err := db.QueryRow("SELECT properties FROM products WHERE name = ?", name).Scan(&propsJSON)
		if err == sql.ErrNoRows {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Product not found"})
			return
		} else if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
			return
		}

		// The schema asks for the "data" of the product. 
		// Since the product is a set of properties, we return the JSON representation of the full product.
		var props map[string]string
		json.Unmarshal([]byte(propsJSON), &props)
		
		fullProduct := make(map[string]string)
		fullProduct["name"] = name
		for k, v := range props {
			fullProduct[k] = v
		}
		
		finalData, _ := json.Marshal(fullProduct)
		c.JSON(http.StatusOK, gin.H{"data": string(finalData)})
	})

	// POST /upload
	r.POST("/upload", func(c *gin.Context) {
		var req struct {
			Name string `json:"name"`
			Data string `json:"data"`
		}
		if err := c.ShouldBindJSON(&req); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid upload query"})
			return
		}

		var fullProduct map[string]string
		if err := json.Unmarshal([]byte(req.Data), &fullProduct); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid data format"})
			return
		}

		// Ensure the name in the data matches the name provided in the request
		if fullProduct["name"] != req.Name {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Name mismatch between field and data"})
			return
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
			c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
			return
		}

		c.JSON(http.StatusOK, gin.H{"message": "Product updated"})
	})

	// GET /search
	r.GET("/search", func(c *gin.Context) {
		query := c.Query("query")
		if query == "" {
			c.JSON(http.StatusBadRequest, gin.H{"error": "query parameter is required"})
			return
		}

		rows, err := db.Query("SELECT name, properties FROM products")
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
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
				p := make(Product)
				p["name"] = name
				for k, v := range props {
					p[k] = v
				}
				results = append(results, p)
			}
		}

		c.JSON(http.StatusOK, gin.H{"results": results})
	})

	r.Run("0.0.0.0:5000")
}