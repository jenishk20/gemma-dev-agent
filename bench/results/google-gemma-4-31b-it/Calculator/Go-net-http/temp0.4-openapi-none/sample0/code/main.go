package main

import (
	"encoding/json"
	"fmt"
	"go/ast"
	"go/parser"
	"go/token"
	"log"
	"net/http"
	"strconv"
)

type CalcRequest struct {
	Expression string `json:"expression"`
}

type CalcResponse struct {
	Result string `json:"result"`
}

func evaluate(expr string) (float64, error) {
	tr := token.NewTokenList(nil) // Not used, but needed for parser
	_ = tr
	
	// Use go/parser to parse the expression as a Go expression
	exprAst, err := parser.ParseExpr(expr)
	if err != nil {
		return 0, err
	}

	var eval func(ast.Expr) (float64, error)
	eval = func(e ast.Expr) (float64, error) {
		switch t := e.(type) {
		case *ast.BasicLit:
			if t.Kind == token.INT || t.Kind == token.FLOAT {
				return strconv.ParseFloat(t.Value, 64)
			}
			return 0, fmt.Errorf("invalid literal")
		case *ast.BinaryExpr:
			left, err := eval(t.X)
			if err != nil {
				return 0, err
			}
			right, err := eval(t.Y)
			if err != nil {
				return 0, err
			}
			switch t.Op {
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
			return eval(t.X)
		default:
			return 0, fmt.Errorf("unsupported expression type")
		}
	}

	return eval(exprAst)
}

func calculatorHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var req CalcRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "Invalid input", http.StatusBadRequest)
		return
	}

	resVal, err := evaluate(req.Expression)
	if err != nil {
		http.Error(w, "Invalid input", http.StatusBadRequest)
		return
	}

	resp := CalcResponse{
		Result: fmt.Sprintf("%g", resVal),
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(resp)
}

func main() {
	http.HandleFunc("/calculator", calculatorHandler)

	fmt.Println("Server starting on 0.0.0.0:5000...")
	log.Fatal(http.ListenAndServe("0.0.0.0:5000", nil))
}