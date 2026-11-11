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
		body := string(c.Body())

		// 1. Extract Email address from "From: ..." header
		// Regex looks for "From: Name <email@domain.com>" or "From: email@domain.com"
		email := ""
		fromRegex := regexp.MustCompile(`(?i)From:\s*([^<\n\r]*<([^>\s]+)>|([^\s\n\r]+))`)
		matches := fromRegex.FindStringSubmatch(body)
		if len(matches) > 0 {
			if matches[2] != "" {
				email = matches[2] // Group 2 is the email inside <>
			} else {
				email = matches[3] // Group 3 is the raw email string
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

		return c.JSON(UnsubscribeResponse{
			Email:       email,
			Unsubscribe: shouldUnsubscribe,
		})
	})

	log.Fatal(app.Listen("0.0.0.0:5000"))
}