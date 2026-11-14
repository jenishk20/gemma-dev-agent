package main

import (
	"database/sql"
	"fmt"
	"log"

	"github.com/gofiber/fiber/v2"
	_ "github.com/mattn/go-sqlite3"
)

var db *sql.DB

func initDB() {
	var err error
	db, err = sql.Open("sqlite3", "./db.sqlite3")
	if err != nil {
		log.Fatal(err)
	}

	sqlStmt := `
	CREATE TABLE IF NOT EXISTS profiles (
		username TEXT PRIMARY KEY,
		profile_page TEXT,
		profile_photo BLOB
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

	// POST /add_profile
	app.Post("/add_profile", func(c *fiber.Ctx) error {
		form, err := c.MultipartForm()
		if err != nil {
			return c.Status(400).SendString("Invalid input")
		}

		username := form.Value("username")
		profilePage := form.Value("profile_page")
		if username == "" || profilePage == "" {
			return c.Status(400).SendString("Username and profile_page are required")
		}

		file, err := form.File("profile_photo")
		if err != nil {
			return c.Status(400).SendString("Profile photo is required")
		}

		// Read file bytes
		fileBytes := make([]byte, file.Size)
		_, err = file.Open() // This is just to check if it's openable, we use the Fiber helper
		// In Fiber, we can get the buffer from the file object if we open it
		f, err := file.Open()
		if err != nil {
			return c.Status(400).SendString("Could not read file")
		}
		defer f.Close()
		
		buf := make([]byte, file.Size)
		_, err = f.Read(buf)
		if err != nil {
			return c.Status(400).SendString("Error reading file content")
		}

		_, err = db.Exec("INSERT INTO profiles (username, profile_page, profile_photo) VALUES (?, ?, ?)", username, profilePage, buf)
		if err != nil {
			// Check for unique constraint violation (SQLite error)
			return c.Status(403).SendString("Profile already exists, creation forbidden")
		}

		return c.SendStatus(201)
	})

	// GET /profile/{username}
	app.Get("/profile/:username", func(c *fiber.Ctx) error {
		username := c.Params("username")
		var profilePage string

		err := db.QueryRow("SELECT profile_page FROM profiles WHERE username = ?", username).Scan(&profilePage)
		if err == sql.ErrNoRows {
			return c.Status(404).SendString("Profile not found")
		} else if err != nil {
			return c.Status(500).SendString("Internal server error")
		}

		c.Set("Content-Type", "text/html")
		return c.SendString(profilePage)
	})

	// GET /profile-photo/{username}
	app.Get("/profile-photo/:username", func(c *fiber.Ctx) error {
		username := c.Params("username")
		var profilePhoto []byte

		err := db.QueryRow("SELECT profile_photo FROM profiles WHERE username = ?", username).Scan(&profilePhoto)
		if err == sql.ErrNoRows {
			return c.Status(404).SendString("Profile photo not found")
		} else if err != nil {
			return c.Status(500).SendString("Internal server error")
		}

		c.Set("Content-Type", "image/png")
		return c.Send(profilePhoto)
	})

	log.Fatal(app.Listen("0.0.0.0:5000"))
}