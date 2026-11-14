package main

import (
	"bufio"
	"bytes"
	"fmt"
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
		bodyBytes, err := c.GetRawData()
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Could not read request body"})
			return
		}

		emailContent := string(bodyBytes)
		
		// Extract email from "From: Name <email@domain.com>" or "From: email@domain.com"
		email := extractEmail(emailContent)
		
		// Check for unsubscribe keywords
		shouldUnsubscribe := checkUnsubscribeKeywords(emailContent)

		c.JSON(http.StatusOK, UnsubscribeResponse{
			Email:       email,
			Unsubscribe: shouldUnsubscribe,
		})
	})

	r.Run("0.0.0.0:5000")
}

func extractEmail(content string) string {
	// Look for the "From:" header
	scanner := bufio.NewScanner(bytes.NewReader([]byte(content)))
	for scanner.Scan() {
		line := scanner.Text()
		if strings.HasPrefix(strings.ToLower(line), "from:") {
			// Regex to find email inside angle brackets or just the email string
			re := regexp.MustCompile(`[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}`)
			match := re.FindString(line)
			if match != "" {
				return match
			}
		}
	}
	return ""
}

func checkUnsubscribeKeywords(content string) bool {
	keywords := []string{
		"unsubscribe",
		"remove me",
		"deregister me",
		"stop sending me",
		"delete me",
	}

	lowerContent := strings.ToLower(content)
	for _, kw := range keywords {
		if strings.Contains(lowerContent, kw) {
			return true
		}
	}
	return false
}