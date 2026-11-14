package main

import (
	"log"
	"net/mail"
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

		// Extract email from the "From:" header
		emailAddr := ""
		msg, err := mail.ReadMessage(strings.NewReader(body))
		if err == nil {
			from := msg.Header.Get("From")
			addr, err := mail.ParseAddress(from)
			if err == nil {
				emailAddr = addr.Address
			}
		}

		// If mail.ReadMessage fails or doesn't find a header, 
		// try a simple regex fallback for "From: ... <email>"
		if emailAddr == "" {
			re := regexp.MustCompile(`(?i)From:.*<(.+@.+)>>?`)
			matches := re.FindStringSubmatch(body)
			if len(matches) > 1 {
				emailAddr = matches[1]
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
		lowerBody := strings.ToLower(body)
		for _, kw := range keywords {
			if strings.Contains(lowerBody, kw) {
				shouldUnsubscribe = true
				break
			}
		}

		return c.JSON(UnsubscribeResponse{
			Email:       emailAddr,
			Unsubscribe: shouldUnsubscribe,
		})
	})

	log.Fatal(app.Listen("0.0.0.0:5000"))
}