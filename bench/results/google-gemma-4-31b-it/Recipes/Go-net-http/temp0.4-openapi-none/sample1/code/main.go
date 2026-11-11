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
	"sync"

	_ "github.com/mattn/go-sqlite3"
	"github.com/google/uuid"
)

// Models
type Recipe struct {
	ID           string   `json:"id"`
	Title        string   `json:"title"`
	Ingredients []string `json:"ingredients"`
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

type CommentRequest struct {
	Comment string `json:"comment"`
}

type RecipeUploadRequest struct {
	Title        string   `json:"title"`
	Ingredients []string `json:"ingredients"`
	Instructions string   `json:"instructions"`
}

var db *sql.DB
var mu sync.Mutex

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
	fmt.Fprintf(w, "<h1>Recipe Overview</h1><ul>")
	for _, rec := range recipes {
		fmt.Fprintf(w, "<li><a href='/recipes/%s'>%s</a></li>", rec.ID, rec.Title)
	}
	fmt.Fprintf(w, "</ul>")
}

func handleUpload(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var req RecipeUploadRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "Invalid input", http.StatusBadRequest)
		return
	}

	if req.Title == "" || len(req.Ingredients) == 0 || req.Instructions == "" {
		http.Error(w, "Missing required fields", http.StatusBadRequest)
		return
	}

	id := uuid.New().String()
	ingredientsJSON, _ := json.Marshal(req.Ingredients)

	_, err := db.Exec("INSERT INTO recipes (id, title, ingredients, instructions) VALUES (?, ?, ?, ?)",
		id, req.Title, string(ingredientsJSON), req.Instructions)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	w.WriteHeader(http.StatusCreated)
	json.NewEncoder(w).Encode(Recipe{
		ID:           id,
		Title:        req.Title,
		Ingredients:  req.Ingredients,
		Instructions: req.Instructions,
	})
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
		}
		if action == "ratings" && r.Method == http.MethodPost {
			handleAddRating(w, r, recipeID)
			return
		}
	}

	if r.Method != http.MethodGet {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	// Get Recipe Details
	var title, instructions, ingredientsStr string
	err := db.QueryRow("SELECT title, instructions, ingredients FROM recipes WHERE id = ?", recipeID).Scan(&title, &instructions, &ingredientsStr)
	if err == sql.ErrNoRows {
		http.Error(w, "Recipe not found", http.StatusNotFound)
		return
	} else if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	var ingredients []string
	json.Unmarshal([]byte(ingredientsStr), &ingredients)

	// Get Comments
	rows, _ := db.Query("SELECT comment FROM comments WHERE recipe_id = ?", recipeID)
	var comments []string
	for rows.Next() {
		var c string
		rows.Scan(&c)
		comments = append(comments, c)
	}
	rows.Close()

	// Get Avg Rating
	var avg float64
	db.QueryRow("SELECT AVG(rating) FROM ratings WHERE recipe_id = ?", recipeID).Scan(&avg)

	w.Header().Set("Content-Type", "text/html")
	tmpl := `<h1>{{.Title}}</h1>
	<p><strong>Ingredients:</strong> {{range .Ingredients}} {{.}} {{end}}</p>
	<p><strong>Instructions:</strong> {{.Instructions}}</p>
	<p><strong>Average Rating:</strong> {{.AvgRating}}</p>
	<h3>Comments</h3>
	<ul>{{range .Comments}}<li>{{.}}</li>{{end}}</ul>
	<hr>
	<form action="/recipes/{{.ID}}/ratings" method="POST">
		Rating (1-5): <input type="number" name="rating" min="1" max="5">
		<input type="submit" value="Rate">
	</form>
	<form action="/recipes/{{.ID}}/comments" method="POST">
		Comment: <input type="text" name="comment">
		<input type="submit" value="Comment">
	</form>`
	
	t, _ := template.New("recipe").Parse(tmpl)
	t.Execute(w, map[string]interface{}{
		"ID":           recipeID,
		"Title":        title,
		"Ingredients":  ingredients,
		"Instructions": instructions,
		"Comments":     comments,
		"AvgRating":    avg,
	})
}

func handleAddComment(w http.ResponseWriter, r *http.Request, recipeID string) {
	var req CommentRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		// Try parsing form data if JSON fails (for HTML form support)
		req.Comment = r.FormValue("comment")
	}

	if req.Comment == "" {
		http.Error(w, "Invalid input", http.StatusBadRequest)
		return
	}

	res, err := db.Exec("INSERT INTO comments (recipe_id, comment) VALUES (?, ?)", recipeID, req.Comment)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	
	if rows, _ := res.RowsAffected(); rows == 0 {
		http.Error(w, "Recipe not found", http.StatusNotFound)
		return
	}

	w.WriteHeader(http.StatusCreated)
}

func handleAddRating(w http.ResponseWriter, r *http.Request, recipeID string) {
	var req RatingRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		val := r.FormValue("rating")
		i, err := strconv.Atoi(val)
		if err != nil {
			http.Error(w, "Invalid input", http.StatusBadRequest)
			return
		}
		req.Rating = i
	}

	if req.Rating < 1 || req.Rating > 5 {
		http.Error(w, "Rating must be between 1 and 5", http.StatusBadRequest)
		return
	}

	res, err := db.Exec("INSERT INTO ratings (recipe_id, rating) VALUES (?, ?)", recipeID, req.Rating)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	if rows, _ := res.RowsAffected(); rows == 0 {
		http.Error(w, "Recipe not found", http.StatusNotFound)
		return
	}

	w.WriteHeader(http.StatusCreated)
}