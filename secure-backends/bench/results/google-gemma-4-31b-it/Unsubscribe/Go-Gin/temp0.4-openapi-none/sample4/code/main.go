package main

import (
	"bufio"
	"bytes"
	"io"
	"net/mail"
	"regexp"
	"strings"

	"github.com/gin-gonic/gin"
)

// Response defines the JSON output for the decideUnsubscribe endpoint
type Response struct {
	Email       string `json:"email"`
	Unsubscribe bool   `json:"unsubscribe"`
}

func main() {
	r := gin.Default()

	r.POST("/decideUnsubscribe", func(c *gin.Context) {
		// Read raw body as text/plain
		body, err := io.ReadAll(c.Request.Body)
		if err != nil {
			c.JSON(500, gin.H{"error": "Unable to read request body"})
			return
		}

		emailContent := string(body)

		// Parse the email to extract the sender's address
		msg, err := mail.ReadMessage(strings.NewReader(emailContent))
		var senderEmail string
		if err == nil {
			header := msg.Header.Get("From")
			addr, err := mail.ParseAddress(header)
			if err == nil {
				senderEmail = addr.Address
			}
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

		// If we couldn't find the email via mail.ReadMessage, 
		// try a fallback regex for the "From:" header
		if senderEmail == "" {
			re := regexp.MustCompile(`(?i)From:\s*([^<\r\n]+)?\s*<([^>\r\n]+)>`)
			matches := re.FindStringSubmatch(emailContent)
			if len(matches) > 2 {
				senderEmail = matches[2]
			} else {
				reSimple := regexp.MustCompile(`(?i)From:\s*([^\s\r\n]+)`)
				matchesSimple := reSimple.FindStringSubmatch(emailContent)
				if len(matchesSimple) > 1 {
					senderEmail = matchesSimple[1]
				}
			}
		}

		c.JSON(200, Response{
			Email:       senderEmail,
			Unsubscribe: shouldUnsubscribe,
		})
	})

	r.Run("0.0.0.0:5000")
}