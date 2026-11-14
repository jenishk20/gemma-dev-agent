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
	Token   string `json:"token,omitempty"`
	Message string `json:"message"`
}

var db *sql.DB
var appSecret []byte

func main() {
	var err error
	appSecret = []byte(os.Getenv("APP_SECRET"))
	if len(appSecret) == 0 {
		appSecret = []byte("default_secret_for_dev")
	}

	db, err = sql.Open("sqlite3", "./db.sqlite3")
	if err != nil {
		log.Fatal(err)
	}
	defer db.Close()

	createTable := `CREATE TABLE IF NOT EXISTS users (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		email TEXT UNIQUE NOT NULL,
		password TEXT NOT NULL,
		name TEXT NOT NULL
	);`
	if _, err := db.Exec(createTable); err != nil {
		log.Fatal(err)
	}

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
		sendJSON(w, http.StatusBadRequest, Response{Message: "Invalid request body"})
		return
	}

	if req.Email == "" || req.Password == "" || req.Name == "" {
		sendJSON(w, http.StatusBadRequest, Response{Message: "Missing required fields"})
		return
	}

	hashedPassword, err := bcrypt.GenerateFromPassword([]byte(req.Password), bcrypt.DefaultCost)
	if err != nil {
		sendJSON(w, http.StatusInternalServerError, Response{Message: "Internal server error"})
		return
	}

	_, err = db.Exec("INSERT INTO users (email, password, name) VALUES (?, ?, ?)", req.Email, string(hashedPassword), req.Name)
	if err != nil {
		sendJSON(w, http.StatusBadRequest, Response{Message: "Email already in use or invalid data"})
		return
	}

	sendJSON(w, http.StatusCreated, Response{Message: "Registration successful"})
}

func handleLogin(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var req LoginRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		sendJSON(w, http.StatusBadRequest, Response{Message: "Invalid request body"})
		return
	}

	var storedHash string
	err := db.QueryRow("SELECT password FROM users WHERE email = ?", req.Email).Scan(&storedHash)
	if err != nil {
		sendJSON(w, http.StatusUnauthorized, Response{Message: "Invalid email or password"})
		return
	}

	if err := bcrypt.CompareHashAndPassword([]byte(storedHash), []byte(req.Password)); err != nil {
		sendJSON(w, http.StatusUnauthorized, Response{Message: "Invalid email or password"})
		return
	}

	token, err := createJWT(req.Email)
	if err != nil {
		sendJSON(w, http.StatusInternalServerError, Response{Message: "Could not generate token"})
		return
	}

	sendJSON(w, http.StatusOK, Response{
		Token:   token,
		Message: "Login successful",
	})
}

func createJWT(email string) (string, error) {
	claims := jwt.MapClaims{
		"email": email,
		"exp":   time.Now().Add(time.Hour * 24).Unix(),
	}
	token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
	return token.SignedString(appSecret)
}

func sendJSON(w http.ResponseWriter, status int, payload Response) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(payload)
}