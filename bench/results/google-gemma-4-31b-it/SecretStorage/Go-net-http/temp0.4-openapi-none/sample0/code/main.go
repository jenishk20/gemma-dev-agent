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

type ResponseMessage struct {
	Message string `json:"message"`
}

type TokenResponse struct {
	Token   string `json:"token"`
	Message string `json:"message"`
}

type SecretResponse struct {
	Secret string `json:"secret"`
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

func validateJWT(r *http.Request) (string, error) {
	authHeader := r.Header.Get("Authorization")
	if authHeader == "" {
		return "", fmt.Errorf("missing token")
	}
	tokenStr := authHeader[len("Bearer "):]
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
	return claims["username"].(string), nil
}

func registerHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}
	var u User
	if err := json.NewDecoder(r.Body).Decode(&u); err != nil {
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(ResponseMessage{Message: "Invalid data"})
		return
	}
	hashedPassword, _ := bcrypt.GenerateFromPassword([]byte(u.Password), bcrypt.DefaultCost)
	_, err := db.Exec("INSERT INTO users (email, username, password) VALUES (?, ?, ?)", u.Email, u.Username, string(hashedPassword))
	if err != nil {
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(ResponseMessage{Message: "Email already in use or invalid data"})
		return
	}
	w.WriteHeader(http.StatusCreated)
	json.NewEncoder(w).Encode(ResponseMessage{Message: "Registration successful"})
}

func loginHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}
	var lr LoginRequest
	if err := json.NewDecoder(r.Body).Decode(&lr); err != nil {
		w.WriteHeader(http.StatusBadRequest)
		return
	}
	var username, hashedPassword string
	err := db.QueryRow("SELECT username, password FROM users WHERE email = ?", lr.Email).Scan(&username, &hashedPassword)
	if err != nil || bcrypt.CompareHashAndPassword([]byte(hashedPassword), []byte(lr.Password)) != nil {
		w.WriteHeader(http.StatusUnauthorized)
		json.NewEncoder(w).Encode(ResponseMessage{Message: "Invalid email or password"})
		return
	}
	token, _ := generateJWT(username)
	json.NewEncoder(w).Encode(TokenResponse{Token: token, Message: "Login successful"})
}

func setSecretHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}
	authUsername, err := validateJWT(r)
	if err != nil {
		w.WriteHeader(http.StatusUnauthorized)
		json.NewEncoder(w).Encode(ResponseMessage{Message: "Invalid authentication token"})
		return
	}
	var sr SecretRequest
	if err := json.NewDecoder(r.Body).Decode(&sr); err != nil {
		w.WriteHeader(http.StatusBadRequest)
		return
	}
	if sr.Username != authUsername {
		w.WriteHeader(http.StatusUnauthorized)
		json.NewEncoder(w).Encode(ResponseMessage{Message: "Invalid authentication token"})
		return
	}
	_, err = db.Exec("INSERT OR REPLACE INTO secrets (username, secret_value) VALUES (?, ?)", sr.Username, sr.Secret)
	if err != nil {
		http.Error(w, "Internal server error", http.StatusInternalServerError)
		return
	}
	json.NewEncoder(w).Encode(ResponseMessage{Message: "Secret has been set successfully"})
}

func getSecretHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}
	authUsername, err := validateJWT(r)
	if err != nil {
		w.WriteHeader(http.StatusUnauthorized)
		json.NewEncoder(w).Encode(ResponseMessage{Message: "Invalid authentication token"})
		return
	}
	username := r.URL.Query().Get("username")
	if username == "" || username != authUsername {
		w.WriteHeader(http.StatusUnauthorized)
		json.NewEncoder(w).Encode(ResponseMessage{Message: "Invalid authentication token"})
		return
	}
	var secret string
	err = db.QueryRow("SELECT secret_value FROM secrets WHERE username = ?", username).Scan(&secret)
	if err != nil {
		w.WriteHeader(http.StatusUnauthorized)
		json.NewEncoder(w).Encode(ResponseMessage{Message: "Invalid authentication token"})
		return
	}
	json.NewEncoder(w).Encode(SecretResponse{Secret: secret})
}

func main() {
	jwtKey = []byte(os.Getenv("APP_SECRET"))
	if len(jwtKey) == 0 {
		jwtKey = []byte("default_secret_key")
	}
	initDB()
	defer db.Close()

	mux := http.NewServeMux()
	mux.HandleFunc("/register", registerHandler)
	mux.HandleFunc("/login", loginHandler)
	mux.HandleFunc("/set_secret", setSecretHandler)
	mux.HandleFunc("/get_secret", getSecretHandler)

	log.Println("Server starting on 0.0.0.0:5000...")
	log.Fatal(http.ListenAndServe("0.0.0.0:5000", mux))
}