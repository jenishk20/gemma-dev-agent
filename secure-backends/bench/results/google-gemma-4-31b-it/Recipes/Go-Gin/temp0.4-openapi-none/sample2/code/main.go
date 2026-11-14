package main

import (
	"database/sql"
	"fmt"
	"log"
	"net/http"
	"strconv"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	_ "github.com/mattn/go-sqlite3"
)

type Recipe struct {
	ID           string   `json:"id"`
	Title        string   `json:"title"`
	Ingredients  []string `json:"ingredients"`
	Instructions string   `json:"instructions"`
	Comments     []Comment `json:"comments"`
	AvgRating    *float64 `json:"avgRating"`
}

type Comment struct {
	Comment string `json:"comment"`
}

var db *sql.DB

func initDB() {
	var err error
	db, err = sql.Open("sqlite3", "db.sqlite3")
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
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		recipe_id TEXT,
		comment TEXT,
		FOREIGN KEY(recipe_id) REFERENCES recipes(id)
	);
	CREATE TABLE IF NOT EXISTS ratings (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		recipe_id TEXT,
		rating INTEGER,
		FOREIGN KEY(recipe_id) REFERENCES recipes(id)
	);
	`
	_, err = db.Exec(sqlStmt)
	if err != nil {
		log.Fatal(err)
	}
}

func main() {
	initDB()
	defer db.Close()

	r := gin.Default()

	r.GET("/recipes", getRecipesOverview)
	r.POST("/recipes/upload", uploadRecipe)
	r.GET("/recipes/:recipeId", getRecipe)
	r.POST("/recipes/:recipeId/comments", addComment)
	r.POST("/recipes/:recipeId/ratings", addRating)

	r.Run("0.0.0.0:5000")
}

func getRecipesOverview(c *gin.Context) {
	rows, err := db.Query("SELECT id, title FROM recipes")
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Database error"})
		return
	}
	defer rows.Close()

	html := "<h1>Recipe Overview</h1><ul>"
	count := 0
	for rows.Next() {
		var id, title string
		rows.Scan(&id, &title)
		html += fmt.Sprintf("<li><a href='/recipes/%s'>%s</a></li>", id, title)
		count++
	}
	html += "</ul>"

	if count == 0 {
		html = "<h1>No recipes found</h1>"
	}

	c.Header("Content-Type", "text/html")
	c.String(http.StatusOK, html)
}

func uploadRecipe(c *gin.Context) {
	var req struct {
		Title        string   `json:"title" binding:"required"`
		Ingredients  []string `json:"ingredients" binding:"required"`
		Instructions string   `json:"instructions" binding:"required"`
	}

	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid input"})
		return
	}

	id := uuid.New().String()
	ingredientsStr := ""
	for i, ing := range req.Ingredients {
		ingredientsStr += ing
		if i < len(req.Ingredients)-1 {
			ingredientsStr += ","
		}
	}

	_, err := db.Exec("INSERT INTO recipes (id, title, ingredients, instructions) VALUES (?, ?, ?, ?)", id, req.Title, ingredientsStr, req.Instructions)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to save recipe"})
		return
	}

	c.JSON(http.StatusCreated, Recipe{
		ID:           id,
		Title:        req.Title,
		Ingredients:  req.Ingredients,
		Instructions: req.Instructions,
	})
}

func getRecipe(c *gin.Context) {
	id := c.Param("recipeId")
	var title, ingredientsStr, instructions string
	err := db.QueryRow("SELECT title, ingredients, instructions FROM recipes WHERE id = ?", id).Scan(&title, &ingredientsStr, &instructions)
	if err == sql.ErrNoRows {
		c.JSON(http.StatusNotFound, gin.H{"error": "Recipe not found"})
		return
	} else if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Database error"})
		return
	}

	var comments []string
	rows, _ := db.Query("SELECT comment FROM comments WHERE recipe_id = ?", id)
	for rows.Next() {
		var comm string
		rows.Scan(&comm)
		comments = append(comments, comm)
	}
	rows.Close()

	var avgRating float64
	err = db.QueryRow("SELECT AVG(rating) FROM ratings WHERE recipe_id = ?", id).Scan(&avgRating)
	if err != nil {
		avgRating = 0
	}

	html := fmt.Sprintf("<h1>%s</h1><p>%s</p><h3>Ingredients</h3><ul>", title, instructions)
	// Simple split for ingredients
	import "strings" // Note: I must move imports to top, but for this single-file constraint I'll use a helper or fix imports.
}