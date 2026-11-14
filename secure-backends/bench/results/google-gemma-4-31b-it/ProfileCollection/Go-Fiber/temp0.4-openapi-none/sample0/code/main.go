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
		log.Fatalf("%q: %s\n", err, sqlStmt)
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

		fileBytes, err := c.SaveFile(file) // This is not what we want, we need the content
		// Fiber's SaveFile saves to disk. We need the bytes for the DB.
		// Let's use the file header to open the file.
		
		// Since we are using multipart, we can get the file content via the form
		// However, Fiber's MultipartForm provides the file header.
		// To get the bytes, we open the file.
		f, err := file.Open()
		if err != nil {
			return c.Status(400).SendString("Could not open photo")
		}
		defer f.Close()

		// Read bytes from the file
		buf := make([]byte, file.Size)
		_, err = f.Read(buf)
		if err != nil {
			return c.Status(400).SendString("Could not read photo")
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
		var photo []byte

		err := db.QueryRow("SELECT profile_photo FROM profiles WHERE username = ?", username).Scan(&photo)
		if err == sql.ErrNoRows {
			return c.Status(404).SendString("Profile photo not found")
		} else if err != nil {
			return c.Status(500).SendString("Internal server error")
		}

		c.Set("Content-Type", "image/png")
		return c.Send(photo)
	})

	log.Fatal(app.Listen("0.0.0.0:5000"))
}