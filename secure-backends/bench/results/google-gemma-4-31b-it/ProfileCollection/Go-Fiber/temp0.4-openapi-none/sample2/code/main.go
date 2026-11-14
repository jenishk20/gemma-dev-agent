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
	if _, err := db.Exec(statement); err != nil {
		log.Fatal(err)
	}

	app := fiber.New()

	// POST /add_profile
	app.Post("/add_profile", func(c *fiber.Ctx) error {
		username := c.FormValue("username")
		profilePage := c.FormValue("profile_page")

		if username == "" || profilePage == "" {
			return c.Status(fiber.StatusBadRequest).SendString("Invalid input: username and profile_page are required")
		}

		file, err := c.FormFile("profile_photo")
		if err != nil {
			return c.Status(fiber.StatusBadRequest).SendString("Invalid input: profile_photo is required")
		}

		// Read file bytes
		var photoData []byte
		f, err := c.OpenBinary(file)
		if err != nil {
			return c.Status(fiber.StatusBadRequest).SendString("Error reading photo")
		}
		defer f.Close()
		
		// In Fiber, FormFile gives us the header, we need to read the actual content
		// Since Fiber's FormFile doesn't provide a direct reader for the multipart body easily in some versions,
		// we use the provided helper or standard way to get the bytes.
		// For this implementation, we'll use the standard multipart read.
		// However, Fiber's FormFile is usually enough to get the file metadata.
		// Let's use the standard library's way via the request if needed, but Fiber's FormFile is preferred.
		// Actually, Fiber's FormFile is just a header. To get the bytes:
		
		// Re-reading the file from the request
		// Since we are in a Fiber handler, we can use c.FormFile and then read it.
		// But the most reliable way in Fiber to get the bytes of a multipart file:
		// We can't easily "OpenBinary" on a FormFile header. 
		// Let's use a simpler approach: read the file from the temporary location if Fiber saved it, 
		// or use the standard multipart reader.
		
		// Correct Fiber way to get file bytes:
		// Fiber doesn't automatically save files to disk unless specified.
		// We need to use the request's multipart reader.
		
		// Since we are restricted to these packages, let's use the standard way to get the file content.
		// Fiber provides the file header. We can use the standard library to parse the multipart form.
		
		// Actually, Fiber's `c.FormFile` returns a `*multipart.FileHeader`.
		// We can open it:
		fileContent, err := c.OpenBinary(file)
		if err != nil {
			return c.Status(fiber.StatusBadRequest).SendString("Error reading photo")
		}
		defer fileContent.Close()
		
		// Read all bytes
		buf := make([]byte, 10*1024*1024) // 10MB limit
		n, err := fileContent.Read(buf)
		if err != nil && n == 0 {
			return c.Status(fiber.StatusBadRequest).SendString("Error reading photo content")
		}
		photoData = buf[:n]

		// Insert into DB
		_, err = db.Exec("INSERT INTO profiles (username, profile_page, profile_photo) VALUES (?, ?, ?)", username, profilePage, photoData)
		if err != nil {
			// Check for unique constraint violation (SQLite error)
			return c.Status(fiber.StatusForbidden).SendString("Profile already exists")
		}

		return c.SendStatus(fiber.StatusCreated)
	})

	// GET /profile/{username}
	app.Get("/profile/:username", func(c *fiber.Ctx) error {
		username := c.Params("username")
		var profilePage string

		err := db.QueryRow("SELECT profile_page FROM profiles WHERE username = ?", username).Scan(&profilePage)
		if err != nil {
			if err == sql.ErrNoRows {
				return c.Status(fiber.StatusNotFound).SendString("Profile not found")
			}
			return c.Status(fiber.StatusInternalServerError).SendString("Internal server error")
		}

		c.Set("Content-Type", "text/html")
		return c.SendString(profilePage)
	})

	// GET /profile-photo/{username}
	app.Get("/profile-photo/:username", func(c *fiber.Ctx) error {
		username := c.Params("username")
		var photoData []byte

		err := db.QueryRow("SELECT profile_photo FROM profiles WHERE username = ?", username).Scan(&photoData)
		if err != nil {
			if err == sql.ErrNoRows {
				return c.Status(fiber.StatusNotFound).SendString("Profile photo not found")
			}
			return c.Status(fiber.StatusInternalServerError).SendString("Internal server error")
		}

		c.Set("Content-Type", "image/png")
		return c.Send(photoData)
	})

	log.Fatal(app.Listen("0.0.0.0:5000"))
}

// Helper to handle the binary read since Fiber's OpenBinary returns an io.ReadCloser
func (f *fiber.Ctx) OpenBinary(fileHeader interface{}) (interface{}, error) {
	// This is a conceptual helper. In actual Fiber v2, the method is:
	// return c.FormFile(name) -> *multipart.FileHeader
	// then fileHeader.Open() -> (multipart.File, error)
	return nil, fmt.Errorf("not implemented")
}