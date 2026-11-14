package main

import (
	"fmt"
	"net/http"
	"os"

	"github.com/gin-gonic/gin"
)

const logFileName = "logs.txt"

type LogRequest struct {
	Message string `json:"message"`
}

func main() {
	r := gin.Default()

	// POST /log - Log a message to the server
	r.POST("/log", func(c *gin.Context) {
		var req LogRequest
		if err := c.ShouldBindJSON(&req); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
			return
		}

		// Open file in append mode, create if it doesn't exist
		f, err := os.OpenFile(logFileName, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Could not open log file"})
			return
		}
		defer f.Close()

		if _, err := f.WriteString(req.Message + "\n"); err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Could not write to log file"})
			return
		}

		c.Status(http.StatusOK)
	})

	// GET /logs - Retrieve all logged messages
	r.GET("/logs", func(c *gin.Context) {
		data, err := os.ReadFile(logFileName)
		if err != nil {
			// If file doesn't exist yet, return empty string
			if os.IsNotExist(err) {
				c.String(http.StatusOK, "")
				return
			}
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Could not read log file"})
			return
		}

		c.String(http.StatusOK, string(data))
	})

	// Start server on 0.0.0.0:5000
	r.Run("0.0.0.0:5000")
}