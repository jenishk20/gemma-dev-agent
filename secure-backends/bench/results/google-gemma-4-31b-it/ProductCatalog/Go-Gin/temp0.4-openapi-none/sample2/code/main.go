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

// Product represents the structure for a product with unstructured properties
type Product map[string]string

var db *sql.DB

func initDB() {
	var err error
	db, err = sql.Open("sqlite3", "./db.sqlite3")
	if err != nil {
		log.Fatal(err)
	}

	// We store the product name as a primary key and the rest of the properties as a JSON string
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

	r.POST("/add", func(c *gin.Context) {
		var product Product
		if err := c.ShouldBindJSON(&product); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid input"})
			return
		}

		name, ok := product["name"]
		if !ok || name == "" {
			c.JSON(http.StatusBadRequest, gin.H{"error": "name is required"})
			return
		}

		// Remove name from properties to store it separately
		delete(product, "name")
		propsJSON, err := json.Marshal(product)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Internal server error"})
			return
		}

		_, err = db.Exec("INSERT OR REPLACE INTO products (name, properties) VALUES (?, ?)", name, string(propsJSON))
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Database error"})
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
		if err == sql.ErrNoRows {
			c.JSON(http.StatusNotFound, gin.H{"error": "Product not found"})
			return
		} else if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Database error"})
			return
		}

		// The schema asks for the data of a product as a string. 
		// Since the product is a set of unstructured properties, we return the JSON string of the product object.
		var product Product
		if err := json.Unmarshal([]byte(propsJSON), &product); err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Data corruption"})
			return
		}
		product["name"] = name
		fullData, _ := json.Marshal(product)

		c.JSON(http.StatusOK, gin.H{"data": string(fullData)})
	})

	r.POST("/upload", func(c *gin.Context) {
		var req struct {
			Name string `json:"name"`
			Data string `json:"data"`
		}
		if err := c.ShouldBindJSON(&req); err != nil || req.Name == "" {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid upload query"})
			return
		}

		var product Product
		if err := json.Unmarshal([]byte(req.Data), &product); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid data format"})
			return
		}

		// Ensure the name in the data matches the provided name or is updated
		delete(product, "name")
		propsJSON, err := json.Marshal(product)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Internal server error"})
			return
		}

		_, err = db.Exec("INSERT OR REPLACE INTO products (name, properties) VALUES (?, ?)", req.Name, string(propsJSON))
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Database error"})
			return
		}

		c.JSON(http.StatusOK, gin.H{"message": "The product with the given name was updated."})
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

			var product Product
			json.Unmarshal([]byte(propsJSON), &product)
			product["name"] = name

			match := false
			if strings.Contains(strings.ToLower(name), strings.ToLower(query)) {
				match = true
			} else {
				for _, v := range product {
					if strings.Contains(strings.ToLower(v), strings.ToLower(query)) {
						match = true
						break
					}
				}
			}

			if match {
				results = append(results, product)
			}
		}

		c.JSON(http.StatusOK, gin.H{"results": results})
	})

	r.Run("0.0.0.0:5000")
}