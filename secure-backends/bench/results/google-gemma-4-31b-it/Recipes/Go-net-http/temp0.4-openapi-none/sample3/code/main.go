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

	"github.com/google/uuid"
	_ "github.com/mattn/go-sqlite3"
)

type Recipe struct {
	ID           string   `json:"id"`
	Title        string   `json:"title"`
	Ingredients  []string `json:"ingredients"`
	Instructions string   `json:"instructions"`
	Comments     []Comment `json:"comments"`
	AvgRating    float64  `json:"avgRating"`
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

func main() {
	initDB()
	defer db.Close()

	mux := http.NewServeMux()

	mux.HandleFunc("/recipes", handleRecipes)
	mux.HandleFunc("/recipes/upload", handleUpload)
	mux.HandleFunc("/recipes/", handleRecipeDetail) // Handles /recipes/{id}, /recipes/{id}/comments, /recipes/{id}/ratings

	fmt.Println("Server starting on 0.0.0.0:5000...")
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

	var recipes []struct {
		ID    string
		Title string
	}
	for rows.Next() {
		var id, title string
		rows.Scan(&id, &title)
		recipes = append(recipes, struct {
			ID    string
			Title string
		}{id, title})
	}

	w.Header().Set("Content-Type", "text/html")
	tmpl := `<html><body><h1>Recipes</h1><ul>{{range .}}<li><a href="/recipes/{{.ID}}">{{.Title}}</a></li>{{end}}</ul></body></html>`
	t, _ := template.New("webpage").Parse(tmpl)
	t.Execute(w, recipes)
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
	ingrs := strings.Join(rec.Ingredients, "|")

	_, err := db.Exec("INSERT INTO recipes (id, title, ingredients, instructions) VALUES (?, ?, ?, ?)", rec.ID, rec.Title, ingrs, rec.Instructions)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusCreated)
	json.NewEncoder(w).Encode(rec)
}

func handleRecipeDetail(w http.ResponseWriter, r *http.Request) {
	path := strings.TrimPrefix(r.URL.Path, "/recipes/")
	parts := strings.Split(path, "/")
	recipeID := parts[0]

	if recipeID == "" {
		http.NotFound(w, r)
		return
	}

	// Check if it's a sub-resource
	if len(parts) > 1 {
		subResource := parts[1]
		if subResource == "comments" && r.Method == http.MethodPost {
			handleAddComment(w, r, recipeID)
			return
		} else if subResource == "ratings" && r.Method == http.MethodPost {
			handleAddRating(w, r, recipeID)
			return
		}
	}

	if r.Method == http.MethodGet {
		handleGetRecipe(w, r, recipeID)
		return
	}

	http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
}

func handleGetRecipe(w http.ResponseWriter, r *http.Request, id string) {
	var title, ingrsStr, instrs string
	err := db.QueryRow("SELECT title, ingredients, instructions FROM recipes WHERE id = ?", id).Scan(&title, &ingrsStr, &instrs)
	if err == sql.ErrNoRows {
		http.NotFound(w, r)
		return
	} else if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	var comments []string
	rows, _ := db.Query("SELECT comment FROM comments WHERE recipe_id = ?", id)
	for rows.Next() {
		var c string
		rows.Scan(&c)
		comments = append(comments, c)
	}
	rows.Close()

	var avgRating float64
	err = db.QueryRow("SELECT AVG(rating) FROM ratings WHERE recipe_id = ?", id).Scan(&avgRating)
	if err != nil {
		avgRating = 0
	}

	w.Header().Set("Content-Type", "text/html")
	tmpl := `<html><body><h1>{{.Title}}</h1><p><b>Ingredients:</b> {{.Ingrs}}</p><p><b>Instructions:</b> {{.Instrs}}</p><p><b>Rating:</b> {{.Rating}}</p><h3>Comments</h3><ul>{{range .Comments}}<li>{{.}}</li>{{end}}</ul><a href="/recipes">Back</a></body></html>`
	t, _ := template.New("detail").Parse(tmpl)
	t.Execute(w, map[string]interface{}{
		"Title":    title,
		"Ingrs":    strings.ReplaceAll(ingrsStr, "|", ", "),
		"Instrs":   instrs,
		"Rating":   fmt.Sprintf("%.2f", avgRating),
		"Comments": comments,
	})
}

func handleAddComment(w http.ResponseWriter, r *http.Request, id string) {
	var c Comment
	if err := json.NewDecoder(r.Body).Decode(&c); err != nil || c.Comment == "" {
		http.Error(w, "Invalid input", http.StatusBadRequest)
		return
	}

	res, err := db.Exec("INSERT INTO comments (recipe_id, comment) VALUES (?, ?)", id, c.Comment)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	
	rowsAffected, _ := res.RowsAffected()
	if rowsAffected == 0 {
		// Check if recipe exists
		var exists int
		db.QueryRow("SELECT 1 FROM recipes WHERE id = ?", id).Scan(&exists)
		if exists == 0 {
			http.NotFound(w, r)
			return
		}
	}

	w.WriteHeader(http.StatusCreated)
}

func handleAddRating(w http.ResponseWriter, r *http.Request, id string) {
	var req RatingRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil || req.Rating < 1 || req.Rating > 5 {
		http.Error(w, "Invalid input", http.StatusBadRequest)
		return
	}

	res, err := db.Exec("INSERT INTO ratings (recipe_id, rating) VALUES (?, ?)", id, req.Rating)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	rowsAffected, _ := res.RowsAffected()
	if rowsAffected == 0 {
		var exists int
		db.QueryRow("SELECT 1 FROM recipes WHERE id = ?", id).Scan(&exists)
		if exists == 0 {
			http.NotFound(w, r)
			return
		}
	}

	w.WriteHeader(http.StatusCreated)
}