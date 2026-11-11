package main

import (
	"database/sql"
	"fmt"
	"html/template"
	"log"
	"net/http"
	"strings"

	"github.com/gin-gonic/gin"
	_ "github.com/mattn/go-sqlite3"
)

type Product struct {
	ID   int
	Name string
	Tags string
}

var db *sql.DB

func initDB() {
	var err error
	db, err = sql.Open("sqlite3", "./db.sqlite3")
	if err != nil {
		log.Fatal(err)
	}

	sqlStmt := `
	CREATE TABLE IF NOT EXISTS products (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		product_name TEXT NOT NULL,
		tags TEXT NOT NULL
	);
	`
	_, err = db.Exec(sqlStmt)
	if err != nil {
		log.Fatalf("%v", err)
	}
}

type ProductRequest struct {
	ProductName string   `json:"product_name" binding:"required"`
	Tags        []string `json:"tags" binding:"required"`
}

func main() {
	initDB()
	defer db.Close()

	r := gin.Default()

	// HTML Template for recommendations
	tmpl := template.New("recommender")
	tmpl = template.Must(tmpl.Parse(`
		<!DOCTYPE html>
		<html>
		<head><title>Recommendations</title></head>
		<body>
			<h1>Recommended Products</h1>
			<ul>
				{{range .}}
				<li>{{.Name}} (Tags: {{.Tags}})</li>
				{{else}}
				<li>No products found matching those tags.</li>
				{{end}}
			</ul>
		</body>
		</html>
	`))

	r.GET("/recommender", func(c *gin.Context) {
		tagsQuery := c.Query("tags")
		if tagsQuery == "" {
			c.String(http.StatusBadRequest, "Missing tags parameter")
			return
		}

		searchTags := strings.Split(tagsQuery, ",")
		var results []Product

		for _, tag := range searchTags {
			tag = strings.TrimSpace(tag)
			rows, err := db.Query("SELECT id, product_name, tags FROM products WHERE tags LIKE ?", "%"+tag+"%")
			if err != nil {
				c.String(http.StatusInternalServerError, "Database error")
				return
			}

			for rows.Next() {
				var p Product
				if err := rows.Scan(&p.ID, &p.Name, &p.Tags); err != nil {
					continue
				}
				// Avoid duplicates if a product matches multiple tags
				exists := false
				for _, existing := range results {
					if existing.ID == p.ID {
						exists = true
						break
					}
				}
				if !exists {
					results = append(results, p)
				}
			}
			rows.Close()
		}

		c.Header("Content-Type", "text/html")
		err := tmpl.Execute(c.Writer, results)
		if err != nil {
			c.String(http.StatusInternalServerError, "Template error")
		}
	})

	r.POST("/recommender", func(c *gin.Context) {
		var req ProductRequest
		if err := c.ShouldBindJSON(&req); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid input"})
			return
		}

		tagsString := strings.Join(req.Tags, ",")
		_, err := db.Exec("INSERT INTO products (product_name, tags) VALUES (?, ?)", req.ProductName, tagsString)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Database error"})
			return
		}

		c.JSON(http.StatusOK, gin.H{"status": "Successful operation"})
	})

	r.Run("0.0.0.0:5000")
}