package main

import (
	"fmt"
	"log"
	"strconv"
	"strings"
	"unicode"

	"github.com/gofiber/fiber/v2"
)

type CalcRequest struct {
	Expression string `json:"expression"`
}

type CalcResponse struct {
	Result string `json:"result"`
}

func main() {
	app := fiber.New()

	app.Post("/calculator", func(c *fiber.Ctx) error {
		var req CalcRequest
		if err := c.BodyParser(&req); err != nil {
			return c.Status(400).JSON(fiber.Map{"error": "Invalid input"})
		}

		result, err := evaluate(req.Expression)
		if err != nil {
			return c.Status(400).JSON(fiber.Map{"error": "Invalid expression"})
		}

		return c.JSON(CalcResponse{Result: result})
	})

	log.Fatal(app.Listen("0.0.0.0:5000"))
}

func evaluate(expr string) (string, error) {
	expr = strings.ReplaceAll(expr, " ", "")
	if expr == "" {
		return "", fmt.Errorf("empty expression")
	}

	tokens := tokenize(expr)
	if len(tokens) == 0 {
		return "", fmt.Errorf("invalid expression")
	}

	// Shunting-yard algorithm to convert to postfix
	var output []string
	var stack []string
	precedence := map[string]int{"+": 1, "-": 1, "*": 2, "/": 2}

	for _, token := range tokens {
		if isDigit(token) {
			output = append(output, token)
		} else if op, ok := precedence[token]; ok {
			for len(stack) > 0 {
				top := stack[len(stack)-1]
				if topOp, ok2 := precedence[top]; ok2 && topOp >= op {
					output = append(output, top)
					stack = stack[:len(stack)-1]
				} else {
					break
				}
			}
			stack = append(stack, token)
		} else {
			return "", fmt.Errorf("invalid character")
		}
	}
	for len(stack) > 0 {
		output = append(output, stack[len(stack)-1])
		stack = stack[:len(stack)-1]
	}

	// Evaluate postfix
	var evalStack []float64
	for _, token := range output {
		if val, err := strconv.ParseFloat(token, 64); err == nil {
			evalStack = append(evalStack, val)
		} else {
			if len(evalStack) < 2 {
				return "", fmt.Errorf("invalid expression")
			}
			b := evalStack[len(evalStack)-1]
			a := evalStack[len(evalStack)-2]
			evalStack = evalStack[:len(evalStack)-2]

			var res float64
			switch token {
			case "+":
				res = a + b
			case "-":
				res = a - b
			case "*":
				res = a * b
			case "/":
				if b == 0 {
					return "", fmt.Errorf("division by zero")
				}
				res = a / b
			}
			evalStack = append(evalStack, res)
		}
	}

	if len(evalStack) != 1 {
		return "", fmt.Errorf("invalid expression")
	}

	final := evalStack[0]
	return strconv.FormatFloat(final, 'f', -1, 64), nil
}

func tokenize(expr string) []string {
	var tokens []string
	var currentNum strings.Builder

	for i := 0; i < len(expr); i++ {
		char := rune(expr[i])
		if unicode.IsDigit(char) || char == '.' {
			currentNum.WriteRune(char)
		} else {
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

func isDigit(s string) bool {
	if len(s) == 0 {
		return false
	}
	return unicode.IsDigit(rune(s[0]))
}