package main

import (
	"fmt"
	"log"
	"strconv"
	"strings"
	"unicode"

	"github.com/gofiber/fiber/v2"
)

// Request represents the input for the calculator
type Request struct {
	Expression string `json:"expression"`
}

// Response represents the output of the calculator
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

		if req.Expression == "" {
			return c.Status(400).JSON(fiber.Map{"error": "Expression cannot be empty"})
		}

		result, err := evaluate(req.Expression)
		if err != nil {
			return c.Status(400).JSON(fiber.Map{"error": fmt.Sprintf("Invalid expression: %v", err)})
		}

		return c.JSON(Response{Result: result})
	})

	log.Fatal(app.Listen("0.0.0.0:5000"))
}

// evaluate handles basic arithmetic expressions with precedence (+, -, *, /)
func evaluate(expr string) (string, error) {
	expr = strings.ReplaceAll(expr, " ", "")
	if expr == "" {
		return "", fmt.Errorf("empty expression")
	}

	tokens := tokenize(expr)
	if len(tokens) == 0 {
		return "", fmt.Errorf("no valid tokens found")
	}

	// First pass: Handle multiplication and division
	var values []string
	var ops []string

	i := 0
	for i < len(tokens) {
		token := tokens[i]
		if isOperator(token) {
			ops = append(ops, token)
			i++
		} else {
			val, err := strconv.ParseFloat(token, 64)
			if err != nil {
				return "", err
			}
			
			// Look ahead for * or /
			for i+1 < len(tokens) && (tokens[i+1] == "*" || tokens[i+1] == "/") {
				op := tokens[i+1]
				i += 2
				if i >= len(tokens) {
					return "", fmt.Errorf("unexpected end of expression")
				}
				nextVal, err := strconv.ParseFloat(tokens[i], 64)
				if err != nil {
					return "", err
				}
				if op == "*" {
					val *= nextVal
				} else {
					if nextVal == 0 {
						return "", fmt.Errorf("division by zero")
					}
					val /= nextVal
				}
			}
			values = append(values, fmt.Sprintf("%f", val))
			i++
		}
	}

	// Second pass: Handle addition and subtraction
	if len(values) == 0 {
		return "", fmt.Errorf("invalid expression")
	}

	res, err := strconv.ParseFloat(values[0], 64)
	if err != nil {
		return "", err
	}

	for j := 0; j < len(ops); j++ {
		nextVal, err := strconv.ParseFloat(values[j+1], 64)
		if err != nil {
			return "", err
		}
		if ops[j] == "+" {
			res += nextVal
		} else if ops[j] == "-" {
			res -= nextVal
		}
	}

	// Format result to remove trailing zeros if it's an integer
	return strconv.FormatFloat(res, 'f', -1, 64), nil
}

func tokenize(expr string) []string {
	var tokens []string
	var currentNum strings.Builder

	for _, char := range expr {
		if unicode.IsDigit(char) || char == '.' {
			currentNum.WriteRune(char)
		} else if isOpChar(char) {
			if currentNum.Len() > 0 {
				tokens = append(tokens, currentNum.String())
				currentNum.Reset()
			}
			tokens = append(tokens, string(char))
		} else {
			// Ignore invalid characters or treat as error (handled by ParseFloat)
			if currentNum.Len() > 0 {
				tokens = append(tokens, currentNum.String())
				currentNum.Reset()
			}
			tokens = append(tokens, string(char))
		}
	}
	if currentNum.Len() > 0 {
		tokens = append(tokens, currentNum.String())
	}
	return tokens
}

func isOpChar(r rune) bool {
	return r == '+' || r == '-' || r == '*' || r == '/'
}

func isOperator(s string) bool {
	return s == "+" || s == "-" || s == "*" || s == "/"
}