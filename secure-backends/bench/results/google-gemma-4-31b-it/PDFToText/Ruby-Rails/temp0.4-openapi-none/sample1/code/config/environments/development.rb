require_relative "../config/application"

Rails.application.configure do
  # Set ActiveRecord to work with SQLite3 development.sqlite3
  config.active_record.database_selector = { a: :development }
  config.active_record.database_authenticator = { a: :development }

  config.active_record.migration_schedules = { a: :development }

  # Use the database-backed active cache for development
  config.cache_store = :redis_cache_store if ENV["REDIS_URL"].present?
  
  # Disable assets as requested
  config.public_file_server.enabled = true
  
  # Log level
  config.log_level = :debug
end