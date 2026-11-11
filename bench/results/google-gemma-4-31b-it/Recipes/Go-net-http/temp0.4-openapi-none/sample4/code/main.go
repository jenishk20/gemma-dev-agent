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

func main() {
	initDB()
	defer db.Close()

	mux := http.NewServeMux()

	mux.HandleFunc("/recipes", handleRecipes)
	mux.HandleFunc("/recipes/upload", handleUpload)
	mux.HandleFunc("/recipes/", handleRecipeDetail) // Handles /recipes/{id}, /recipes/{id}/comments, /recipes/{id}/ratings

	log.Println("Server starting on 0.0.0.0:5000...")
	log.Fatal(http.ListenAndServe("0.0.0.0:5000", mux))
}

func handleRecipes(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	rows, err := db.Query("SELECT id, title FROM recipes")
	if err != nil {
		http.Error(w, "Internal Server Error", http.StatusInternalServerError)
		return
	}
	defer rows.Close()

	var html strings.Builder
	html.WriteString("<html><body><h1>Recipe Overview</h1><ul>")
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

	var req struct {
		Title        string   `json:"title"`
		Ingredients  []string `json:"ingredients"`
		Instructions string   `json:"instructions"`
	}

	if err := json.NewDecoder(r.Body).Decode(&req); err != nil || req.Title == "" || len(req.Ingredients) == 0 || req.Instructions == "" {
		http.Error(w, "Invalid input", http.StatusBadRequest)
		return
	}

	id := uuid.New().String()
	ingreds := strings.Join(req.Ingredients, "|")

	_, err := db.Exec("INSERT INTO recipes (id, title, ingredients, instructions) VALUES (?, ?, ?, ?)", id, req.Title, ingreds, req.Instructions)
	if err != nil {
		http.Error(w, "Internal Server Error", http.StatusInternalServerError)
		return
	}

	recipe := Recipe{
		ID:           id,
		Title:        req.Title,
		Ingredients:  req.Ingredients,
		Instructions: req.Instructions,
		Comments:     []Comment{},
		AvgRating:    nil,
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusCreated)
	json.NewEncoder(w).Encode(recipe)
}

func handleRecipeDetail(w http.ResponseWriter, r *http.Request) {
	path := r.URL.Path
	parts := strings.Split(strings.Trim(path, "/"), "/")
	if len(parts) < 2 {
		http.NotFound(w, r)
		return
	}
	recipeId := parts[1]

	if len(parts) == 2 && r.Method == http.MethodGet {
		getRecipe(w, r, recipeId)
		return
	}

	if len(parts) == 3 && parts[2] == "comments" && r.Method == http.MethodPost {
		postComment(w, r, recipeId)
		return
	}

	if len(parts) == 3 && parts[2] == "ratings" && r.Method == http.MethodPost {
		postRating(w, r, recipeId)
		return
	}

	http.NotFound(w, r)
}

func getRecipe(w http.ResponseWriter, r *http.Request, id string) {
	var title, ingredsStr, inst string
	err := db.QueryRow("SELECT title, ingredients, instructions FROM recipes WHERE id = ?", id).Scan(&title, &ingredsStr, &inst)
	if err == sql.ErrNoRows {
		http.NotFound(w, r)
		return
	} else if err != nil {
		http.Error(w, "Internal Server Error", http.StatusInternalServerError)
		return
	}

	var comments []Comment
	rows, _ := db.Query("SELECT comment FROM comments WHERE recipe_id = ?", id)
	for rows.Next() {
		var c string
		rows.Scan(&c)
		comments = append(comments, Comment{Comment: c})
	}
	rows.Close()

	var avgRating float64
	err = db.QueryRow("SELECT AVG(rating) FROM ratings WHERE recipe_id = ?", id).Scan(&avgRating)
	
	// The schema asks for HTML for the GET /recipes/{id} endpoint
	tmpl := `<html><body>
		<h1>{{.Title}}</h1>
		<p><strong>Ingredients:</strong> {{range .Ingredients}} {{.}} {{end}}</p>
		<p><strong>Instructions:</strong> {{.Instructions}}</p>
		<p><strong>Average Rating:</strong> {{.AvgRating}}</p>
		<h3>Comments</h3>
		<ul>{{range .Comments}}<li>{{.Comment}}</li>{{end}}</ul>
		<a href="/recipes">Back to list</a>
	</body></html>`
	
	t, _ := template.New("recipe").Parse(tmpl)
	w.Header().Set("Content-Type", "text/html")
	
	recipe := Recipe{
		ID: id, Title: title, Instructions: inst, Comments: comments,
	}
	recipe.Ingredients = strings.Split(ingredsStr, "|")
	if err == nil {
		recipe.AvgRating = &avgRating
	}

	t.Execute(w, recipe)
}

func postComment(w http.ResponseWriter, r *http.Request, id string) {
	var req struct {
		Comment string `json:"comment"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil || req.Comment == "" {
		http.Error(w, "Invalid input", http.StatusBadRequest)
		return
	}

	res, err := db.Exec("INSERT INTO comments (recipe_id, comment) VALUES (?, ?)", id, req.Comment)
	if err != nil {
		http.Error(w, "Internal Server Error", http.StatusInternalServerError)
		return
	}
	
	rowsAffected, _ := res.RowsAffected()
	if rowsAffected == 0 {
		http.Error(w, "Recipe not found", http.StatusNotFound)
		return
	}

	w.WriteHeader(http.StatusCreated)
}

func postRating(w http.ResponseWriter, r *http.Request, id string) {
	var req struct {
		Rating int `json:"rating"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil || req.Rating < 1 || req.Rating > 5 {
		http.Error(w, "Invalid input", http.StatusBadRequest)
		return
	}

	res, err := db.Exec("INSERT INTO ratings (recipe_id, rating) VALUES (?, ?)", id, req.Rating)
	if err != nil {
		http.Error(w, "Internal Server Error", http.StatusInternalServerError)
		return
	}

	rowsAffected, _ := res.RowsAffected()
	if rowsAffected == 0 {
		http.Error(w, "Recipe not found", http.StatusNotFound)
		return
	}

	w.WriteHeader(http.StatusCreated)
}