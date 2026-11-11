require " concentrates/development"

Rails.application.configure do
  # Set default ActiveRecord adapter to SQLite3
  config.active_record.adapter = "sqlite3"

  # Keep all logs for debugging
  config.log_level = :debug

  # Disable asset pipeline as requested
  config.public_file_server.enabled = true
end