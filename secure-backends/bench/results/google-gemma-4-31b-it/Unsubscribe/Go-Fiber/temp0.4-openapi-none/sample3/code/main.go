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
		// Read the raw body as text/plain
		body := string(c.Body())

		// 1. Extract Email from "From:" header
		// Regex looks for "From: Name <email@domain.com>" or "From: email@domain.com"
		email := ""
		emailRegex := regexp.MustCompile(`(?i)From:\s*([^<\r\n]+)?\s*<([^>\r\n]+)>|From:\s*([^\s\r\n,]+@[^\s\r\n,]+)`)
		matches := emailRegex.FindStringSubmatch(body)
		if len(matches) > 0 {
			if matches[2] != "" {
				email = matches[2]
			} else if matches[3] != "" {
				email = matches[3]
			}
		}

		// 2. Decide if user wants to unsubscribe
		// Keywords: "unsubscribe", "remove me", "deregister me", "stop sending me", "delete me"
		keywords := []string{
			"unsubscribe",
			"remove me",
			"deregister me",
			"stop sending me",
			"delete me",
		}

		shouldUnsubscribe := false
		lowerBody := strings.ToLower(body)
		for _, kw := range keywords {
			if strings.Contains(lowerBody, kw) {
				shouldUnsubscribe = true
				break
			}
		}

		return c.JSON(fiber.Map{
			"email":       email,
			"unsubscribe": shouldUnsubscribe,
		})
	})

	log.Fatal(app.Listen("0.0.0.0:5000"))
}