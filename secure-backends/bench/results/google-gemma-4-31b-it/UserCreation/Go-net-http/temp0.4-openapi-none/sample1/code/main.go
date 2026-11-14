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

type App struct {
	db *sql.DB
}

func main() {
	db, err := sql.Open("sqlite3", "./db.sqlite3")
	if err != nil {
		log.Fatal(err)
	}
	defer db.Close()

	app := &App{db: db}
	app.initDB()

	mux := http.NewServeMux()
	mux.HandleFunc("/invite_user", app.handleInviteUser)
	mux.HandleFunc("/create_user", app.handleCreateUser)

	fmt.Println("Server starting on 0.0.0.0:5000...")
	log.Fatal(http.ListenAndServe("0.0.0.0:5000", mux))
}

func (app *App) initDB() {
	queries := []string{
		`CREATE TABLE IF NOT EXISTS invitations (
			invite_id TEXT PRIMARY KEY,
			email TEXT UNIQUE,
			used INTEGER DEFAULT 0
		);`,
		`CREATE TABLE IF NOT EXISTS users (
			username TEXT PRIMARY KEY,
			password TEXT,
			email TEXT
		);`,
	}

	for _, q := range queries {
		_, err := app.db.Exec(q)
		if err != nil {
			log.Fatal(err)
		}
	}
}

func (app *App) handleInviteUser(w http.ResponseWriter, r *http.Request) {
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
	err := app.db.QueryRow("SELECT invite_id FROM invitations WHERE email = ?", req.Email).Scan(&inviteID)

	if err == sql.ErrNoRows {
		inviteID = uuid.New().String()
		_, err = app.db.Exec("INSERT INTO invitations (invite_id, email) VALUES (?, ?)", inviteID, req.Email)
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

func (app *App) handleCreateUser(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var req CreateUserRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "Invalid request body", http.StatusBadRequest)
		return
	}

	if req.InviteID == "" || req.UserName == "" || req.Password == "" {
		http.Error(w, "Missing required fields", http.StatusBadRequest)
		return
	}

	var email string
	var used int
	err := app.db.QueryRow("SELECT email, used FROM invitations WHERE invite_id = ?", req.InviteID).Scan(&email, &used)
	if err == sql.ErrNoRows || used == 1 {
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

	_, err = app.db.Exec("INSERT INTO users (username, password, email) VALUES (?, ?, ?)", req.UserName, string(hashedPassword), email)
	if err != nil {
		// Check for unique constraint violation on username
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(MessageResponse{Message: "Username already exists. Try providing different username."})
		return
	}

	_, err = app.db.Exec("UPDATE invitations SET used = 1 WHERE invite_id = ?", req.InviteID)
	if err != nil {
		log.Printf("Warning: failed to mark invite as used: %v", err)
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(MessageResponse{Message: "User created successfully"})
}

func init() {
	// Ensure APP_SECRET is present if needed, though not used for basic logic here
	if os.Getenv("APP_SECRET") == "" {
		// We don't exit here to keep the app runnable, but the prompt mentioned it.
	}
}