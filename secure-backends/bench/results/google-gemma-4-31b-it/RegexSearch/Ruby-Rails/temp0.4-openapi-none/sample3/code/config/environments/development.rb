require "active_support/all"

Rails.application.configure do
  # Set all ActiveRecord models to raise an exception on save failures.
  config.active_record.raise_on_save_failure = false

  # Configure Active Record to work with SQLite3
  config.active_record.database_type = :sqlite3

  # Put your application in development mode.
  config.env_file = ".env"
  
  # Ensure the server binds to 0.0.0.0 for container accessibility
  config.public_file_server.enabled = true
end