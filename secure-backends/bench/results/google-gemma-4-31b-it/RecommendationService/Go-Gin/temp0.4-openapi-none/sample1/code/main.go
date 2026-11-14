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
	Name string   `json:"product_name" binding:"required"`
	Tags []string `json:"tags" binding:"required"`
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
		
		// Query to find products that match at least one of the tags
		query := `
			SELECT DISTINCT p.name 
			FROM products p 
			JOIN tags t ON p.id = t.product_id 
			WHERE t.tag IN (`
		
		placeholders := make([]string, len(searchTags))
		args := make([]interface{}, len(searchTags))
		for i, tag := range searchTags {
			placeholders[i] = "?"
			args[i] = strings.TrimSpace(tag)
		}
		query += strings.Join(placeholders, ",") + `);`

		rows, err := db.Query(query, args...)
		if err != nil {
			c.String(http.StatusInternalServerError, "Database error")
			return
		}
		defer rows.Close()

		var results []string
		for rows.Next() {
			var name string
			if err := rows.Scan(&name); err == nil {
				results = append(results, name)
			}
		}

		var htmlBuilder strings.Builder
		htmlBuilder.WriteString("<html><body>")
		if len(results) == 0 {
			htmlBuilder.WriteString("<p>No products found matching those tags.</p>")
		} else {
			htmlBuilder.WriteString("<h1>Recommended Products</h1><ul>")
			for _, name := range results {
				htmlBuilder.WriteString(fmt.Sprintf("<li>%s</li>", name))
			}
			htmlBuilder.WriteString("</ul>")
		}
		htmlBuilder.WriteString("</body></html>")

		c.Header("Content-Type", "text/html")
		c.String(http.StatusOK, htmlBuilder.String())
	})

	r.POST("/recommender", func(c *gin.Context) {
		var prod Product
		if err := c.ShouldBindJSON(&prod); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid input"})
			return
		}

		tx, err := db.Begin()
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Transaction error"})
			return
		}

		res, err := tx.Exec("INSERT INTO products (name) VALUES (?)", prod.Name)
		if err != nil {
			tx.Rollback()
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Insert product error"})
			return
		}

		productID, _ := res.LastInsertId()
		for _, tag := range prod.Tags {
			_, err := tx.Exec("INSERT INTO tags (product_id, tag) VALUES (?, ?)", productID, strings.TrimSpace(tag))
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