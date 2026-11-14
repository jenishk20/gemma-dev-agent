package main

import (
	"database/sql"
	"fmt"
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
		file, err := c.FormFile("profile_photo")

		if username == "" || profilePage == "" || err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid input"})
			return
		}

		// Read the file bytes
		var photoBytes []byte
		// We open the file to read its content
		f, err := file.Open()
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Could not open image"})
			return
		}
		defer f.Close()

		// In a real app we'd use io.ReadAll, but for simplicity in one file:
		buf := make([]byte, file.Size)
		_, err = f.Read(buf)
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Could not read image"})
			return
		}
		photoBytes = buf

		_, err = db.Exec("INSERT INTO profiles (username, profile_page, profile_photo) VALUES (?, ?, ?)", username, profilePage, photoBytes)
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
		var photoBytes []byte

		err := db.QueryRow("SELECT profile_photo FROM profiles WHERE username = ?", username).Scan(&photoBytes)
		if err == sql.ErrNoRows {
			c.JSON(http.StatusNotFound, gin.H{"error": "Photo not found"})
			return
		} else if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Database error"})
			return
		}

		c.Header("Content-Type", "image/png")
		c.Data(http.StatusOK, "image/png", photoBytes)
	})

	fmt.Println("Server starting on 0.0.0.0:5000")
	r.Run("0.0.0.0:5000")
}