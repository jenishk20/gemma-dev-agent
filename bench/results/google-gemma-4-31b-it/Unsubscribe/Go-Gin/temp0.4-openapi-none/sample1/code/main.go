package main

import (
	"io"
	"net/http"
	"regexp"
	"strings"

	"github.com/gin-gonic/gin"
)

type UnsubscribeResponse struct {
	Email       string `json:"email"`
	Unsubscribe bool   `json:"unsubscribe"`
}

func main() {
	r := gin.Default()

	r.POST("/decideUnsubscribe", func(c *gin.Context) {
		// Read the raw request body (text/plain)
		body, err := io.ReadAll(c.Request.Body)
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Unable to read request body"})
			return
		}

		emailContent := string(body)

		// Extract email from the "From:" header
		// Regex looks for "From: Name <email@domain.com>" or "From: email@domain.com"
		email := ""
		fromRegex := regexp.MustCompile(`(?i)From:\s*([^<\r\n]+)?<?([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})>?`)
		matches := fromRegex.FindStringSubmatch(emailContent)
		if len(matches) > 2 {
			email = matches[2]
		}

		// Keywords to identify unsubscribe requests
		keywords := []string{
			"unsubscribe",
			"remove me",
			"deregister me",
			"stop sending me",
			"delete me",
		}

		shouldUnsubscribe := false
		lowerContent := strings.ToLower(emailContent)
		for _, kw := range keywords {
			if strings.Contains(lowerContent, kw) {
				shouldUnsubscribe = true
				break
			}
		}

		c.JSON(http.StatusOK, UnsubscribeResponse{
			Email:       email,
			Unsubscribe: shouldUnsubscribe,
		})
	})

	r.Run("0.0.0.0:5000")
}