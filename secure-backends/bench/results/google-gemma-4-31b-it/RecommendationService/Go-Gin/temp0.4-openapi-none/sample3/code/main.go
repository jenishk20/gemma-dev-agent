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
	CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT);
	CREATE TABLE IF NOT EXISTS tags (id INTEGER PRIMARY KEY AUTOINCREMENT, product_id INTEGER, tag TEXT);
	CREATE INDEX IF NOT EXISTS idx_tags_tag ON tags(tag);
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
		
		query := `
			SELECT DISTINCT p.id, p.name 
			FROM products p 
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
			var id int
			var name string
			if err := rows.Scan(&id, &name); err != nil {
				continue
			}
			found = true
			htmlBuilder.WriteString(fmt.Sprintf("<li>%s</li>", name))
		}
		htmlBuilder.WriteString("</ul></body></html>")

		if !found {
			c.Header("Content-Type", "text/html")
			c.String(http.StatusOK, "<html><body><h1>Recommended Products</h1><p>No products found matching the tags.</p></body></html>")
			return
		}

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
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Database error"})
			return
		}

		res, err := tx.Exec("INSERT INTO products (name) VALUES (?)", req.ProductName)
		if err != nil {
			tx.Rollback()
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Database error"})
			return
		}

		productID, _ := res.LastInsertId()
		for _, tag := range req.Tags {
			_, err = tx.Exec("INSERT INTO tags (product_id, tag) VALUES (?, ?)", productID, strings.TrimSpace(tag))
			if err != nil {
				tx.Rollback()
				c.JSON(http.StatusInternalServerError, gin.H{"error": "Database error"})
				return
			}
		}

		if err := tx.Commit(); err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Database error"})
			return
		}

		c.JSON(http.StatusOK, gin.H{"status": "Successful operation"})
	})

	r.Run("0.0.0.0:5000")
}