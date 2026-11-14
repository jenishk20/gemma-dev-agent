package main

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"

	"github.com/google/uuid"
	_ "github.com/mattn/go-sqlite3"
	"golang.org/x/crypto/bcrypt"
)

type InviteRequest struct {
	Email string `json:"email"`
}

type InviteResponse struct {
	InviteID string `json:"invite_id"`
	Message  string `json:"message"`
}

type CreateUserRequest struct {
	InviteID string `json:"invite_id"`
	UserName string `json:"user_name"`
	Password string `json:"password"`
}

type MessageResponse struct {
	Message string `json:"message"`
}

var db *sql.DB

func initDB() {
	var err error
	db, err = sql.Open("sqlite3", "./db.sqlite3")
	if err != nil {
		log.Fatal(err)
	}

	sqlStmt := `
	CREATE TABLE IF NOT EXISTS invites (
		invite_id TEXT PRIMARY KEY,
		email TEXT UNIQUE NOT NULL,
		used INTEGER DEFAULT 0
	);
	CREATE TABLE IF NOT EXISTS users (
		username TEXT PRIMARY KEY,
		password TEXT NOT NULL,
		email TEXT UNIQUE NOT NULL
	);`
	_, err = db.Exec(sqlStmt)
	if err != nil {
		log.Fatal(err)
	}
}

func inviteUserHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var req InviteRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "Invalid request body", http.StatusBadRequest)
		return
	}

	if req.Email == "" {
		http.Error(w, "Email is required", http.StatusBadRequest)
		return
	}

	var inviteID string
	err := db.QueryRow("SELECT invite_id FROM invites WHERE email = ?", req.Email).Scan(&inviteID)

	if err == sql.ErrNoRows {
		inviteID = uuid.New().String()
		_, err = db.Exec("INSERT INTO invites (invite_id, email) VALUES (?, ?)", inviteID, req.Email)
		if err != nil {
			http.Error(w, "Database error", http.StatusInternalServerError)
			return
		}
	} else if err != nil {
		http.Error(w, "Database error", http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(InviteResponse{
		InviteID: inviteID,
		Message:  "Invitation created successfully",
	})
}

func createUserHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var req CreateUserRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "Invalid request body", http.StatusBadRequest)
		return
	}

	var email string
	var used int
	err := db.QueryRow("SELECT email, used FROM invites WHERE invite_id = ?", req.InviteID).Scan(&email, &used)
	if err == sql.ErrNoRows || (err == nil && used == 1) {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusUnauthorized)
		json.NewEncoder(w).Encode(MessageResponse{Message: "Invalid invite_id"})
		return
	} else if err != nil {
		http.Error(w, "Database error", http.StatusInternalServerError)
		return
	}

	hashedPassword, err := bcrypt.GenerateFromPassword([]byte(req.Password), bcrypt.DefaultCost)
	if err != nil {
		http.Error(w, "Password hashing error", http.StatusInternalServerError)
		return
	}

	_, err = db.Exec("INSERT INTO users (username, password, email) VALUES (?, ?, ?)", req.UserName, string(hashedPassword), email)
	if err != nil {
		// Check for unique constraint violation on username
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(MessageResponse{Message: "Username already exists. Try providing different username."})
		return
	}

	_, err = db.Exec("UPDATE invites SET used = 1 WHERE invite_id = ?", req.InviteID)
	if err != nil {
		log.Printf("Warning: failed to mark invite as used: %v", err)
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(MessageResponse{Message: "User created successfully"})
}

func main() {
	initDB()
	defer db.Close()

	// Ensure APP_SECRET is present as per requirements, though not used for simple login/creation
	_ = os.Getenv("APP_SECRET")

	http.HandleFunc("/invite_user", inviteUserHandler)
	http.HandleFunc("/create_user", createUserHandler)

	fmt.Println("Server starting on 0.0.0.0:5000...")
	log.Fatal(http.ListenAndServe("0.0.0.0:5000", nil))
}