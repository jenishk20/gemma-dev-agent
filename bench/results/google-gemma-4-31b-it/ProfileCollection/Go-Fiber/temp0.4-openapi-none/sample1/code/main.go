package main

import (
	"database/sql"
	"fmt"
	"log"
	"net/http"

	"github.com/gofiber/fiber/v2"
	_ "github.com/mattn/go-sqlite3"
)

func main() {
	// Initialize SQLite database
	db, err := sql.Open("sqlite3", "./db.sqlite3")
	if err != nil {
		log.Fatal(err)
	}
	defer db.Close()

	// Create table for profiles
	statement := `CREATE TABLE IF NOT EXISTS profiles (
		username TEXT PRIMARY KEY, 
		profile_page TEXT, 
		profile_photo BLOB
	);`
	_, err = db.Exec(statement)
	if err != nil {
		log.Fatal(err)
	}

	app := fiber.New()

	// POST /add_profile: Add a new user profile
	app.Post("/add_profile", func(c *fiber.Ctx) error {
		username := c.FormValue("username")
		profilePage := c.FormValue("profile_page")

		if username == "" || profilePage == "" {
			return c.Status(fiber.StatusBadRequest).SendString("Invalid input: username and profile_page are required")
		}

		// Handle file upload for profile_photo
		file, err := c.FormFile("profile_photo")
		if err != nil {
			return c.Status(fiber.StatusBadRequest).SendString("Invalid input: profile_photo is required")
		}

		// Read file bytes
		var photoData []byte
		if file != nil {
			// Fiber's FormFile doesn't provide the bytes directly, we need to open it
			// However, for simplicity in this context, we can use the provided helper or open the temp file
			// In Fiber v2, we can use c.FormFile and then read the file from the local temp path
			// But a more robust way is to use the multipart reader. 
			// For this implementation, we'll use the standard way to read the uploaded file.
			
			// Since we are limited to the provided packages, we use the standard library to read the file
			// Fiber's FormFile returns a *fasthttp.FileHeader. We can't easily read it without fasthttp.
			// Instead, we use the request body directly or the Fiber helper.
			// Actually, Fiber's FormFile is a wrapper. Let's use the correct way to get bytes:
			
			// Note: In Fiber, the easiest way to get the bytes of a file is to use the `SaveFile` 
			// but we need it in the DB. We will read the file from the temporary location.
			// However, Fiber's FormFile is actually a pointer to a fasthttp.FileHeader.
			// To get the bytes, we can use the following:
			
			// Because we are restricted to the provided packages and Fiber, 
			// we use the standard multipart form parsing if needed, but Fiber provides 
			// a way to get the file. Let's use the `c.FormFile` and then read the content.
			
			// Correction: Fiber's FormFile is a fasthttp.FileHeader. 
			// To get the content, we can use the `Open` method.
			f, err := file.Open()
			if err != nil {
				return c.Status(fiber.StatusBadRequest).SendString("Error reading file")
			}
			defer f.Close()
			
			// Read all bytes
			buf := make([]byte, 10*1024*1024) // 10MB limit
			n, err := f.Read(buf)
			if err != nil && n == 0 {
				return c.Status(fiber.StatusBadRequest).SendString("Error reading file content")
			}
			photoData = buf[:n]
		}

		// Insert into DB
		_, err = db.Exec("INSERT INTO profiles (username, profile_page, profile_photo) VALUES (?, ?, ?)", username, profilePage, photoData)
		if err != nil {
			// Check for unique constraint violation (SQLite error)
			return c.Status(fiber.StatusForbidden).SendString("Profile already exists, creation forbidden")
		}

		return c.Status(fiber.StatusCreated).SendString("Profile created successfully")
	})

	// GET /profile/{username}: Get user profile HTML
	app.Get("/profile/:username", func(c *fiber.Ctx) error {
		username := c.Params("username")
		var profilePage string

		err := db.QueryRow("SELECT profile_page FROM profiles WHERE username = ?", username).Scan(&profilePage)
		if err == sql.ErrNoRows {
			return c.Status(fiber.StatusNotFound).SendString("Profile not found")
		} else if err != nil {
			return c.Status(fiber.StatusInternalServerError).SendString("Internal Server Error")
		}

		c.Set("Content-Type", "text/html")
		return c.SendString(profilePage)
	})

	// GET /profile-photo/{username}: Get user profile photo PNG
	app.Get("/profile-photo/:username", func(c *fiber.Ctx) error {
		username := c.Params("username")
		var photoData []byte

		err := db.QueryRow("SELECT profile_photo FROM profiles WHERE username = ?", username).Scan(&photoData)
		if err == sql.ErrNoRows {
			return c.Status(fiber.StatusNotFound).SendString("Profile photo not found")
		} else if err != nil {
			return c.Status(fiber.StatusInternalServerError).SendString("Internal Server Error")
		}

		c.Set("Content-Type", "image/png")
		return c.Send(photoData)
	})

	log.Fatal(app.Listen("0.0.0.0:5000"))
}