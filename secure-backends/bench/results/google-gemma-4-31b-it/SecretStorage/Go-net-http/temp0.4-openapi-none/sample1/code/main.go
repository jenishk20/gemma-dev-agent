package main

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"strings"
	"time"

	"github.com/golang-jwt/jwt/v5"
	_ "github.com/mattn/go-sqlite3"
	"golang.org/x/crypto/bcrypt"
)

var db *sql.DB
var jwtKey []byte

type User struct {
	Email    string `json:"email"`
	Username string `json:"username"`
	Password string `json:"password"`
}

type LoginRequest struct {
	Email    string `json:"email"`
	Password string `json:"password"`
}

type SecretRequest struct {
	Username string `json:"username"`
	Secret   string `json:"secret"`
}

type Response struct {
	Message string `json:"message,omitempty"`
	Token   string `json:"token,omitempty"`
	Secret  string `json:"secret,omitempty"`
}

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
		username TEXT UNIQUE,
		password TEXT
	);
	CREATE TABLE IF NOT EXISTS secrets (
		username TEXT PRIMARY KEY,
		secret_value TEXT,
		FOREIGN KEY(username) REFERENCES users(username)
	);`
	_, err = db.Exec(sqlStmt)
	if err != nil {
		log.Fatal(err)
	}
}

func generateJWT(username string) (string, error) {
	token := jwt.NewWithClaims(jwt.SigningMethodHS256, jwt.MapClaims{
		"username": username,
		"exp":      time.Now().Add(time.Hour * 24).Unix(),
	})
	return token.SignedString(jwtKey)
}

func validateJWT(tokenStr string) (string, error) {
	tokenStr = strings.TrimPrefix(tokenStr, "Bearer ")
	token, err := jwt.Parse(tokenStr, func(token *jwt.Token) (interface{}, error) {
		return jwtKey, nil
	})

	if err != nil || !token.Valid {
		return "", fmt.Errorf("invalid token")
	}

	if claims, ok := token.Claims.(jwt.MapClaims); ok {
		return claims["username"].(string), nil
	}
	return "", fmt.Errorf("invalid claims")
}

func registerHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var user User
	if err := json.NewDecoder(r.Body).Decode(&user); err != nil {
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(Response{Message: "Invalid data"})
		return
	}

	hashedPassword, _ := bcrypt.GenerateFromPassword([]byte(user.Password), bcrypt.DefaultCost)
	_, err := db.Exec("INSERT INTO users (email, username, password) VALUES (?, ?, ?)", user.Email, user.Username, string(hashedPassword))
	if err != nil {
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(Response{Message: "Email already in use or invalid data"})
		return
	}

	w.WriteHeader(http.StatusCreated)
	json.NewEncoder(w).Encode(Response{Message: "Registration successful"})
}

func loginHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var creds LoginRequest
	if err := json.NewDecoder(r.Body).Decode(&creds); err != nil {
		http.Error(w, "Bad request", http.StatusBadRequest)
		return
	}

	var hashedPassword string
	var username string
	err := db.QueryRow("SELECT password, username FROM users WHERE email = ?", creds.Email).Scan(&hashedPassword, &username)
	if err != nil {
		w.WriteHeader(http.StatusUnauthorized)
		json.NewEncoder(w).Encode(Response{Message: "Invalid email or password"})
		return
	}

	if err := bcrypt.CompareHashAndPassword([]byte(hashedPassword), []byte(creds.Password)); err != nil {
		w.WriteHeader(http.StatusUnauthorized)
		json.NewEncoder(w).Encode(Response{Message: "Invalid email or password"})
		return
	}

	token, err := generateJWT(username)
	if err != nil {
		http.Error(w, "Internal server error", http.StatusInternalServerError)
		return
	}

	json.NewEncoder(w).Encode(Response{Token: token, Message: "Login successful"})
}

func setSecretHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	authHeader := r.Header.Get("Authorization")
	usernameFromToken, err := validateJWT(authHeader)
	if err != nil {
		w.WriteHeader(http.StatusUnauthorized)
		json.NewEncoder(w).Encode(Response{Message: "Invalid authentication token"})
		return
	}

	var req SecretRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "Bad request", http.StatusBadRequest)
		return
	}

	if req.Username != usernameFromToken {
		w.WriteHeader(http.StatusUnauthorized)
		json.NewEncoder(w).Encode(Response{Message: "Invalid authentication token"})
		return
	}

	_, err = db.Exec("INSERT OR REPLACE INTO secrets (username, secret_value) VALUES (?, ?)", req.Username, req.Secret)
	if err != nil {
		http.Error(w, "Internal server error", http.StatusInternalServerError)
		return
	}

	json.NewEncoder(w).Encode(Response{Message: "Secret has been set successfully"})
}

func getSecretHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	authHeader := r.Header.Get("Authorization")
	usernameFromToken, err := validateJWT(authHeader)
	if err != nil {
		w.WriteHeader(http.StatusUnauthorized)
		json.NewEncoder(w).Encode(Response{Message: "Invalid authentication token"})
		return
	}

	usernameQuery := r.URL.Query().Get("username")
	if usernameQuery == "" || usernameQuery != usernameFromToken {
		w.WriteHeader(http.StatusUnauthorized)
		json.NewEncoder(w).Encode(Response{Message: "Invalid authentication token"})
		return
	}

	var secretValue string
	err = db.QueryRow("SELECT secret_value FROM secrets WHERE username = ?", usernameQuery).Scan(&secretValue)
	if err != nil {
		w.WriteHeader(http.StatusUnauthorized)
		json.NewEncoder(w).Encode(Response{Message: "Invalid authentication token"})
		return
	}

	json.NewEncoder(w).Encode(Response{Secret: secretValue})
}

func main() {
	secret := os.Getenv("APP_SECRET")
	if secret == "" {
		secret = "default_secret_key"
	}
	jwtKey = []byte(secret)

	initDB()
	defer db.Close()

	mux := http.NewServeMux()
	mux.HandleFunc("/register", registerHandler)
	mux.HandleFunc("/login", loginHandler)
	mux.HandleFunc("/set_secret", setSecretHandler)
	mux.HandleFunc("/get_secret", getSecretHandler)

	fmt.Println("Server starting on 0.0.0.0:5000...")
	log.Fatal(http.ListenAndServe("0.0.0.0:5000", mux))
}