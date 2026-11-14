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
		return "", fmt.Errorf("expression must end with a number")
	}

	// First pass: handle multiplication (*)
	var afterMul []string
	for i := 0; i < len(tokens); i++ {
		if tokens[i] == "*" {
			left, _ := strconv.Atoi(afterMul[len(afterMul)-1])
			right, err := strconv.Atoi(tokens[i+1])
			if err != nil {
				return "", err
			}
			res := left * right
			afterMul[len(afterMul)-1] = strconv.Itoa(res)
			i++ // skip the next number
		} else {
			afterMul = append(afterMul, tokens[i])
		}
	}

	// Second pass: handle addition (+)
	finalRes := 0
	firstNum, err := strconv.Atoi(afterMul[0])
	if err != nil {
		return "", err
	}
	finalRes = firstNum

	for i := 1; i < len(afterMul); i += 2 {
		if afterMul[i] != "+" {
			return "", fmt.Errorf("unexpected operator")
		}
		num, err := strconv.Atoi(afterMul[i+1])
		if err != nil {
			return "", err
		}
		finalRes += num
	}

	return strconv.Itoa(finalRes), nil
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