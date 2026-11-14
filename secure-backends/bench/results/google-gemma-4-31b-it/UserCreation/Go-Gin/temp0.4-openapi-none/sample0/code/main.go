package main

import (
	"database/sql"
	"fmt"
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
	CREATE TABLE IF NOT EXISTS invites (
		id TEXT PRIMARY KEY,
		email TEXT UNIQUE NOT NULL,
		used INTEGER DEFAULT 0
	);
	CREATE TABLE IF NOT EXISTS users (
		username TEXT PRIMARY KEY,
		password TEXT NOT NULL,
		email TEXT UNIQUE NOT NULL
	);`
	_, err = db.Exec(sqlStmt)
	if err != nil {
		log.Fatal(err)
	}
}

func handleInviteUser(c *gin.Context) {
	var req InviteRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"message": "Invalid request body"})
		return
	}

	var inviteID string
	err := db.QueryRow("SELECT id FROM invites WHERE email = ?", req.Email).Scan(&inviteID)

	if err == sql.ErrNoRows {
		inviteID = uuid.New().String()
		_, err = db.Exec("INSERT INTO invites (id, email) VALUES (?, ?)", inviteID, req.Email)
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
}

func handleCreateUser(c *gin.Context) {
	var req CreateUserRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"message": "Invalid request body"})
		return
	}

	var email string
	var used int
	err := db.QueryRow("SELECT email, used FROM invites WHERE id = ?", req.InviteID).Scan(&email, &used)
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
		if err.Error() == "UNIQUE constraint failed: users.username" {
			c.JSON(http.StatusBadRequest, MessageResponse{Message: "Username already exists. Try providing different username."})
			return
		}
		c.JSON(http.StatusInternalServerError, gin.H{"message": "Database error"})
		return
	}

	_, err = db.Exec("UPDATE invites SET used = 1 WHERE id = ?", req.InviteID)
	if err != nil {
		log.Printf("Warning: failed to mark invite as used: %v", err)
	}

	c.JSON(http.StatusOK, MessageResponse{Message: "User created successfully"})
}

func main() {
	// APP_SECRET is required by prompt but not used in these specific endpoints
	// as they are public-facing invitation/registration flows.
	_ = os.Getenv("APP_SECRET")

	initDB()
	defer db.Close()

	r := gin.Default()

	r.POST("/invite_user", handleInviteUser)
	r.POST("/create_user", handleCreateUser)

	fmt.Println("Server starting on 0.0.0.0:5000")
	r.Run("0.0.0.0:5000")
}