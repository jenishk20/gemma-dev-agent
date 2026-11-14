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
		bodyBytes, err := io.ReadAll(c.Request.Body)
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Unable to read request body"})
			return
		}
		body := string(bodyBytes)

		// Extract email from the "From:" header
		email := extractEmail(body)

		// Check for unsubscribe keywords in the body
		shouldUnsubscribe := checkUnsubscribe(body)

		c.JSON(http.StatusOK, UnsubscribeResponse{
			Email:       email,
			Unsubscribe: shouldUnsubscribe,
		})
	})

	r.Run("0.0.0.0:5000")
}

func extractEmail(body string) string {
	// Look for "From: Name <email@domain.com>" or "From: email@domain.com"
	re := regexp.MustCompile(`(?i)From:\s*([^<\n\r]*\s*<)?([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})`)
	matches := re.FindStringSubmatch(body)
	if len(matches) >= 3 {
		return matches[2]
	}
	return ""
}

func checkUnsubscribe(body string) bool {
	keywords := []string{
		"unsubscribe",
		"remove me",
		"deregister me",
		"stop sending me",
		"delete me",
	}

	lowerBody := strings.ToLower(body)
	for _, kw := range keywords {
		if strings.Contains(lowerBody, kw) {
			return true
		}
	}
	return false
}