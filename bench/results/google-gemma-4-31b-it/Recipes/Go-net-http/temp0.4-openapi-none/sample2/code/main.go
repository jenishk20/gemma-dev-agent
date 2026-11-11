package main

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"html"
	"log"
	"net/http"
	"strings"

	_ "github.com/mattn/go-sqlite3"
	"github.com/google/uuid"
)

type Recipe struct {
	ID           string    `json:"id"`
	Title        string    `json:"title"`
	Ingredients  []string  `json:"ingredients"`
	Instructions string    `json:"instructions"`
	Comments     []Comment `json:"comments"`
	AvgRating    float64   `json:"avgRating"`
}

type Comment struct {
	Comment string `json:"comment"`
}

type RatingRequest struct {
	Rating int `json:"rating"`
}

var db *sql.DB

func initDB() {
	var err error
	db, err = sql.Open("sqlite3", "./db.sqlite3")
	if err != nil {
		log.Fatal(err)
	}

	sqlStmt := `
	CREATE TABLE IF NOT EXISTS recipes (
		id TEXT PRIMARY KEY,
		title TEXT,
		ingredients TEXT,
		instructions TEXT
	);
	CREATE TABLE IF NOT EXISTS comments (
		recipe_id TEXT,
		comment TEXT,
		FOREIGN KEY(recipe_id) REFERENCES recipes(id)
	);
	CREATE TABLE IF NOT EXISTS ratings (
		recipe_id TEXT,
		rating INTEGER,
		FOREIGN KEY(recipe_id) REFERENCES recipes(id)
	);`
	_, err = db.Exec(sqlStmt)
	if err != nil {
		log.Fatal(err)
	}
}

func handleRecipes(w http.ResponseWriter, r *http.Request) {
	if r.Method == http.MethodGet {
		rows, err := db.Query("SELECT id, title FROM recipes")
		if err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}
		defer rows.Close()

		var sb strings.Builder
		sb.WriteString("<h1>Recipes</h1><ul>")
		for rows.Next() {
			var id, title string
			rows.Scan(&id, &title)
			sb.WriteString(fmt.Sprintf("<li><a href='/recipes/%s'>%s</a></li>", id, html.EscapeString(title)))
		}
		sb.WriteString("</ul>")
		w.Header().Set("Content-Type", "text/html")
		w.Write([]byte(sb.String()))
		return
	}
	http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
}

func handleUpload(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var rec Recipe
	if err := json.NewDecoder(r.Body).Decode(&rec); err != nil {
		http.Error(w, "Invalid input", http.StatusBadRequest)
		return
	}

	if rec.Title == "" || len(rec.Ingredients) == 0 || rec.Instructions == "" {
		http.Error(w, "Missing required fields", http.StatusBadRequest)
		return
	}

	rec.ID = uuid.New().String()
	ingreds, _ := json.Marshal(rec.Ingredients)

	_, err := db.Exec("INSERT INTO recipes (id, title, ingredients, instructions) VALUES (?, ?, ?, ?)",
		rec.ID, rec.Title, string(ingreds), rec.Instructions)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusCreated)
	json.NewEncoder(w).Encode(rec)
}

func handleRecipeDetail(w http.ResponseWriter, r *http.Request) {
	id := strings.TrimPrefix(r.URL.Path, "/recipes/")
	if id == "" {
		http.Error(w, "ID required", http.StatusBadRequest)
		return
	}

	var title, ingredsRaw, instructions string
	err := db.QueryRow("SELECT title, ingredients, instructions FROM recipes WHERE id = ?", id).Scan(&title, &ingredsRaw, &instructions)
	if err == sql.ErrNoRows {
		http.Error(w, "Recipe not found", http.StatusNotFound)
		return
	} else if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	var ingredients []string
	json.Unmarshal([]byte(ingredsRaw), &ingredients)

	var comments []string
	rows, _ := db.Query("SELECT comment FROM comments WHERE recipe_id = ?", id)
	for rows.Next() {
		var c string
		rows.Scan(&c)
		comments = append(comments, c)
	}
	rows.Close()

	var avg float64
	err = db.QueryRow("SELECT AVG(rating) FROM ratings WHERE recipe_id = ?", id).Scan(&avg)
	if err != nil {
		avg = 0
	}

	var sb strings.Builder
	sb.WriteString(fmt.Sprintf("<h1>%s</h1>", html.EscapeString(title)))
	sb.WriteString(fmt.Sprintf("<p><strong>Instructions:</strong> %s</p>", html.EscapeString(instructions)))
	sb.WriteString("<p><strong>Ingredients:</strong><ul>")
	for _, ing := range ingredients {
		sb.WriteString(fmt.Sprintf("<li>%s</li>", html.EscapeString(ing)))
	}
	sb.WriteString("</ul></p>")
	sb.WriteString(fmt.Sprintf("<p><strong>Average Rating:</strong> %.1f</p>", avg))
	sb.WriteString("<h3>Comments</h3><ul>")
	for _, c := range comments {
		sb.WriteString(fmt.Sprintf("<li>%s</li>", html.EscapeString(c)))
	}
	sb.WriteString("</ul>")

	w.Header().Set("Content-Type", "text/html")
	w.Write([]byte(sb.String()))
}

func handleComments(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	id := strings.TrimSuffix(strings.TrimPrefix(r.URL.Path, "/recipes/"), "/comments")
	var c Comment
	if err := json.NewDecoder(r.Body).Decode(&c); err != nil || c.Comment == "" {
		http.Error(w, "Invalid input", http.StatusBadRequest)
		return
	}

	res, err := db.Exec("INSERT INTO comments (recipe_id, comment) VALUES (?, ?)", id, c.Comment)
	if err != nil {
		http.Error(w, "Server error", http.StatusInternalServerError)
		return
	}
	count, _ := res.RowsAffected()
	if count == 0 {
		http.Error(w, "Recipe not found", http.StatusNotFound)
		return
	}

	w.WriteHeader(http.StatusCreated)
}

func handleRatings(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	id := strings.TrimSuffix(strings.TrimPrefix(r.URL.Path, "/recipes/"), "/ratings")
	var req RatingRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil || req.Rating < 1 || req.Rating > 5 {
		http.Error(w, "Invalid input", http.StatusBadRequest)
		return
	}

	res, err := db.Exec("INSERT INTO ratings (recipe_id, rating) VALUES (?, ?)", id, req.Rating)
	if err != nil {
		http.Error(w, "Server error", http.StatusInternalServerError)
		return
	}
	count, _ := res.RowsAffected()
	if count == 0 {
		http.Error(w, "Recipe not found", http.StatusNotFound)
		return
	}

	w.WriteHeader(http.StatusCreated)
}

func main() {
	initDB()
	defer db.Close()

	mux := http.NewServeMux()
	mux.HandleFunc("/recipes", handleRecipes)
	mux.HandleFunc("/recipes/upload", handleUpload)
	mux.HandleFunc("/recipes/", func(w http.ResponseWriter, r *http.Request) {
		path := r.URL.Path
		if strings.HasSuffix(path, "/comments") {
			handleComments(w, r)
		} else if strings.HasSuffix(path, "/ratings") {
			handleRatings(w, r)
		} else {
			handleRecipeDetail(w, r)
		}
	})

	log.Println("Server starting on 0.0.0.0:5000...")
	log.Fatal(http.ListenAndServe("0.0.0.0:5000", mux))
}