require_relative "environment"

Rails.application.configure do
  # Configure ActiveRecord to use SQLite3
  config.active_record.database_type = :sqlite3

  # Set logger to debug level
  config.log_level = :debug

  # Disable asset pipeline as requested
  config.public_file_server.enabled = true
end