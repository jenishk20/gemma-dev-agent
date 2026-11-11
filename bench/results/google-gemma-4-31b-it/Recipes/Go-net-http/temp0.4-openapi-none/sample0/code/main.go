package main

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"html/template"
	"log"
	"net/http"
	"strconv"
	"strings"

	_ "github.com/mattn/go-sqlite3"
	"github.com/google/uuid"
)

// Models
type Recipe struct {
	ID           string    `json:"id"`
	Title        string    `json:"title"`
	Ingredients  []string `json:"ingredients"`
	Instructions string    `json:"instructions"`
	Comments     []Comment `json:"comments"`
	AvgRating    *float64  `json:"avgRating"`
}

type Comment struct {
	Comment string `json:"comment"`
}

type RatingRequest struct {
	Rating int `json:"rating"`
}

type CommentRequest struct {
	Comment string `json:"comment"`
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
		content TEXT,
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

func main() {
	initDB()
	defer db.Close()

	mux := http.NewServeMux()

	mux.HandleFunc("/recipes", handleRecipes)
	mux.HandleFunc("/recipes/upload", handleUpload)
	mux.HandleFunc("/recipes/", handleRecipeDetail) // Handles /recipes/{id}, /recipes/{id}/comments, /recipes/{id}/ratings

	fmt.Println("Server starting on 0.0.0.0:5000")
	log.Fatal(http.ListenAndServe("0.0.0.0:5000", mux))
}

func handleRecipes(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	rows, err := db.Query("SELECT id, title FROM recipes")
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	defer rows.Close()

	var html strings.Builder
	html.WriteString("<html><body><h1>Recipes</h1><ul>")
	for rows.Next() {
		var id, title string
		if err := rows.Scan(&id, &title); err != nil {
			continue
		}
		html.WriteString(fmt.Sprintf("<li><a href='/recipes/%s'>%s</a></li>", id, title))
	}
	html.WriteString("</ul></body></html>")

	w.Header().Set("Content-Type", "text/html")
	w.Write([]byte(html.String()))
}

func handleUpload(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var req Recipe
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "Invalid input", http.StatusBadRequest)
		return
	}

	if req.Title == "" || len(req.Ingredients) == 0 || req.Instructions == "" {
		http.Error(w, "Missing required fields", http.StatusBadRequest)
		return
	}

	id := uuid.New().String()
	ingreds := strings.Join(req.Ingredients, ",")
	_, err := db.Exec("INSERT INTO recipes (id, title, ingredients, instructions) VALUES (?, ?, ?, ?)", id, req.Title, ingreds, req.Instructions)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	req.ID = id
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusCreated)
	json.NewEncoder(w).Encode(req)
}

func handleRecipeDetail(w http.ResponseWriter, r *http.Request) {
	path := strings.TrimPrefix(r.URL.Path, "/recipes/")
	parts := strings.Split(path, "/")
	recipeID := parts[0]

	if recipeID == "" {
		http.NotFound(w, r)
		return
	}

	// Route to specific actions
	if len(parts) > 1 {
		action := parts[1]
		if action == "comments" && r.Method == http.MethodPost {
			handleAddComment(w, r, recipeID)
			return
		} else if action == "ratings" && r.Method == http.MethodPost {
			handleAddRating(w, r, recipeID)
			return
		}
	}

	if r.Method != http.MethodGet {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	// Get Recipe
	var title, ingreds, instructions string
	err := db.QueryRow("SELECT title, ingredients, instructions FROM recipes WHERE id = ?", recipeID).Scan(&title, &ingreds, &instructions)
	if err == sql.ErrNoRows {
		http.NotFound(w, r)
		return
	} else if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	// Get Comments
	rows, _ := db.Query("SELECT content FROM comments WHERE recipe_id = ?", recipeID)
	var comments []string
	for rows.Next() {
		var c string
		rows.Scan(&c)
		comments = append(comments, c)
	}
	rows.Close()

	// Get Avg Rating
	var avg float64
	err = db.QueryRow("SELECT AVG(rating) FROM ratings WHERE recipe_id = ?", recipeID).Scan(&avg)
	if err != nil {
		avg = 0
	}

	tmpl := `<html><body>
		<h1>{{.Title}}</h1>
		<p><strong>Ingredients:</strong> {{.Ingredients}}</p>
		<p><strong>Instructions:</strong> {{.Instructions}}</p>
		<p><strong>Average Rating:</strong> {{.Avg}}</p>
		<h3>Comments</h3>
		<ul>{{range .Comments}}<li>{{.}}</li>{{end}}</ul>
		<a href="/recipes">Back to list</a>
	</body></html>`
	
	t, _ := template.New("recipe").Parse(tmpl)
	w.Header().Set("Content-Type", "text/html")
	t.Execute(w, map[string]interface{}{
		"Title":       title,
		"Ingredients": ingreds,
		"Instructions": instructions,
		"Avg":         fmt.Sprintf("%.2f", avg),
		"Comments":    comments,
	})
}

func handleAddComment(w http.ResponseWriter, r *http.Request, recipeID string) {
	var req CommentRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "Invalid input", http.StatusBadRequest)
		return
	}

	var exists int
	db.QueryRow("SELECT 1 FROM recipes WHERE id = ?", recipeID).Scan(&exists)
	if exists == 0 {
		http.Error(w, "Recipe not found", http.StatusNotFound)
		return
	}

	_, err := db.Exec("INSERT INTO comments (recipe_id, content) VALUES (?, ?)", recipeID, req.Comment)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	w.WriteHeader(http.StatusCreated)
}

func handleAddRating(w http.ResponseWriter, r *http.Request, recipeID string) {
	var req RatingRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "Invalid input", http.StatusBadRequest)
		return
	}

	if req.Rating < 1 || req.Rating > 5 {
		http.Error(w, "Rating must be between 1 and 5", http.StatusBadRequest)
		return
	}

	var exists int
	db.QueryRow("SELECT 1 FROM recipes WHERE id = ?", recipeID).Scan(&exists)
	if exists == 0 {
		http.Error(w, "Recipe not found", http.StatusNotFound)
		return
	}

	_, err := db.Exec("INSERT INTO ratings (recipe_id, rating) VALUES (?, ?)", recipeID, req.Rating)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	w.WriteHeader(http.StatusCreated)
}