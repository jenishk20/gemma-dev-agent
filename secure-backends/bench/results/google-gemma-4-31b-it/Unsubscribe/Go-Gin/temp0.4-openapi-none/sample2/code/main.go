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
		// Read raw body as text/plain
		bodyBytes, err := io.ReadAll(c.Request.Body)
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Unable to read request body"})
			return
		}
		body := string(bodyBytes)

		// Extract Email from "From: ..." header
		email := extractEmail(body)

		// Determine if the user wants to unsubscribe
		shouldUnsubscribe := checkUnsubscribeKeywords(body)

		c.JSON(http.StatusOK, UnsubscribeResponse{
			Email:       email,
			Unsubscribe: shouldUnsubscribe,
		})
	})

	r.Run("0.0.0.0:5000")
}

func extractEmail(text string) string {
	// Look for "From: Name <email@domain.com>" or "From: email@domain.com"
	re := regexp.MustCompile(`(?i)From:\s*([^<\r\n]*\s*<)?([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})`)
	matches := re.FindStringSubmatch(text)
	if len(matches) > 2 {
		return matches[2]
	}
	return ""
}

func checkUnsubscribeKeywords(text string) bool {
	keywords := []string{
		"unsubscribe",
		"remove me",
		"deregister me",
		"stop sending me",
		"delete me",
	}

	lowerText := strings.ToLower(text)
	for _, keyword := range keywords {
		if strings.Contains(lowerText, keyword) {
			return true
		}
	}
	return false
}