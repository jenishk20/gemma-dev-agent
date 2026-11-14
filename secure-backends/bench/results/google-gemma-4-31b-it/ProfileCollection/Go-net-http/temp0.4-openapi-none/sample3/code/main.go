package main

import (
	"database/sql"
	"fmt"
	"io"
	"log"
	"net/http"
	"strings"

	_ "github.com/mattn/go-sqlite3"
)

var db *sql.DB

func initDB() {
	var err error
	db, err = sql.Open("sqlite3", "./db.sqlite3")
	if err != nil {
		log.Fatal(err)
	}

	sqlStmt := `
	CREATE TABLE IF NOT EXISTS profiles (
		username TEXT PRIMARY KEY,
		profile_page TEXT,
		profile_photo BLOB
	);`
	_, err = db.Exec(sqlStmt)
	if err != nil {
		log.Fatal(err)
	}
}

func handleAddProfile(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	// Parse multipart form
	err := r.ParseMultipartForm(10 << 20) // 10MB limit
	if err != nil {
		http.Error(w, "Invalid input", http.StatusBadRequest)
		return
	}

	username := r.FormValue("username")
	profilePage := r.FormValue("profile_page")

	if username == "" || profilePage == "" {
		http.Error(w, "Username and profile page are required", http.StatusBadRequest)
		return
	}

	file, header, err := r.FormFile("profile_photo")
	if err != nil {
		http.Error(w, "Profile photo is required", http.StatusBadRequest)
		return
	}
	defer file.Close()

	// Basic validation for PNG
	if !strings.HasSuffix(strings.ToLower(header.Filename), ".png") {
		http.Error(w, "Only PNG files are allowed", http.StatusBadRequest)
		return
	}

	photoBytes, err := io.ReadAll(file)
	if err != nil {
		http.Error(w, "Error reading photo", http.StatusInternalServerError)
		return
	}

	_, err = db.Exec("INSERT INTO profiles (username, profile_page, profile_photo) VALUES (?, ?, ?)", username, profilePage, photoBytes)
	if err != nil {
		if strings.Contains(err.Error(), "UNIQUE constraint failed") {
			http.Error(w, "Profile already exists", http.StatusForbidden)
			return
		}
		http.Error(w, "Database error", http.StatusInternalServerError)
		return
	}

	w.WriteHeader(http.StatusCreated)
}

func handleGetProfile(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	username := strings.TrimPrefix(r.URL.Path, "/profile/")
	if username == "" {
		http.Error(w, "Username required", http.StatusBadRequest)
		return
	}

	var profilePage string
	err := db.QueryRow("SELECT profile_page FROM profiles WHERE username = ?", username).Scan(&profilePage)
	if err == sql.ErrNoRows {
		http.Error(w, "Profile not found", http.StatusNotFound)
		return
	} else if err != nil {
		http.Error(w, "Database error", http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "text/html")
	fmt.Fprint(w, profilePage)
}

func handleGetPhoto(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	username := strings.TrimPrefix(r.URL.Path, "/profile-photo/")
	if username == "" {
		http.Error(w, "Username required", http.StatusBadRequest)
		return
	}

	var photoBytes []byte
	err := db.QueryRow("SELECT profile_photo FROM profiles WHERE username = ?", username).Scan(&photoBytes)
	if err == sql.ErrNoRows {
		http.Error(w, "Photo not found", http.StatusNotFound)
		return
	} else if err != nil {
		http.Error(w, "Database error", http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "image/png")
	w.Write(photoBytes)
}

func main() {
	initDB()
	defer db.Close()

	mux := http.NewServeMux()
	mux.HandleFunc("/add_profile", handleAddProfile)
	mux.HandleFunc("/profile/", handleGetProfile)
	mux.HandleFunc("/profile-photo/", handleGetPhoto)

	fmt.Println("Server starting on 0.0.0.0:5000...")
	log.Fatal(http.ListenAndServe("0.0.0.0:5000", mux))
}