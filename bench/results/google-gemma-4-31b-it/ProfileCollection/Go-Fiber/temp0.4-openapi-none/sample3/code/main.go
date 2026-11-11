package main

import (
	"database/sql"
	"fmt"
	"log"

	"github.com/gofiber/fiber/v2"
	_ "github.com/mattn/go-sqlite3"
)

type Profile struct {
	Username    string
	ProfilePage string
	ProfilePhoto []byte
}

func main() {
	db, err := sql.Open("sqlite3", "./db.sqlite3")
	if err != nil {
		log.Fatal(err)
	}
	defer db.Close()

	// Create table
	statement := `CREATE TABLE IF NOT EXISTS profiles (
		username TEXT PRIMARY KEY, 
		profile_page TEXT, 
		profile_photo BLOB
	);`
	if _, err := db.Exec(statement); err != nil {
		log.Fatal(err)
	}

	app := fiber.New()

	// POST /add_profile
	app.Post("/add_profile", func(c *fiber.Ctx) error {
		form, err := c.MultipartForm()
		if err != nil {
			return c.Status(400).SendString("Invalid input")
		}

		username := form.Value["username"][0]
		profilePage := form.Value["profile_page"][0]
		
		fileHeader, err := form.File("profile_photo")
		if err != nil {
			return c.Status(400).SendString("Profile photo is required")
		}

		file, err := fileHeader.Open()
		if err != nil {
			return c.Status(400).SendString("Could not open photo file")
		}
		defer file.Close()

		// Read file bytes
		buf := make([]byte, fileHeader.Size)
		_, err = file.Read(buf)
		if err != nil {
			return c.Status(400).SendString("Error reading photo")
		}

		// Insert into DB
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
		if err != nil {
			if err == sql.ErrNoRows {
				return c.Status(404).SendString("Profile not found")
			}
			return c.Status(500).SendString("Internal server error")
		}

		c.Set("Content-Type", "text/html")
		return c.SendString(profilePage)
	})

	// GET /profile-photo/{username}
	app.Get("/profile-photo/:username", func(c *fiber.Ctx) error {
		username := c.Params("username")
		var photo []byte

		err := db.QueryRow("SELECT profile_photo FROM profiles WHERE username = ?", username).Scan(&photo)
		if err != nil {
			if err == sql.ErrNoRows {
				return c.Status(404).SendString("Profile photo not found")
			}
			return c.Status(500).SendString("Internal server error")
		}

		c.Set("Content-Type", "image/png")
		return c.Send(photo)
	})

	log.Fatal(app.Listen("0.0.0.0:5000"))
}