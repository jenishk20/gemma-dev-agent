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

// evaluate handles basic arithmetic expressions (+, -, *, /) with operator precedence.
// It uses a simple two-stack algorithm (shunting-yard style) to evaluate the expression.
func evaluate(expr string) (string, error) {
	expr = strings.ReplaceAll(expr, " ", "")
	if expr == "" {
		return "", fmt.Errorf("empty expression")
	}

	var values []float64
	var ops []rune

	precedence := map[rune]int{
		'+': 1,
		'-': 1,
		'*': 2,
		'/': 2,
	}

	applyOp := func() error {
		if len(values) < 2 || len(ops) == 0 {
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
		case '+':
			res = val1 + val2
		case '-':
			res = val1 - val2
		case '*':
			res = val1 * val2
		case '/':
			if val2 == 0 {
				return fmt.Errorf("division by zero")
			}
			res = val1 / val2
		default:
			return fmt.Errorf("unknown operator")
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
		} else if char == '(' {
			ops = append(ops, char)
		} else if char == ')' {
			for len(ops) > 0 && ops[len(ops)-1] != '(' {
				if err := applyOp(); err != nil {
					return "", err
				}
			}
			if len(ops) == 0 {
				return "", fmt.Errorf("mismatched parentheses")
			}
			ops = ops[:len(ops)-1]
		} else if p, ok := precedence[char]; ok {
			for len(ops) > 0 && ops[len(ops)-1] != '(' && precedence[ops[len(ops)-1]] >= p {
				if err := applyOp(); err != nil {
					return "", err
				}
			}
			ops = append(ops, char)
		} else {
			return "", fmt.Errorf("invalid character: %c", char)
		}
	}

	for len(ops) > 0 {
		if ops[len(ops)-1] == '(' {
			return "", fmt.Errorf("mismatched parentheses")
		}
		if err := applyOp(); err != nil {
			return "", err
		}
	}

	if len(values) != 1 {
		return "", fmt.Errorf("invalid expression")
	}

	return strconv.FormatFloat(values[0], 'f', -1, 64), nil
}

func main() {
	r := gin.Default()

	r.POST("/calculator", func(c *gin.Context) {
		var req CalcRequest
		if err := c.ShouldBindJSON(&req); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid input"})
			return
		}

		result, err := evaluate(req.Expression)
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
			return
		}

		c.JSON(http.StatusOK, CalcResponse{Result: result})
	})

	r.Run("0.0.0.0:5000")
}