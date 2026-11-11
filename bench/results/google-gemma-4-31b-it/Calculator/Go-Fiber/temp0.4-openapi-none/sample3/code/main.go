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
			return c.Status(400).JSON(fiber.Map{"error": err.Error()})
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

	// Shunting-yard algorithm to handle precedence
	var values []float64
	var ops []string

	precedence := map[string]int{
		"+": 1, "-": 1,
		"*": 2, "/": 2,
	}

	for i := 0; i < len(tokens); i++ {
		token := tokens[i]
		if isNumber(token) {
			val, _ := strconv.ParseFloat(token, 64)
			values = append(values, val)
		} else if token == "(" {
			ops = append(ops, token)
		} else if token == ")" {
			for len(ops) > 0 && ops[len(ops)-1] != "(" {
				if err := applyOp(&values, &ops); err != nil {
					return "", err
				}
			}
			if len(ops) == 0 {
				return "", fmt.Errorf("mismatched parentheses")
			}
			ops = ops[:len(ops)-1] // pop "("
		} else {
			for len(ops) > 0 && precedence[ops[len(ops)-1]] >= precedence[token] {
				if err := applyOp(&values, &ops); err != nil {
					return "", err
				}
			}
			ops = append(ops, token)
		}
	}

	for len(ops) > 0 {
		if ops[len(ops)-1] == "(" {
			return "", fmt.Errorf("mismatched parentheses")
		}
		if err := applyOp(&values, &ops); err != nil {
			return "", err
		}
	}

	if len(values) != 1 {
		return "", fmt.Errorf("invalid expression")
	}

	res := values[0]
	return strconv.FormatFloat(res, 'f', -1, 64), nil
}

func tokenize(expr string) []string {
	var tokens []string
	var currentNumber strings.Builder

	for _, char := range expr {
		if unicode.IsDigit(char) || char == '.' {
			currentNumber.WriteRune(char)
		} else {
			if currentNumber.Len() > 0 {
				tokens = append(tokens, currentNumber.String())
				currentNumber.Reset()
			}
			if strings.ContainsRune("+-*/()", char) {
				tokens = append(tokens, string(char))
			}
		}
	}
	if currentNumber.Len() > 0 {
		tokens = append(tokens, currentNumber.String())
	}
	return tokens
}

func isNumber(s string) bool {
	_, err := strconv.ParseFloat(s, 64)
	return err == nil
}

func applyOp(values *[]float64, ops *[]string) error {
	if len(*values) < 2 {
		return fmt.Errorf("invalid expression")
	}
	op := (*ops)[len(*ops)-1]
	*ops = (*ops)[:len(*ops)-1]

	right := (*values)[len(*values)-1]
	left := (*values)[len(*values)-2]
	*values = (*values)[:len(*values)-2]

	var res float64
	switch op {
	case "+":
		res = left + right
	case "-":
		res = left - right
	case "*":
		res = left * right
	case "/":
		if right == 0 {
			return fmt.Errorf("division by zero")
		}
		res = left / right
	default:
		return fmt.Errorf("unknown operator")
	}
	*values = append(*values, res)
	return nil
}