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

type ProfileStore struct {
	db *sql.DB
}

func NewProfileStore(dbPath string) (*ProfileStore, error) {
	db, err := sql.Open("sqlite3", dbPath)
	if err != nil {
		return nil, err
	}

	query := `
	CREATE TABLE IF NOT EXISTS profiles (
		username TEXT PRIMARY KEY,
		profile_page TEXT,
		profile_photo BLOB
	);`
	if _, err := db.Exec(query); err != nil {
		return nil, err
	}

	return &ProfileStore{db: db}, nil
}

func (s *ProfileStore) AddProfile(username, page string, photo []byte) error {
	_, err := s.db.Exec("INSERT INTO profiles (username, profile_page, profile_photo) VALUES (?, ?, ?)", username, page, photo)
	return err
}

func (s *ProfileStore) GetProfile(username string) (string, error) {
	var page string
	err := s.db.QueryRow("SELECT profile_page FROM profiles WHERE username = ?", username).Scan(&page)
	return page, err
}

func (s *ProfileStore) GetPhoto(username string) ([]byte, error) {
	var photo []byte
	err := s.db.QueryRow("SELECT profile_photo FROM profiles WHERE username = ?", username).Scan(&photo)
	return photo, err
}

func main() {
	store, err := NewProfileStore("./db.sqlite3")
	if err != nil {
		log.Fatal(err)
	}

	mux := http.NewServeMux()

	mux.HandleFunc("/add_profile", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			http.Error(w, "Method Not Allowed", http.StatusMethodNotAllowed)
			return
		}

		err := r.ParseMultipartForm(10 << 20) // 10MB
		if err != nil {
			http.Error(w, "Invalid input", http.StatusBadRequest)
			return
		}

		username := r.FormValue("username")
		profilePage := r.FormValue("profile_page")
		photoFile, _, err := r.FormFile("profile_photo")
		if err != nil {
			http.Error(w, "Missing profile photo", http.StatusBadRequest)
			return
		}
		defer photoFile.Close()

		photoBytes, err := io.ReadAll(photoFile)
		if err != nil {
			http.Error(w, "Error reading photo", http.StatusInternalServerError)
			return
		}

		if username == "" || profilePage == "" {
			http.Error(w, "Invalid input", http.StatusBadRequest)
			return
		}

		err = store.AddProfile(username, profilePage, photoBytes)
		if err != nil {
			if strings.Contains(err.Error(), "UNIQUE constraint failed") {
				http.Error(w, "Profile already exists", http.StatusForbidden)
			} else {
				http.Error(w, "Internal server error", http.StatusInternalServerError)
			}
			return
		}

		w.WriteHeader(http.StatusCreated)
	})

	mux.HandleFunc("/profile/", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodGet {
			http.Error(w, "Method Not Allowed", http.StatusMethodNotAllowed)
			return
		}

		username := strings.TrimPrefix(r.URL.Path, "/profile/")
		if username == "" {
			http.Error(w, "Username required", http.StatusBadRequest)
			return
		}

		page, err := store.GetProfile(username)
		if err == sql.ErrNoRows {
			http.Error(w, "Profile not found", http.StatusNotFound)
			return
		} else if err != nil {
			http.Error(w, "Internal server error", http.StatusInternalServerError)
			return
		}

		w.Header().Set("Content-Type", "text/html")
		fmt.Fprint(w, page)
	})

	mux.HandleFunc("/profile-photo/", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodGet {
			http.Error(w, "Method Not Allowed", http.StatusMethodNotAllowed)
			return
		}

		username := strings.TrimPrefix(r.URL.Path, "/profile-photo/")
		if username == "" {
			http.Error(w, "Username required", http.StatusBadRequest)
			return
		}

		photo, err := store.GetPhoto(username)
		if err == sql.ErrNoRows {
			http.Error(w, "Photo not found", http.StatusNotFound)
			return
		} else if err != nil {
			http.Error(w, "Internal server error", http.StatusInternalServerError)
			return
		}

		w.Header().Set("Content-Type", "image/png")
		w.Write(photo)
	})

	log.Println("Server starting on 0.0.0.0:5000")
	if err := http.ListenAndServe("0.0.0.0:5000", mux); err != nil {
		log.Fatal(err)
	}
}