package main

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"time"

	"github.com/golang-jwt/jwt/v5"
	_ "github.com/mattn/go-sqlite3"
	"golang.org/x/crypto/bcrypt"
)

type User struct {
	ID       int
	Email    string
	Password string
	Name     string
}

type LoginRequest struct {
	Email    string `json:"email"`
	Password string `json:"password"`
}

type RegisterRequest struct {
	Email    string `json:"email"`
	Password string `json:"password"`
	Name     string `json:"name"`
}

type Response struct {
	Message string `json:"message,omitempty"`
	Token   string `json:"token,omitempty"`
}

var db *sql.DB
var appSecret string

func initDB() {
	var err error
	db, err = sql.Open("sqlite3", "./db.sqlite3")
	if err != nil {
		log.Fatal(err)
	}

	sqlStmt := `
	CREATE TABLE IF NOT EXISTS users (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		email TEXT UNIQUE,
		password TEXT,
		name TEXT
	);`
	_, err = db.Exec(sqlStmt)
	if err != nil {
		log.Fatal(err)
	}
}

func main() {
	appSecret = os.Getenv("APP_SECRET")
	if appSecret == "" {
		appSecret = "default_secret_key"
	}

	initDB()
	defer db.Close()

	mux := http.NewServeMux()
	mux.HandleFunc("/login", handleLogin)
	mux.HandleFunc("/register", handleRegister)

	fmt.Println("Server starting on 0.0.0.0:5000...")
	log.Fatal(http.ListenAndServe("0.0.0.0:5000", mux))
}

func handleRegister(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var req RegisterRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		sendJSONResponse(w, http.StatusBadRequest, Response{Message: "Invalid request body"})
		return
	}

	if req.Email == "" || req.Password == "" || req.Name == "" {
		sendJSONResponse(w, http.StatusBadRequest, Response{Message: "Email, password, and name are required"})
		return
	}

	hashedPassword, err := bcrypt.GenerateFromPassword([]byte(req.Password), bcrypt.DefaultCost)
	if err != nil {
		sendJSONResponse(w, http.StatusInternalServerError, Response{Message: "Internal server error"})
		return
	}

	_, err = db.Exec("INSERT INTO users (email, password, name) VALUES (?, ?, ?)", req.Email, string(hashedPassword), req.Name)
	if err != nil {
		sendJSONResponse(w, http.StatusBadRequest, Response{Message: "Email already in use or invalid data"})
		return
	}

	sendJSONResponse(w, http.StatusCreated, Response{Message: "Registration successful"})
}

func handleLogin(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var req LoginRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		sendJSONResponse(w, http.StatusBadRequest, Response{Message: "Invalid request body"})
		return
	}

	var storedPassword string
	err := db.QueryRow("SELECT password FROM users WHERE email = ?", req.Email).Scan(&storedPassword)
	if err != nil {
		sendJSONResponse(w, http.StatusUnauthorized, Response{Message: "Invalid email or password"})
		return
	}

	err = bcrypt.CompareHashAndPassword([]byte(storedPassword), []byte(req.Password))
	if err != nil {
		sendJSONResponse(w, http.StatusUnauthorized, Response{Message: "Invalid email or password"})
		return
	}

	token, err := createJWT(req.Email)
	if err != nil {
		sendJSONResponse(w, http.StatusInternalServerError, Response{Message: "Could not generate token"})
		return
	}

	sendJSONResponse(w, http.StatusOK, Response{
		Token:   token,
		Message: "Login successful",
	})
}

func createJWT(email string) (string, error) {
	token := jwt.NewWithClaims(jwt.SigningMethodHS256, jwt.MapClaims{
		"email": email,
		"exp":   time.Now().Add(time.Hour * 24).Unix(),
	})

	return token.SignedString([]byte(appSecret))
}

func sendJSONResponse(w http.ResponseWriter, code int, payload Response) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(code)
	json.NewEncoder(w).Encode(payload)
}