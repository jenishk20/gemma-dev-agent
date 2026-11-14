package main

import (
	"database/sql"
	"fmt"
	"log"
	"net/http"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	_ "github.com/mattn/go-sqlite3"
)

type Click struct {
	ID        string    `json:"id"`
	Timestamp time.Time `json:"timestamp"`
}

var db *sql.DB

func initDB() {
	var err error
	db, err = sql.Open("sqlite3", "./db.sqlite3")
	if err != nil {
		log.Fatal(err)
	}

	sqlStmt := `
	CREATE TABLE IF NOT EXISTS clicks (
		id TEXT PRIMARY KEY,
		timestamp DATETIME
	);`
	_, err = db.Exec(sqlStmt)
	if err != nil {
		log.Fatalf("Error creating table: %q: %s\n", err, sqlStmt)
	}
}

func main() {
	initDB()
	defer db.Close()

	r := gin.Default()

	r.POST("/click", func(c *gin.Context) {
		id := uuid.New().String()
		timestamp := time.Now().UTC()

		_, err := db.Exec("INSERT INTO clicks (id, timestamp) VALUES (?, ?)", id, timestamp)
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Could not register click"})
			return
		}

		c.Status(http.StatusCreated)
	})

	r.GET("/clicks", func(c *gin.Context) {
		dateStr := c.Query("date")
		direction := c.Query("direction")

		if dateStr == "" || direction == "" {
			c.JSON(http.StatusBadRequest, gin.H{"error": "date and direction are required"})
			return
		}

		// Validate direction enum
		validDirections := map[string]bool{"<": true, ">": true, "<=": true, ">=": true}
		if !validDirections[direction] {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid direction. Use <, >, <=, or >="})
			return
		}

		// Parse date to ensure it's valid (YYYY-MM-DD)
		_, err := time.Parse("2006-01-02", dateStr)
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid date format. Use YYYY-MM-DD"})
			return
		}

		// Build query. Since direction is validated against a strict enum, it's safe from SQL injection.
		query := fmt.Sprintf("SELECT id, timestamp FROM clicks WHERE timestamp %s ?", direction)
		rows, err := db.Query(query, dateStr)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Database error"})
			return
		}
		defer rows.Close()

		var clicks []Click
		for rows.Next() {
			var cl Click
			if err := rows.Scan(&cl.ID, &cl.Timestamp); err != nil {
				continue
			}
			clicks = append(clicks, cl)
		}

		if len(clicks) == 0 {
			c.JSON(http.StatusNotFound, gin.H{"message": "No clicks found"})
			return
		}

		c.JSON(http.StatusOK, clicks)
	})

	r.Run("0.0.0.0:5000")
}