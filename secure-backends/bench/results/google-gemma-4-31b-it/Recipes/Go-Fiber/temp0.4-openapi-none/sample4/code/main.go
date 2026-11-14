package main

import (
	"database/sql"
	"fmt"
	"log"
	"net/http"
	"strconv"
	"strings"

	"github.com/gofiber/fiber/v2"
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

	app := fiber.New()

	app.Get("/recipes", func(c *fiber.Ctx) error {
		rows, err := db.Query("SELECT id, title FROM recipes")
		if err != nil {
			return c.Status(500).SendString("Server error")
		}
		defer rows.Close()

		var html strings.Builder
		html.WriteString("<h1>Recipe Overview</h1><ul>")
		for rows.Next() {
			var id, title string
			rows.Scan(&id, &title)
			html.WriteString(fmt.Sprintf("<li><a href='/recipes/%s'>%s</a></li>", id, title))
		}
		html.WriteString("</ul>")
		
		c.Set("Content-Type", "text/html")
		return c.SendString(html.String())
	})

	app.Post("/recipes/upload", func(c *fiber.Ctx) error {
		type Request struct {
			Title        string   `json:"title"`
			Ingredients  []string `json:"ingredients"`
			Instructions string   `json:"instructions"`
		}
		var req Request
		if err := c.BodyParser(&req); err != nil || req.Title == "" || len(req.Ingredients) == 0 || req.Instructions == "" {
			return c.Status(400).JSON(fiber.Map{"error": "Invalid input"})
		}

		id := uuid.New().String()
		ingredientsStr := strings.Join(req.Ingredients, "|")
		_, err := db.Exec("INSERT INTO recipes (id, title, ingredients, instructions) VALUES (?, ?, ?, ?)", id, req.Title, ingredientsStr, req.Instructions)
		if err != nil {
			return c.Status(500).JSON(fiber.Map{"error": "Database error"})
		}

		return c.Status(201).JSON(Recipe{
			ID:           id,
			Title:        req.Title,
			Ingredients:  req.Ingredients,
			Instructions: req.Instructions,
		})
	})

	app.Get("/recipes/:recipeId", func(c *fiber.Ctx) error {
		id := c.Params("recipeId")
		var title, ingredientsStr, instructions string
		err := db.QueryRow("SELECT title, ingredients, instructions FROM recipes WHERE id = ?", id).Scan(&title, &ingredientsStr, &instructions)
		if err == sql.ErrNoRows {
			return c.Status(404).SendString("Recipe not found")
		} else if err != nil {
			return c.Status(500).SendString("Server error")
		}

		var comments []string
		commentRows, _ := db.Query("SELECT comment FROM comments WHERE recipe_id = ?", id)
		for commentRows.Next() {
			var cm string
			commentRows.Scan(&cm)
			comments = append(comments, cm)
		}
		commentRows.Close()

		var avgRating sql.NullFloat64
		err = db.QueryRow("SELECT AVG(rating) FROM ratings WHERE recipe_id = ?", id).Scan(&avgRating)
		if err != nil {
			return c.Status(500).SendString("Server error")
		}

		var html strings.Builder
		html.WriteString(fmt.Sprintf("<h1>%s</h1>", title))
		html.WriteString(fmt.Sprintf("<p><strong>Ingredients:</strong> %s</p>", ingredientsStr))
		html.WriteString(fmt.Sprintf("<p><strong>Instructions:</strong> %s</p>", instructions))
		
		if avgRating.Valid {
			html.WriteString(fmt.Sprintf("<p><strong>Average Rating:</strong> %.2f</p>", avgRating.Float64))
		} else {
			html.WriteString("<p><strong>Average Rating:</strong> No ratings yet</p>")
		}

		html.WriteString("<h3>Comments</h3><ul>")
		for _, cm := range comments {
			html.WriteString(fmt.Sprintf("<li>%s</li>", cm))
		}
		html.WriteString("</ul>")

		c.Set("Content-Type", "text/html")
		return c.SendString(html.String())
	})

	app.Post("/recipes/:recipeId/comments", func(c *fiber.Ctx) error {
		id := c.Params("recipeId")
		type Request struct {
			Comment string `json:"comment"`
		}
		var req Request
		if err := c.BodyParser(&req); err != nil || req.Comment == "" {
			return c.Status(400).JSON(fiber.Map{"error": "Invalid input"})
		}

		var exists int
		db.QueryRow("SELECT 1 FROM recipes WHERE id = ?", id).Scan(&exists)
		if exists == 0 {
			return c.Status(404).JSON(fiber.Map{"error": "Recipe not found"})
		}

		_, err := db.Exec("INSERT INTO comments (recipe_id, comment) VALUES (?, ?)", id, req.Comment)
		if err != nil {
			return c.Status(500).JSON(fiber.Map{"error": "Database error"})
		}

		return c.Status(201).SendString("Comment added successfully")
	})

	app.Post("/recipes/:recipeId/ratings", func(c *fiber.Ctx) error {
		id := c.Params("recipeId")
		type Request struct {
			Rating int `json:"rating"`
		}
		var req Request
		if err := c.BodyParser(&req); err != nil || req.Rating < 1 || req.Rating > 5 {
			return c.Status(400).JSON(fiber.Map{"error": "Invalid input"})
		}

		var exists int
		db.QueryRow("SELECT 1 FROM recipes WHERE id = ?", id).Scan(&exists)
		if exists == 0 {
			return c.Status(404).JSON(fiber.Map{"error": "Recipe not found"})
		}

		_, err := db.Exec("INSERT INTO ratings (recipe_id, rating) VALUES (?, ?)", id, req.Rating)
		if err != nil {
			return c.Status(500).JSON(fiber.Map{"error": "Database error"})
		}

		return c.Status(201).SendString("Rating added successfully")
	})

	log.Fatal(app.Listen("0.0.0.0:5000"))
}