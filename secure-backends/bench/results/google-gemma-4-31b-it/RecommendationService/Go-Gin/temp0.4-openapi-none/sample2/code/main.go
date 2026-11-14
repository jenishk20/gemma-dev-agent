package main

import (
	"database/sql"
	"fmt"
	"log"
	"net/http"
	"strings"

	"github.com/gin-gonic/gin"
	_ "github.com/mattn/go-sqlite3"
)

type Product struct {
	ID   int      `json:"id"`
	Name string   `json:"product_name"`
	Tags []string `json:"tags"`
}

type ProductRequest struct {
	ProductName string   `json:"product_name" binding:"required"`
	Tags        []string `json:"tags" binding:"required"`
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
		name TEXT NOT NULL
	);
	CREATE TABLE IF NOT EXISTS tags (
		product_id INTEGER,
		tag TEXT NOT NULL,
		FOREIGN KEY(product_id) REFERENCES products(id)
	);
	`
	_, err = db.Exec(sqlStmt)
	if err != nil {
		log.Fatal(err)
	}
}

func main() {
	initDB()
	defer db.Close()

	r := gin.Default()

	r.GET("/recommender", func(c *gin.Context) {
		tagsQuery := c.Query("tags")
		if tagsQuery == "" {
			c.String(http.StatusBadRequest, "Missing tags parameter")
			return
		}

		searchTags := strings.Split(tagsQuery, ",")
		
		// Query to find products that match at least one of the provided tags
		query := `
			SELECT DISTINCT p.name 
			FROM products p 
			JOIN tags t ON p.id = t.product_id 
			WHERE t.tag IN (%s)`
		
		placeholders := make([]string, len(searchTags))
		args := make([]interface{}, len(searchTags))
		for i, tag := range searchTags {
			placeholders[i] = "?"
			args[i] = strings.TrimSpace(tag)
		}

		finalQuery := fmt.Sprintf(query, strings.Join(placeholders, ","))
		rows, err := db.Query(finalQuery, args...)
		if err != nil {
			c.String(http.StatusInternalServerError, "Database error")
			return
		}
		defer rows.Close()

		var products []string
		for rows.Next() {
			var name string
			if err := rows.Scan(&name); err == nil {
				products = append(products, name)
			}
		}

		// Generate HTML response
		var html strings.Builder
		html.WriteString("<html><body><h1>Recommended Products</h1><ul>")
		if len(products) == 0 {
			html.WriteString("<li>No products found matching these tags.</li>")
		} else {
			for _, p := range products {
				html.WriteString(fmt.Sprintf("<li>%s</li>", p))
			}
		}
		html.WriteString("</ul></body></html>")

		c.Header("Content-Type", "text/html")
		c.String(http.StatusOK, html.String())
	})

	r.POST("/recommender", func(c *gin.Context) {
		var req ProductRequest
		if err := c.ShouldBindJSON(&req); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid input"})
			return
		}

		tx, err := db.Begin()
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Transaction error"})
			return
		}

		res, err := tx.Exec("INSERT INTO products (name) VALUES (?)", req.ProductName)
		if err != nil {
			tx.Rollback()
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Insert product error"})
			return
		}

		id, _ := res.LastInsertId()
		for _, tag := range req.Tags {
			_, err = tx.Exec("INSERT INTO tags (product_id, tag) VALUES (?, ?)", id, strings.TrimSpace(tag))
			if err != nil {
				tx.Rollback()
				c.JSON(http.StatusInternalServerError, gin.H{"error": "Insert tag error"})
				return
			}
		}

		if err := tx.Commit(); err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Commit error"})
			return
		}

		c.JSON(http.StatusOK, gin.H{"status": "Successful operation"})
	})

	r.Run("0.0.0.0:5000")
}