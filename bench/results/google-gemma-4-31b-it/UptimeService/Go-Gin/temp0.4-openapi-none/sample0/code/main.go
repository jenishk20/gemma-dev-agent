package main

import (
	"database/sql"
	"log"
	"net/http"
	"time"

	"github.com/gin-gonic/gin"
	_ "github.com/mattn/go-sqlite3"
)

type HeartbeatRequest struct {
	ServiceID string `json:"serviceId" binding:"required"`
	Token     string `json:"token" binding:"required"`
}

type TokenRequest struct {
	Token string `json:"token" binding:"required"`
}

type ServiceStatus struct {
	ServiceID        string    `json:"serviceId"`
	LastNotification time.Time `json:"lastNotification"`
}

var db *sql.DB

func initDB() {
	var err error
	db, err = sql.Open("sqlite3", "./db.sqlite3")
	if err != nil {
		log.Fatal(err)
	}

	sqlStmt := `
	CREATE TABLE IF NOT EXISTS services (
		service_id TEXT PRIMARY KEY,
		token TEXT,
		last_notification DATETIME
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

	r.POST("/heartbeat", func(c *gin.Context) {
		var req HeartbeatRequest
		if err := c.ShouldBindJSON(&req); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid request payload"})
			return
		}

		now := time.Now()
		_, err := db.Exec(
			"INSERT INTO services (service_id, token, last_notification) VALUES (?, ?, ?) "+
				"ON CONFLICT(service_id) DO UPDATE SET token=excluded.token, last_notification=excluded.last_notification",
			req.ServiceID, req.Token, now,
		)

		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Internal server error"})
			return
		}

		c.Status(http.StatusOK)
	})

	r.POST("/services", func(c *gin.Context) {
		var req TokenRequest
		if err := c.ShouldBindJSON(&req); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid request payload"})
			return
		}

		rows, err := db.Query("SELECT service_id, last_notification FROM services WHERE token = ?", req.Token)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Internal server error"})
			return
		}
		defer rows.Close()

		var services []ServiceStatus
		for rows.Next() {
			var s ServiceStatus
			if err := rows.Scan(&s.ServiceID, &s.LastNotification); err != nil {
				c.JSON(http.StatusInternalServerError, gin.H{"error": "Internal server error"})
				return
			}
			services = append(services, s)
		}

		if services == nil {
			services = make([]ServiceStatus, 0)
		}

		c.JSON(http.StatusOK, services)
	})

	r.Run("0.0.0.0:5000")
}