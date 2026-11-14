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

// evaluate handles basic arithmetic expressions with + and * following order of operations.
// It supports integers and basic spacing.
func evaluate(expr string) (string, error) {
	expr = strings.ReplaceAll(expr, " ", "")
	if expr == "" {
		return "", fmt.Errorf("empty expression")
	}

	// Tokenize expression into numbers and operators
	var tokens []string
	var currentNum strings.Builder
	for _, char := range expr {
		if unicode.IsDigit(char) {
			currentNum.WriteRune(char)
		} else if char == '+' || char == '*' {
			if currentNum.Len() == 0 {
				return "", fmt.Errorf("invalid operator position")
			}
			tokens = append(tokens, currentNum.String())
			tokens = append(tokens, string(char))
			currentNum.Reset()
		} else {
			return "", fmt.Errorf("invalid character: %c", char)
		}
	}
	if currentNum.Len() > 0 {
		tokens = append(tokens, currentNum.String())
	} else {
		return "", fmt.Errorf("expression ends with operator")
	}

	// First pass: Handle Multiplication (*)
	var afterMult []string
	for i := 0; i < len(tokens); i++ {
		if tokens[i] == "*" {
			left, _ := strconv.Atoi(afterMult[len(afterMult)-1])
			right, _ := strconv.Atoi(tokens[i+1])
			res := left * right
			afterMult[len(afterMult)-1] = strconv.Itoa(res)
			i++ // skip the right operand
		} else {
			afterMult = append(afterMult, tokens[i])
		}
	}

	// Second pass: Handle Addition (+)
	total := 0
	for i := 0; i < len(afterMult); i++ {
		if afterMult[i] == "+" {
			i++
			val, _ := strconv.Atoi(afterMult[i])
			total += val
		} else {
			val, _ := strconv.Atoi(afterMult[i])
			total = val
		}
	}

	return strconv.Itoa(total), nil
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