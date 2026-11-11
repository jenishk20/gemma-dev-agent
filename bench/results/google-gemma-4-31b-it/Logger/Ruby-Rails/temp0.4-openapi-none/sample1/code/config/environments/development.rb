require "rails/all"

Rails.application.configure do
  config.load_defaults 8.0

  # Use SQLite for development
  config.active_record.database_settings = {
    adapter: "sqlite3",
    database: "db.sqlite3"
  }

  # Ensure we don't use asset pipeline as requested
  config.public_file_server_paths = Dir.glob("#{Rails.root}/public/**/*")
end