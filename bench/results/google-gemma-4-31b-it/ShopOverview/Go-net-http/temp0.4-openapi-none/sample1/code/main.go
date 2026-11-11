package main

import (
	"database/sql"
	"encoding/csv"
	"encoding/json"
	"fmt"
	"html/template"
	"log"
	"net/http"
	"os"
	"strconv"
	"strings"
	"time"

	"github.com/golang-jwt/jwt/v5"
	_ "github.com/mattn/go-sqlite3"
	"golang.org/x/crypto/bcrypt"
)

var db *sql.DB
var jwtKey []byte

type Merchant struct {
	Email    string `json:"email"`
	Name     string `json:"name"`
	Password string `json:"password"`
}

type Ware struct {
	Name        string
	Description string
	Price       float64
	MerchantEmail string
}

func initDB() {
	var err error
	db, err = sql.Open("sqlite3", "./db.sqlite3")
	if err != nil {
		log.Fatal(err)
	}

	sqlStmt := `
	CREATE TABLE IF NOT EXISTS merchants (
		email TEXT PRIMARY KEY,
		name TEXT,
		password TEXT
	);
	CREATE TABLE IF NOT EXISTS wares (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		merchant_email TEXT,
		name TEXT,
		description TEXT,
		price REAL,
		FOREIGN KEY(merchant_email) REFERENCES merchants(email)
	);`
	_, err = db.Exec(sqlStmt)
	if err != nil {
		log.Fatal(err)
	}
}

func createToken(email string) (string, error) {
	token := jwt.NewWithClaims(jwt.SigningMethodHS256, jwt.MapClaims{
		"email": email,
		"exp":   time.Now().Add(time.Hour * 24).Unix(),
	})
	return token.SignedString(jwtKey)
}

func validateToken(tokenStr string) (string, error) {
	token, err := jwt.Parse(tokenStr, func(token *jwt.Token) (interface{}, error) {
		return jwtKey, nil
	})
	if err != nil || !token.Valid {
		return "", fmt.Errorf("invalid token")
	}
	claims, ok := token.Claims.(jwt.MapClaims)
	if !ok {
		return "", fmt.Errorf("invalid claims")
	}
	return claims["email"].(string), nil
}

func authMiddleware(next http.HandlerFunc) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		cookie, err := r.Cookie("AUTH_COOKIE")
		if err != nil {
			http.Error(w, "Unauthorized", http.StatusUnauthorized)
			return
		}
		_, err = validateToken(cookie.Value)
		if err != nil {
			http.Error(w, "Unauthorized", http.StatusUnauthorized)
			return
		}
		next(w, r)
	}
}

func handleRegister(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}
	var m Merchant
	if err := json.NewDecoder(r.Body).Decode(&m); err != nil {
		http.Error(w, "Invalid input", http.StatusBadRequest)
		return
	}
	if m.Email == "" || m.Name == "" || m.Password == "" {
		http.Error(w, "Missing fields", http.StatusBadRequest)
		return
	}

	hashedPassword, _ := bcrypt.GenerateFromPassword([]byte(m.Password), bcrypt.DefaultCost)
	_, err := db.Exec("INSERT INTO merchants (email, name, password) VALUES (?, ?, ?)", m.Email, m.Name, string(hashedPassword))
	if err != nil {
		http.Error(w, "Merchant already exists or DB error", http.StatusBadRequest)
		return
	}
	w.WriteHeader(http.StatusCreated)
}

func handleLogin(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}
	var creds Merchant
	if err := json.NewDecoder(r.Body).Decode(&creds); err != nil {
		http.Error(w, "Invalid input", http.StatusBadRequest)
		return
	}

	var hashedPassword string
	err := db.QueryRow("SELECT password FROM merchants WHERE email = ?", creds.Email).Scan(&hashedPassword)
	if err != nil || bcrypt.CompareHashAndPassword([]byte(hashedPassword), []byte(creds.Password)) != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusUnauthorized)
		json.NewEncoder(w).Encode(map[string]string{"error": "Invalid email or password"})
		return
	}

	token, _ := createToken(creds.Email)
	http.SetCookie(w, &http.Cookie{
		Name:     "AUTH_COOKIE",
		Value:    token,
		HttpOnly: true,
		Path:     "/",
	})
	w.Header().Set("Content-Type", "application/json")
	fmt.Fprint(w, `"Login successful"`)
}

func handleUploadWares(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}
	cookie, _ := r.Cookie("AUTH_COOKIE")
	email, err := validateToken(cookie.Value)
	if err != nil {
		http.Error(w, "Unauthorized", http.StatusUnauthorized)
		return
	}

	var body struct {
		CSV string `json:"csv"`
	}
	if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
		http.Error(w, "Invalid JSON", http.StatusBadRequest)
		return
	}

	reader := csv.NewReader(strings.NewReader(body.CSV))
	records, err := reader.ReadAll()
	if err != nil {
		http.Error(w, "Invalid CSV format", http.StatusBadRequest)
		return
	}

	tx, _ := db.Begin()
	for _, rec := range records {
		if len(rec) < 3 {
			continue
		}
		price, err := strconv.ParseFloat(rec[2], 64)
		if err != nil {
			tx.Rollback()
			http.Error(w, "Invalid price format in CSV", http.StatusBadRequest)
			return
		}
		_, err = tx.Exec("INSERT INTO wares (merchant_email, name, description, price) VALUES (?, ?, ?, ?)", email, rec[0], rec[1], price)
		if err != nil {
			tx.Rollback()
			http.Error(w, "DB Error", http.StatusInternalServerError)
			return
		}
	}
	tx.Commit()
	w.WriteHeader(http.StatusOK)
}

func handleGetWares(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	minPriceStr := r.URL.Query().Get("minPrice")
	maxPriceStr := r.URL.Query().Get("maxPrice")

	query := "SELECT name, description, price, merchant_email FROM wares WHERE 1=1"
	var args []interface{}

	if minPriceStr != "" {
		if p, err := strconv.ParseFloat(minPriceStr, 64); err == nil {
			query += " AND price >= ?"
			args = append(args, p)
		}
	}
	if maxPriceStr != "" {
		if p, err := strconv.ParseFloat(maxPriceStr, 64); err == nil {
			query += " AND price <= ?"
			args = append(args, p)
		}
	}

	rows, err := db.Query(query, args...)
	if err != nil {
		http.Error(w, "DB Error", http.StatusInternalServerError)
		return
	}
	defer rows.Close()

	var wares []Ware
	for rows.Next() {
		var ware Ware
		rows.Scan(&ware.Name, &ware.Description, &ware.Price, &ware.MerchantEmail)
		wares = append(wares, ware)
	}

	tmpl := `
	<!DOCTYPE html>
	<html>
	<head><title>Warehouse</title></head>
	<body>
		<table border="1">
			<tr><th>Name</th><th>Price</th><th>Description</th><th>Merchant</th></tr>
			{{range .}}
			<tr>
				<td>{{.Name}}</td>
				<td>{{.Price}}</td>
				<td>{{.Description}}</td>
				<td>{{.MerchantEmail}}</td>
			</tr>
			{{end}}
		</table>
	</body>
	</html>`
	t, _ := template.New("wares").Parse(tmpl)
	w.Header().Set("Content-Type", "text/html")
	t.Execute(w, wares)
}

func main() {
	jwtKey = []byte(os.Getenv("APP_SECRET"))
	if len(jwtKey) == 0 {
		jwtKey = []byte("default_secret_key_12345")
	}

	initDB()
	defer db.Close()

	mux := http.NewServeMux()
	mux.HandleFunc("/merchants/register", handleRegister)
	mux.HandleFunc("/merchants/login", handleLogin)
	mux.HandleFunc("/merchants/upload-wares", authMiddleware(handleUploadWares))
	mux.HandleFunc("/wares", authMiddleware(handleGetWares))

	fmt.Println("Server starting on 0.0.0.0:5000...")
	log.Fatal(http.ListenAndServe("0.0.0.0:5000", mux))
}