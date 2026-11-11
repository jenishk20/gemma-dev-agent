package main

import (
	"database/sql"
	"log"
	"net/http"
	"os"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	_ "github.com/mattn/go-sqlite3"
	"golang.org/x/crypto/bcrypt"
)

type InviteRequest struct {
	Email string `json:"email" binding:"required,email"`
}

type InviteResponse struct {
	InviteID string `json:"invite_id"`
	Message  string `json:"message"`
}

type CreateUserRequest struct {
	InviteID string `json:"invite_id" binding:"required"`
	UserName string `json:"user_name" binding:"required"`
	Password string `json:"password" binding:"required"`
}

type MessageResponse struct {
	Message string `json:"message"`
}

var db *sql.DB

func initDB() {
	var err error
	db, err = sql.Open("sqlite3", "./db.sqlite3")
	if err != nil {
		log.Fatal(err)
	}

	sqlStmt := `
	CREATE TABLE IF NOT EXISTS invitations (
		id TEXT PRIMARY KEY,
		email TEXT UNIQUE NOT NULL,
		used INTEGER DEFAULT 0
	);
	CREATE TABLE IF NOT EXISTS users (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		username TEXT UNIQUE NOT NULL,
		password TEXT NOT NULL,
		email TEXT NOT NULL
	);`
	_, err = db.Exec(sqlStmt)
	if err != nil {
		log.Fatalf("%v", err)
	}
}

func main() {
	initDB()
	defer db.Close()

	r := gin.Default()

	r.POST("/invite_user", func(c *gin.Context) {
		var req InviteRequest
		if err := c.ShouldBindJSON(&req); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"message": "Invalid request body"})
			return
		}

		var inviteID string
		err := db.QueryRow("SELECT id FROM invitations WHERE email = ?", req.Email).Scan(&inviteID)

		if err == sql.ErrNoRows {
			inviteID = uuid.New().String()
			_, err = db.Exec("INSERT INTO invitations (id, email) VALUES (?, ?)", inviteID, req.Email)
			if err != nil {
				c.JSON(http.StatusInternalServerError, gin.H{"message": "Database error"})
				return
			}
		} else if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"message": "Database error"})
			return
		}

		c.JSON(http.StatusOK, InviteResponse{
			InviteID: inviteID,
			Message:  "Invitation created successfully",
		})
	})

	r.POST("/create_user", func(c *gin.Context) {
		var req CreateUserRequest
		if err := c.ShouldBindJSON(&req); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"message": "Invalid request body"})
			return
		}

		var email string
		var used int
		err := db.QueryRow("SELECT email, used FROM invitations WHERE id = ?", req.InviteID).Scan(&email, &used)
		if err == sql.ErrNoRows {
			c.JSON(http.StatusUnauthorized, MessageResponse{Message: "Invalid invite_id"})
			return
		} else if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"message": "Database error"})
			return
		}

		if used == 1 {
			c.JSON(http.StatusUnauthorized, MessageResponse{Message: "Invitation already used"})
			return
		}

		hashedPassword, err := bcrypt.GenerateFromPassword([]byte(req.Password), bcrypt.DefaultCost)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"message": "Password hashing error"})
			return
		}

		_, err = db.Exec("INSERT INTO users (username, password, email) VALUES (?, ?, ?)", req.UserName, string(hashedPassword), email)
		if err != nil {
			// Check for unique constraint violation on username
			c.JSON(http.StatusBadRequest, MessageResponse{Message: "Username already exists. Try providing different username."})
			return
		}

		_, err = db.Exec("UPDATE invitations SET used = 1 WHERE id = ?", req.InviteID)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"message": "Database error updating invitation"})
			return
		}

		c.JSON(http.StatusOK, MessageResponse{Message: "User created successfully"})
	})

	// APP_SECRET is provided in env as per requirements, though not explicitly needed for these specific endpoints
	_ = os.Getenv("APP_SECRET")

	r.Run("0.0.0.0:5000")
}