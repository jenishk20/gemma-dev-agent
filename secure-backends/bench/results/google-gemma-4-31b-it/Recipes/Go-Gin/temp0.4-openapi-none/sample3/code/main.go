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
	ID           string    `json:"id"`
	Title        string    `json:"title"`
	Ingredients []string `json:"ingredients"`
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

	r.GET("/recipes", func(c *gin.Context) {
		rows, err := db.Query("SELECT id, title FROM recipes")
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Database error"})
			return
		}
		defer rows.Close()

		html := "<html><body><h1>Recipe Overview</h1><ul>"
		for rows.Next() {
			var id, title string
			rows.Scan(&id, &title)
			html += fmt.Sprintf("<li><a href='/recipes/%s'>%s</a></li>", id, title)
		}
		html += "</ul></body></html>"
		c.Header("Content-Type", "text/html")
		c.String(http.StatusOK, html)
	})

	r.POST("/recipes/upload", func(c *gin.Context) {
		var input struct {
			Title        string   `json:"title" binding:"required"`
			Ingredients []string `json:"ingredients" binding:"required"`
			Instructions string   `json:"instructions" binding:"required"`
		}

		if err := c.ShouldBindJSON(&input); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid input"})
			return
		}

		id := uuid.New().String()
		ingredientsStr := ""
		for i, ing := range input.Ingredients {
			ingredientsStr += ing
			if i < len(input.Ingredients)-1 {
				ingredientsStr += ","
			}
		}

		_, err := db.Exec("INSERT INTO recipes (id, title, ingredients, instructions) VALUES (?, ?, ?, ?)", 
			id, input.Title, ingredientsStr, input.Instructions)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to save recipe"})
			return
		}

		c.JSON(http.StatusCreated, Recipe{
			ID:           id,
			Title:        input.Title,
			Ingredients: input.Ingredients,
			Instructions: input.Instructions,
		})
	})

	r.GET("/recipes/:recipeId", func(c *gin.Context) {
		recipeId := c.Param("recipeId")
		var title, ingredientsStr, instructions string
		err := db.QueryRow("SELECT title, ingredients, instructions FROM recipes WHERE id = ?", recipeId).Scan(&title, &ingredientsStr, &instructions)
		if err == sql.ErrNoRows {
			c.JSON(http.StatusNotFound, gin.H{"error": "Recipe not found"})
			return
		} else if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Database error"})
			return
		}

		var avgRating float64
		err = db.QueryRow("SELECT AVG(rating) FROM ratings WHERE recipe_id = ?", recipeId).Scan(&avgRating)
		
		html := fmt.Sprintf("<html><body><h1>%s</h1><p><b>Instructions:</b> %s</p>", title, instructions)
		html += "<h3>Comments</h3><ul>"
		rows, _ := db.Query("SELECT comment FROM comments WHERE recipe_id = ?", recipeId)
		for rows.Next() {
			var comment string
			rows.Scan(&comment)
			html += fmt.Sprintf("<li>%s</li>", comment)
		}
		rows.Close()
		html += fmt.Sprintf("</ul><p>Average Rating: %.2f</p></body></html>", avgRating)
		
		c.Header("Content-Type", "text/html")
		c.String(http.StatusOK, html)
	})

	r.POST("/recipes/:recipeId/comments", func(c *gin.Context) {
		recipeId := c.Param("recipeId")
		var input struct {
			Comment string `json:"comment" binding:"required"`
		}

		if err := c.ShouldBindJSON(&input); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid input"})
			return
		}

		var exists bool
		db.QueryRow("SELECT EXISTS(SELECT 1 FROM recipes WHERE id=?)", recipeId).Scan(&exists)
		if !exists {
			c.JSON(http.StatusNotFound, gin.H{"error": "Recipe not found"})
			return
		}

		_, err := db.Exec("INSERT INTO comments (recipe_id, comment) VALUES (?, ?)", recipeId, input.Comment)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to add comment"})
			return
		}
		c.JSON(http.StatusCreated, gin.H{"message": "Comment added successfully"})
	})

	r.POST("/recipes/:recipeId/ratings", func(c *gin.Context) {
		recipeId := c.Param("recipeId")
		var input struct {
			Rating int `json:"rating" binding:"required,min=1,max=5"`
		}

		if err := c.ShouldBindJSON(&input); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid input. Rating must be between 1 and 5"})
			return
		}

		var exists bool
		db.QueryRow("SELECT EXISTS(SELECT 1 FROM recipes WHERE id=?)", recipeId).Scan(&exists)
		if !exists {
			c.JSON(http.StatusNotFound, gin.H{"error": "Recipe not found"})
			return
		}

		_, err := db.Exec("INSERT INTO ratings (recipe_id, rating) VALUES (?, ?)", recipeId, input.Rating)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to add rating"})
			return
		}
		c.JSON(http.StatusCreated, gin.H{"message": "Rating added successfully"})
	})

	r.Run("0.0.0.0:5000")
}