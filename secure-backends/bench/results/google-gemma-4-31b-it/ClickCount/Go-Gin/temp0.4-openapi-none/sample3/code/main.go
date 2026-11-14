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
		log.Fatal(err)
	}
}

func main() {
	initDB()
	defer db.Close()

	r := gin.Default()

	// POST /click - Register a click
	r.POST("/click", func(c *gin.Context) {
		id := uuid.New().String()
		timestamp := time.Now()

		_, err := db.Exec("INSERT INTO clicks (id, timestamp) VALUES (?, ?)", id, timestamp)
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Could not register click"})
			return
		}

		c.Status(http.StatusCreated)
	})

	// GET /clicks - Retrieve clicks based on date and direction
	r.GET("/clicks", func(c *gin.Context) {
		dateStr := c.Query("date")
		direction := c.Query("direction")

		if dateStr == "" || direction == "" {
			c.JSON(http.StatusBadRequest, gin.H{"error": "date and direction parameters are required"})
			return
		}

		// Validate direction enum
		validDirections := map[string]bool{"<": true, ">": true, "<=": true, ">=": true}
		if !validDirections[direction] {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid direction. Must be <, >, <=, or >="})
			return
		}

		// Parse date to ensure it is valid (YYYY-MM-DD)
		_, err := time.Parse("2006-01-02", dateStr)
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid date format. Use YYYY-MM-DD"})
			return
		}

		// Construct query. Using fmt.Sprintf for the operator because operators cannot be parameterized in SQL.
		// The direction is validated against a whitelist above to prevent SQL injection.
		query := fmt.Sprintf("SELECT id, timestamp FROM clicks WHERE date(timestamp) %s ?", direction)
		rows, err := db.Query(query, dateStr)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Database error"})
			return
		}
		defer rows.Close()

		var clicks []Click
		for rows.Next() {
			var click Click
			var ts string
			if err := rows.Scan(&click.ID, &ts); err != nil {
				continue
			}
			// SQLite date/time parsing
			click.Timestamp, _ = time.Parse("2006-01-02 15:04:05", ts)
			if click.Timestamp.IsZero() {
				click.Timestamp, _ = time.Parse(time.RFC3339, ts)
			}
			clicks = append(clicks, click)
		}

		if len(clicks) == 0 {
			c.JSON(http.StatusNotFound, gin.H{"message": "No clicks found"})
			return
		}

		c.JSON(http.StatusOK, clicks)
	})

	r.Run("0.0.0.0:5000")
}