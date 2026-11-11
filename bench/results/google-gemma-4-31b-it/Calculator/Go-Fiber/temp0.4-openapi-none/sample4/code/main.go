package main

import (
	"fmt"
	"go/ast"
	"go/parser"
	"go/token"
	"strconv"

	"github.com/gofiber/fiber/v2"
)

type CalculationRequest struct {
	Expression string `json:"expression"`
}

type CalculationResponse struct {
	Result string `json:"result"`
}

func evaluate(expr string) (float64, error) {
	tr := token.NewTokenList(nil) // Not actually used by parser.ParseExpr
	_ = tr
	
	// Using go/parser to handle operator precedence (PEMDAS)
	exprAST, err := parser.ParseExpr(expr)
	if err != nil {
		return 0, err
	}

	var eval func(ast.Expr) (float64, error)
	eval = func(e ast.Expr) (float64, error) {
		switch node := e.(type) {
		case *ast.BasicLit:
			if node.Kind == token.INT || node.Kind == token.FLOAT {
				return strconv.ParseFloat(node.Value, 64)
			}
			return 0, fmt.Errorf("invalid literal")
		case *ast.BinaryExpr:
			left, err := eval(node.X)
			if err != nil {
				return 0, err
			}
			right, err := eval(node.Y)
			if err != nil {
				return 0, err
			}
			switch node.Op {
			case token.ADD:
				return left + right, nil
			case token.SUB:
				return left - right, nil
			case token.MUL:
				return left * right, nil
			case token.QUO:
				if right == 0 {
					return 0, fmt.Errorf("division by zero")
				}
				return left / right, nil
			}
			return 0, fmt.Errorf("unsupported operator")
		case *ast.ParenExpr:
			return eval(node.X)
		default:
			return 0, fmt.Errorf("unsupported expression type")
		}
	}

	return eval(exprAST)
}

func main() {
	app := fiber.New()

	app.Post("/calculator", func(c *fiber.Ctx) error {
		var req CalculationRequest
		if err := c.BodyParser(&req); err != nil {
			return c.Status(400).JSON(fiber.Map{"error": "Invalid input"})
		}

		if req.Expression == "" {
			return c.Status(400).JSON(fiber.Map{"error": "Expression is required"})
		}

		res, err := evaluate(req.Expression)
		if err != nil {
			return c.Status(400).JSON(fiber.Map{"error": "Invalid expression"})
		}

		// Format result to remove trailing zeros if it's an integer
		resultStr := fmt.Sprintf("%g", res)

		return c.Status(200).JSON(CalculationResponse{
			Result: resultStr,
		})
	})

	app.Listen("0.0.0.0:5000")
}