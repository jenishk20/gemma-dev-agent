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

// evaluate handles basic arithmetic expressions: +, -, *, /
// It implements a simple recursive descent parser to handle operator precedence
type parser struct {
	tokens []string
	pos    int
}

func (p *parser) parseExpression() float64 {
	result := p.parseTerm()
	for p.pos < len(p.tokens) {
		op := p.tokens[p.pos]
		p.pos++
		if op == "+" {
			result += p.parseTerm()
		} else if op == "-" {
			result -= p.parseTerm()
		} else {
			return result
		}
	}
	return result
}

func (p *parser) parseTerm() float64 {
	result := p.parseFactor()
	for p.pos < len(p.tokens) {
		op := p.tokens[p.pos]
		p.pos++
		if op == "*" {
			result *= p.parseFactor()
		} else if op == "/" {
			divisor := p.parseFactor()
			if divisor == 0 {
				panic("division by zero")
			}
			result /= divisor
		} else {
			return result
		}
	}
	return result
}

func (p *parser) parseFactor() float64 {
	token := p.tokens[p.pos]
	p.pos++
	val, err := strconv.ParseFloat(token, 64)
	if err != nil {
		panic("invalid number")
	}
	return val
}

func tokenize(expr string) []string {
	var tokens []string
	var number strings.Builder
	for _, r := range expr {
		if unicode.IsDigit(r) || r == '.' {
			number.WriteRune(r)
		} else if strings.ContainsRune("+-*/", r) {
			if number.Len() > 0 {
				tokens = append(tokens, number.String())
				number.Reset()
			}
			tokens = append(tokens, string(r))
		} else if unicode.IsSpace(r) {
			if number.Len() > 0 {
				tokens = append(tokens, number.String())
				number.Reset()
			}
		} else {
			panic("invalid character")
		}
	}
	if number.Len() > 0 {
		tokens = append(tokens, number.String())
	}
	return tokens
}

func calculate(expression string) (string, error) {
	defer func() {
		if r := recover(); r != nil {
			// handle panic as error
		}
	}()

	tokens, err := func() ([]string, error) {
		defer func() {
			if r := recover(); r != nil {
				return
			}
		}()
		return tokenize(expression), nil
	}() catch {
		return "", fmt.Errorf("invalid expression")
	}
	
	// Re-implementing the logic without the complex closure to avoid Go's lack of try-catch
	return "", nil 
}

// Simplified calculation logic for the Gin handler to avoid panic issues in a single file
func solve(expr string) (string, error) {
	var tokens []string
	var currentNum strings.Builder
	for _, char := range expr {
		if unicode.IsDigit(char) || char == '.' {
			currentNum.WriteRune(char)
		} else if strings.ContainsRune("+-*/", char) {
			if currentNum.Len() > 0 {
				tokens = append(tokens, currentNum.String())
				currentNum.Reset()
			}
			tokens = append(tokens, string(char))
		} else if unicode.IsSpace(char) {
			if currentNum.Len() > 0 {
				tokens = append(tokens, currentNum.String())
				currentNum.Reset()
			}
		} else {
			return "", fmt.Errorf("invalid character")
		}
	}
	if currentNum.Len() > 0 {
		tokens = append(tokens, currentNum.String())
	}

	if len(tokens) == 0 {
		return "", fmt.Errorf("empty expression")
	}

	// Basic precedence: handle * and / first
	var stack []string
	for i := 0; i < len(tokens); i++ {
		if tokens[i] == "*" || tokens[i] == "/" {
			left, errL := strconv.ParseFloat(stack[len(stack)-1], 64)
			right, errR := strconv.ParseFloat(tokens[i+1], 64)
			if errL != nil || errR != nil {
				return "", fmt.Errorf("invalid operands")
			}
			var res float64
			if tokens[i] == "*" {
				res = left * right
			} else {
				if right == 0 {
					return "", fmt.Errorf("division by zero")
				}
				res = left / right
			}
			stack[len(stack)-1] = fmt.Sprintf("%f", res)
			i++
		} else {
			stack = append(stack, tokens[i])
		}
	}

	// Handle + and -
	var finalRes float64
	var currentOp = "+"
	for i := 0; i < len(stack); i++ {
		if stack[i] == "+" || stack[i] == "-" {
			currentOp = stack[i]
		} else {
			val, err := strconv.ParseFloat(stack[i], 64)
			if err != nil {
				return "", fmt.Errorf("invalid number")
			}
			if currentOp == "+" {
				finalRes += val
			} else {
				finalRes -= val
			}
		}
	}

	return strconv.FormatFloat(finalRes, 'f', -1, 64), nil
}

func main() {
	r := gin.Default()

	r.POST("/calculator", func(c *gin.Context) {
		var req CalcRequest
		if err := c.ShouldBindJSON(&req); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid input"})
			return
		}

		result, err := solve(req.Expression)
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
			return
		}

		c.JSON(http.StatusOK, CalcResponse{Result: result})
	})

	r.Run("0.0.0.0:5000")
}