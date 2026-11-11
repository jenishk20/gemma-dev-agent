package main

import (
	"database/sql"
	"log"
	"net/http"

	"github.com/gin-gonic/gin"
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

	r := gin.Default()

	r.POST("/add_profile", func(c *gin.Context) {
		username := c.PostForm("username")
		profilePage := c.PostForm("profile_page")

		if username == "" || profilePage == "" {
			c.JSON(http.StatusBadRequest, gin.H{"error": "username and profile_page are required"})
			return
		}

		file, err := c.FormFile("profile_photo")
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "profile_photo is required"})
			return
		}

		// We only need the bytes for the DB, so we open the uploaded file
		// Gin's FormFile provides the header, we need to actually read the content
		// Since we are using multipart/form-data, we can use c.Request.MultipartForm
		form, err := c.MultipartForm()
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "failed to parse multipart form"})
			return
		}

		photoFile := form.File["profile_photo"]
		if len(photoFile) == 0 {
			c.JSON(http.StatusBadRequest, gin.H{"error": "profile_photo is missing"})
			return
		}

		// Read the file content
		f, err := photoFile[0].Open()
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to open photo"})
			return
		}
		defer f.Close()

		// Simple way to read the whole file into a byte slice
		var photoData []byte
		buf := make([]byte, 1024*1024) // 1MB buffer
		for {
			n, err := f.Read(buf)
			if n > 0 {
				photoData = append(photoData, buf[:n]...)
			}
			if err != nil {
				break
			}
		}

		_, err = db.Exec("INSERT INTO profiles (username, profile_page, profile_photo) VALUES (?, ?, ?)", username, profilePage, photoData)
		if err != nil {
			// Check for unique constraint violation (SQLite error)
			c.JSON(http.StatusForbidden, gin.H{"error": "Profile already exists"})
			return
		}

		c.Status(http.StatusCreated)
	})

	r.GET("/profile/:username", func(c *gin.Context) {
		username := c.Param("username")
		var profilePage string

		err := db.QueryRow("SELECT profile_page FROM profiles WHERE username = ?", username).Scan(&profilePage)
		if err == sql.ErrNoRows {
			c.JSON(http.StatusNotFound, gin.H{"error": "Profile not found"})
			return
		} else if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Database error"})
			return
		}

		c.Header("Content-Type", "text/html")
		c.String(http.StatusOK, profilePage)
	})

	r.GET("/profile-photo/:username", func(c *gin.Context) {
		username := c.Param("username")
		var photoData []byte

		err := db.QueryRow("SELECT profile_photo FROM profiles WHERE username = ?", username).Scan(&photoData)
		if err == sql.ErrNoRows {
			c.JSON(http.StatusNotFound, gin.H{"error": "Photo not found"})
			return
		} else if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Database error"})
			return
		}

		c.Header("Content-Type", "image/png")
		c.Data(http.StatusOK, "image/png", photoData)
	})

	r.Run("0.0.0.0:5000")
}