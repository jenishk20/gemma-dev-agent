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

		// Read file bytes
		f, err := file.Open()
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Could not open file"})
			return
		}
		defer f.Close()

		var photoData []byte
		buf := make([]byte, file.Size)
		_, err = f.Read(buf)
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Could not read file"})
			return
		}
		photoData = buf

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
			c.JSON(http.StatusNotFound, gin.H{"error": "Profile photo not found"})
			return
		} else if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Database error"})
			return
		}

		c.Header("Content-Type", "image/png")
		c.Data(http.StatusOK, "image/png", photoData)
	})

	fmt.Println("Server starting on 0.0.0.0:5000")
	r.Run("0.0.0.0:5000")
}