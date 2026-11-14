package main

import (
	"log"
	"regexp"
	"strings"

	"github.com/gofiber/fiber/v2"
)

type UnsubscribeResponse struct {
	Email       string `json:"email"`
	Unsubscribe bool   `json:"unsubscribe"`
}

func main() {
	app := fiber.New()

	app.Post("/decideUnsubscribe", func(c *fiber.Ctx) error {
		// Read raw body as text/plain
		body := c.Body()
		emailContent := string(body)

		// Extract email from "From: ..." header
		// Regex looks for "From:" followed by optional name in brackets and the email address
		emailRegex := regexp.MustCompile(`(?i)From:\s*([^<\r\n]*\s*<)?([^>\s\r\n]+>)?`)
		matches := emailRegex.FindStringSubmatch(emailContent)

		email := ""
		if len(matches) > 0 {
			// The email is usually in the second capturing group if <...> is used, 
			// or the first if it's just the address.
			rawEmail := matches[len(matches)-1]
			rawEmail = strings.TrimSpace(rawEmail)
			rawEmail = strings.Trim(rawEmail, "<>")
			email = rawEmail
		}

		// Keywords for unsubscribe detection
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

		return c.Status(fiber.StatusOK).JSON(UnsubscribeResponse{
			Email:       email,
			Unsubscribe: shouldUnsubscribe,
		})
	})

	log.Fatal(app.Listen("0.0.0.0:5000"))
}