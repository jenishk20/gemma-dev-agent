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

type Product struct {
	Name       string            `json:"name"`
	Properties map[string]string `json:"-"` // Used for internal DB handling
}

// Custom MarshalJSON to flatten the map into the product object as per OpenAPI
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
	db, err = sql.Open("sqlite3", "db.sqlite3")
	if err != nil {
		log.Fatal(err)
	}

	// We store the product name and a JSON string of its properties
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

		// Separate name from additional properties
		props := make(map[string]string)
		for k, v := range input {
			if k != "name" {
				props[k] = v
			}
		}

		propsJSON, _ := json.Marshal(props)
		_, err := db.Exec("INSERT OR REPLACE INTO products (name, properties) VALUES (?, ?)", name, string(propsJSON))
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
			c.JSON(http.StatusNotFound, gin.H{"error": "Product not found"})
			return
		} else if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
			return
		}

		// The schema asks for the data of the product. 
		// Since /upload expects the format returned by /download, we return the JSON string of properties.
		c.JSON(http.StatusOK, gin.H{"data": propsJSON})
	})

	// POST /upload
	r.POST("/upload", func(c *gin.Context) {
		var req struct {
			Name string `json:"name"`
			Data string `json:"data"`
		}
		if err := c.ShouldBindJSON(&req); err != nil || req.Name == "" {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid upload query"})
			return
		}

		// Validate that Data is valid JSON
		var temp map[string]string
		if err := json.Unmarshal([]byte(req.Data), &temp); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid data format"})
			return
		}

		_, err := db.Exec("INSERT OR REPLACE INTO products (name, properties) VALUES (?, ?)", req.Name, req.Data)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
			return
		}

		c.JSON(http.StatusOK, gin.H{"message": "The product with the given name was updated."})
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

			// Search in name or any property value
			match := strings.Contains(strings.ToLower(name), strings.ToLower(query))
			if !match {
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