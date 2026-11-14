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
		tag TEXT,
		FOREIGN KEY(product_id) REFERENCES products(id)
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

	r.GET("/recommender", func(c *gin.Context) {
		tagsQuery := c.Query("tags")
		if tagsQuery == "" {
			c.String(http.StatusBadRequest, "Missing tags parameter")
			return
		}

		searchTags := strings.Split(tagsQuery, ",")
		
		// Query to find products that have at least one of the provided tags
		query := `SELECT DISTINCT p.id, p.name FROM products p 
				  JOIN tags t ON p.id = t.product_id 
				  WHERE t.tag IN (`
		
		placeholders := make([]string, len(searchTags))
		args := make([]interface{}, len(searchTags))
		for i, tag := range searchTags {
			placeholders[i] = "?"
			args[i] = strings.TrimSpace(tag)
		}
		query += strings.Join(placeholders, ",") + ")"

		rows, err := db.Query(query, args...)
		if err != nil {
			c.String(http.StatusInternalServerError, "Database error")
			return
		}
		defer rows.Close()

		var htmlBuilder strings.Builder
		htmlBuilder.WriteString("<html><body><h1>Recommended Products</h1><ul>")
		
		found := false
		for rows.Next() {
			found = true
			var id int
			var name string
			if err := rows.Scan(&id, &name); err != nil {
				continue
			}
			htmlBuilder.WriteString(fmt.Sprintf("<li>%s (ID: %d)</li>", name, id))
		}
		
		if !found {
			htmlBuilder.WriteString("<li>No products found matching those tags.</li>")
		}
		
		htmlBuilder.WriteString("</ul></body></html>")
		c.Header("Content-Type", "text/html")
		c.String(http.StatusOK, htmlBuilder.String())
	})

	r.POST("/recommender", func(c *gin.Context) {
		var req ProductRequest
		if err := c.ShouldBindJSON(&req); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid input"})
			return
		}

		tx, err := db.Begin()
		if err != nil {
			c.String(http.StatusInternalServerError, "Database error")
			return
		}

		res, err := tx.Exec("INSERT INTO products (name) VALUES (?)", req.ProductName)
		if err != nil {
			tx.Rollback()
			c.String(http.StatusInternalServerError, "Database error")
			return
		}

		productID, _ := res.LastInsertId()
		for _, tag := range req.Tags {
			_, err = tx.Exec("INSERT INTO tags (product_id, tag) VALUES (?, ?)", productID, strings.TrimSpace(tag))
			if err != nil {
				tx.Rollback()
				c.String(http.StatusInternalServerError, "Database error")
				return
			}
		}

		if err := tx.Commit(); err != nil {
			c.String(http.StatusInternalServerError, "Database error")
			return
		}

		c.Status(http.StatusOK)
	})

	r.Run("0.0.0.0:5000")
}