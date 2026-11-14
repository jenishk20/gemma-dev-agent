package main

import (
	"fmt"
	"net/http"
	"strconv"
	"strings"
	"unicode"

	"github.com/gin-gonic/gin"
)

type CalcRequest struct {
	Expression string `json:"expression" binding:"required"`
}

type CalcResponse struct {
	Result string `json:"result"`
}

func evaluate(expression string) (float64, error) {
	expression = strings.ReplaceAll(expression, " ", "")
	if expression == "" {
		return 0, fmt.Errorf("empty expression")
	}

	var tokens []string
	var currentNumber strings.Builder

	for i := 0; i < len(expression); i++ {
		char := rune(expression[i])
		if unicode.IsDigit(char) || char == '.' {
			currentNumber.WriteRune(char)
		} else {
			if currentNumber.Len() > 0 {
				tokens = append(tokens, currentNumber.String())
				currentNumber.Reset()
			}
			tokens = append(tokens, string(char))
		}
	}
	if currentNumber.Len() > 0 {
		tokens = append(tokens, currentNumber.String())
	}

	// Handle Multiplication and Division first
	var stage1 []string
	for i := 0; i < len(tokens); i++ {
		token := tokens[i]
		if token == "*" || token == "/" {
			if i == 0 || i == len(tokens)-1 {
				return 0, fmt.Errorf("invalid expression")
			}
			left, errL := strconv.ParseFloat(tokens[i-1], 64)
			right, errR := strconv.ParseFloat(tokens[i+1], 64)
			if errL != nil || errR != nil {
				return 0, fmt.Errorf("invalid operand")
			}

			var res float64
			if token == "*" {
				res = left * right
			} else {
				if right == 0 {
					return 0, fmt.Errorf("division by zero")
				}
				res = left / right
			}
			stage1 = append(stage1, fmt.Sprintf("%f", res))
			i += 1 // skip next operand
			// This is a simplified parser; for complex chains we'd need a loop
			// But for basic "1+2*3" it works. To handle "2*3*4", we need a different approach.
		} else {
			// This logic is flawed for multiple MD operations. Let's use a proper stack.
		}
	}
	return 0, fmt.Errorf("parser not implemented")
}

// A more robust simple evaluator for basic arithmetic
func calculate(expr string) (string, error) {
	expr = strings.ReplaceAll(expr, " ", "")
	var values []float64
	var ops []rune

	precedence := map[rune]int{'+': 1, '-': 1, '*': 2, '/': 2}

	applyOp := func() error {
		if len(values) < 2 {
			return fmt.Errorf("invalid expression")
		}
		val2 := values[len(values)-1]
		values = values[:len(values)-1]
		val1 := values[len(values)-1]
		values = values[:len(values)-1]
		op := ops[len(ops)-1]
		ops = ops[:len(ops)-1]

		var res float64
		switch op {
		case '+': res = val1 + val2
		case '-': res = val1 - val2
		case '*': res = val1 * val2
		case '/':
			if val2 == 0 {
				return fmt.Errorf("division by zero")
			}
			res = val1 / val2
		}
		values = append(values, res)
		return nil
	}

	for i := 0; i < len(expr); i++ {
		char := rune(expr[i])
		if unicode.IsDigit(char) || char == '.' {
			start := i
			for i < len(expr) && (unicode.IsDigit(rune(expr[i])) || expr[i] == '.') {
				i++
			}
			val, err := strconv.ParseFloat(expr[start:i], 64)
			if err != nil {
				return "", err
			}
			values = append(values, val)
			i--
		} else if prec, ok := precedence[char]; ok {
			for len(ops) > 0 && precedence[ops[len(ops)-1]] >= prec {
				if err := applyOp(); err != nil {
					return "", err
				}
			}
			ops = append(ops, char)
		} else {
			return "", fmt.Errorf("invalid character")
		}
	}

	for len(ops) > 0 {
		if err := applyOp(); err != nil {
			return "", err
		}
	}

	if len(values) != 1 {
		return "", fmt.Errorf("invalid expression")
	}

	return fmt.Sprintf("%g", values[0]), nil
}

func main() {
	gin.SetMode(gin.ReleaseMode)
	r := gin.Default()

	r.POST("/calculator", func(c *gin.Context) {
		var req CalcRequest
		if err := c.ShouldBindJSON(&req); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid input"})
			return
		}

		result, err := calculate(req.Expression)
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
			return
		}

		c.JSON(http.StatusOK, CalcResponse{Result: result})
	})

	r.Run("0.0.0.0:5000")
}