package main

import (
	"fmt"
	"strconv"
	"strings"
	"unicode"

	"github.com/gofiber/fiber/v2"
)

// Request represents the input for the calculator
type Request struct {
	Expression string `json:"expression"`
}

// Response represents the result of the calculation
type Response struct {
	Result string `json:"result"`
}

func main() {
	app := fiber.New()

	app.Post("/calculator", func(c *fiber.Ctx) error {
		var req Request
		if err := c.BodyParser(&req); err != nil {
			return c.Status(400).JSON(fiber.Map{"error": "Invalid input"})
		}

		result, err := evaluate(req.Expression)
		if err != nil {
			return c.Status(400).JSON(fiber.Map{"error": "Invalid expression"})
		}

		return c.JSON(Response{Result: result})
	})

	app.Listen("0.0.0.0:5000")
}

// evaluate parses and calculates a simple arithmetic expression supporting +, -, * and /
func evaluate(expr string) (string, error) {
	expr = strings.ReplaceAll(expr, " ", "")
	if expr == "" {
		return "", fmt.Errorf("empty expression")
	}

	tokens := tokenize(expr)
	if len(tokens) == 0 {
		return "", fmt.Errorf("invalid expression")
	}

	// Handle multiplication and division first (Precedence)
	var processed []string
	for i := 0; i < len(tokens); i++ {
		token := tokens[i]
		if token == "*" || token == "/" {
			if i == 0 || i == len(tokens)-1 {
				return "", fmt.Errorf("invalid operator position")
			}
			left, errL := strconv.ParseFloat(processed[len(processed)-1], 64)
			right, errR := strconv.ParseFloat(tokens[i+1], 64)
			if errL != nil || errR != nil {
				return "", fmt.Errorf("invalid operand")
			}

			var res float64
			if token == "*" {
				res = left * right
			} else {
				if right == 0 {
					return "", fmt.Errorf("division by zero")
				}
				res = left / right
			}
			processed[len(processed)-1] = fmt.Sprintf("%f", res)
			i++ // skip next token
		} else {
			processed = append(processed, token)
		}
	}

	// Handle addition and subtraction
	var finalResult float64
	currentOp := '+'
	for i := 0; i < len(processed); i++ {
		token := processed[i]
		if token == "+" || token == "-" {
			currentOp = rune(token[0])
		} else {
			val, err := strconv.ParseFloat(token, 64)
			if err != nil {
				return "", fmt.Errorf("invalid number")
			}
			if currentOp == '+' {
				finalResult += val
			} else {
				finalResult -= val
			}
		}
	}

	// Format result to remove trailing zeros if it's an integer
	resStr := fmt.Sprintf("%g", finalResult)
	return resStr, nil
}

func tokenize(expr string) []string {
	var tokens []string
	var currentNum strings.Builder

	for _, char := range expr {
		if unicode.IsDigit(char) || char == '.' {
			currentNum.WriteRune(char)
		} else if char == '+' || char == '-' || char == '*' || char == '/' {
			if currentNum.Len() > 0 {
				tokens = append(tokens, currentNum.String())
				currentNum.Reset()
			}
			tokens = append(tokens, string(char))
		} else {
			// Invalid character
			return nil
		}
	}
	if currentNum.Len() > 0 {
		tokens = append(tokens, currentNum.String())
	}
	return tokens
}