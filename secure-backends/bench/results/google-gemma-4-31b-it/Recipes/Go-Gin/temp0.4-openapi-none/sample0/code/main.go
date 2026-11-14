package main

import (
	"database/sql"
	"fmt"
	"log"
	"net/http"
	"strings"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	_ "github.com/mattn/go-sqlite3"
)

// Models
type Recipe struct {
	ID           string    `json:"id"`
	Title        string    `json:"title"`
	Ingredients  []string `json:"ingredients"`
	Instructions string    `json:"instructions"`
	Comments     []Comment `json:"comments"`
	AvgRating    float64  `json:"avgRating"`
}

type Comment struct {
	Comment string `json:"comment"`
}

type RatingRequest struct {
	Rating int `json:"rating" binding:"required,min=1,max=5"`
}

type CommentRequest struct {
	Comment string `json:"comment" binding:"required"`
}

type UploadRequest struct {
	Title        string   `json:"title" binding:"required"`
	Ingredients  []string `json:"ingredients" binding:"required"`
	Instructions string   `json:"instructions" binding:"required"`
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
	);`
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
		c.Header("Content-Type", "text/html")
		c.String(http.StatusOK, html.String())
	})

	r.POST("/recipes/upload", func(c *gin.Context) {
		var req UploadRequest
		if err := c.ShouldBindJSON(&req); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid input"})
			return
		}

		id := uuid.New().String()
		ingredientsStr := strings.Join(req.Ingredients, ",")
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
			Comments:     []Comment{},
			AvgRating:    0,
		})
	})

	r.GET("/recipes/:recipeId", func(c *gin.Context) {
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
		rowsC, _ := db.Query("SELECT comment FROM comments WHERE recipe_id = ?", id)
		for rowsC.Next() {
			var comm string
			rowsC.Scan(&comm)
			comments = append(comments, comm)
		}
		rowsC.Close()

		var avgRating float64
		err = db.QueryRow("SELECT AVG(rating) FROM ratings WHERE recipe_id = ?", id).Scan(&avgRating)
		if err != nil {
			avgRating = 0
		}

		var html strings.Builder
		html.WriteString("<html><body>")
		html.WriteString(fmt.Sprintf("<h1>%s</h1>", title))
		html.WriteString(fmt.Sprintf("<p><strong>Ingredients:</strong> %s</p>", ingredientsStr))
		html.WriteString(fmt.Sprintf("<p><strong>Instructions:</strong> %s</p>", instructions))
		html.WriteString(fmt.Sprintf("<p><strong>Average Rating:</strong> %.2f</p>", avgRating))
		html.WriteString("<h3>Comments</h3><ul>")
		for _, comm := range comments {
			html.WriteString(fmt.Sprintf("<li>%s</li>", comm))
		}
		html.WriteString("</ul><a href='/recipes'>Back</a></body></html>")

		c.Header("Content-Type", "text/html")
		c.String(http.StatusOK, html.String())
	})

	r.POST("/recipes/:recipeId/comments", func(c *gin.Context) {
		id := c.Param("recipeId")
		var req CommentRequest
		if err := c.ShouldBindJSON(&req); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid input"})
			return
		}

		var exists int
		db.QueryRow("SELECT 1 FROM recipes WHERE id = ?", id).Scan(&exists)
		if exists == 0 {
			c.JSON(http.StatusNotFound, gin.H{"error": "Recipe not found"})
			return
		}

		_, err := db.Exec("INSERT INTO comments (recipe_id, comment) VALUES (?, ?)", id, req.Comment)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to save comment"})
			return
		}
		c.Status(http.StatusCreated)
	})

	r.POST("/recipes/:recipeId/ratings", func(c *gin.Context) {
		id := c.Param("recipeId")
		var req RatingRequest
		if err := c.ShouldBindJSON(&req); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid input"})
			return
		}

		var exists int
		db.QueryRow("SELECT 1 FROM recipes WHERE id = ?", id).Scan(&exists)
		if exists == 0 {
			c.JSON(http.StatusNotFound, gin.H{"error": "Recipe not found"})
			return
		}

		_, err := db.Exec("INSERT INTO ratings (recipe_id, rating) VALUES (?, ?)", id, req.Rating)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to save rating"})
			return
		}
		c.Status(http.StatusCreated)
	})

	r.Run("0.0.0.0:5000")
}