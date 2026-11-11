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

// evaluate parses a basic arithmetic expression using the go/ast package
// to ensure safe evaluation without using a full-blown eval engine.
func evaluate(expr string) (string, error) {
	tr := token.NewTokenSet()
	node, err := parser.ParseExpr(expr)
	if err != nil {
		return "", err
	}

	var eval func(ast.Expr) (float64, error)
	eval = func(e ast.Expr) (float64, error) {
		switch t := e.(type) {
		case *ast.BasicLit:
			if t.Kind == token.INT || t.Kind == token.FLOAT {
				return strconv.ParseFloat(t.Value, 64)
			}
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
		case *ast.ParenExpr:
			return eval(t.X)
		}
		return 0, fmt.Errorf("unsupported expression")
	}

	res, err := eval(node)
	if err != nil {
		return "", err
	}

	return strconv.FormatFloat(res, 'g', -1, 64), nil
}

func calculatorHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var req CalcRequest
	decoder := json.NewDecoder(r.Body)
	if err := decoder.Decode(&req); err != nil {
		http.Error(w, "Invalid JSON", http.StatusBadRequest)
		return
	}

	result, err := evaluate(req.Expression)
	if err != nil {
		http.Error(w, "Invalid input: "+err.Error(), http.StatusBadRequest)
		return
	}

	resp := CalcResponse{Result: result}
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(resp)
}

func main() {
	http.HandleFunc("/calculator", calculatorHandler)

	fmt.Println("Server starting on 0.0.0.0:5000...")
	if err := http.ListenAndServe("0.0.0.0:5000", nil); err != nil {
		log.Fatal(err)
	}
}