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

var db *sql.DB

func initDB() {
	var err error
	db, err = sql.Open("sqlite3", "./db.sqlite3")
	if err != nil {
		log.Fatal(err)
	}

	// We store products in a table. Since properties are unstructured, 
	// we store the 'name' as a primary key and the rest of the object as a JSON string.
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

	r := gin.Default()

	// POST /add
	r.POST("/add", func(c *gin.Context) {
		var product map[string]string
		if err := c.ShouldBindJSON(&product); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid input"})
			return
		}

		name, ok := product["name"]
		if !ok || name == "" {
			c.JSON(http.StatusBadRequest, gin.H{"error": "name is required"})
			return
		}

		// Store the whole map as JSON in the data column
		jsonData, err := json.Marshal(product)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Internal server error"})
			return
		}

		_, err = db.Exec("INSERT OR REPLACE INTO products (name, data) VALUES (?, ?)", name, string(jsonData))
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

		var data string
		err := db.QueryRow("SELECT data FROM products WHERE name = ?", name).Scan(&data)
		if err == sql.ErrNoRows {
			c.JSON(http.StatusNotFound, gin.H{"error": "Product not found"})
			return
		} else if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
			return
		}

		c.JSON(http.StatusOK, gin.H{"data": data})
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

		if req.Name == "" || req.Data == "" {
			c.JSON(http.StatusBadRequest, gin.H{"error": "name and data are required"})
			return
		}

		// Validate that req.Data is actually a valid JSON object representing the product
		var check map[string]string
		if err := json.Unmarshal([]byte(req.Data), &check); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid data format"})
			return
		}

		_, err := db.Exec("INSERT OR REPLACE INTO products (name, data) VALUES (?, ?)", req.Name, req.Data)
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

		rows, err := db.Query("SELECT data FROM products")
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
			return
		}
		defer rows.Close()

		var results []map[string]string
		for rows.Next() {
			var dataStr string
			if err := rows.Scan(&dataStr); err != nil {
				continue
			}

			var product map[string]string
			if err := json.Unmarshal([]byte(dataStr), &product); err != nil {
				continue
			}

			// Search in all values of the map
			match := false
			for _, v := range product {
				if strings.Contains(strings.ToLower(v), strings.ToLower(query)) {
					match = true
					break
				}
			}

			if match {
				results = append(results, product)
			}
		}

		c.JSON(http.StatusOK, gin.H{"results": results})
	})

	// Use APP_SECRET if needed (though not explicitly required for these endpoints)
	_ = os.Getenv("APP_SECRET")

	r.Run("0.0.0.0:5000")
}