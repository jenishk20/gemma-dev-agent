require "rails/all"

Rails.application.configure do
  # Keep the development environment simple
  config.lazy_load_paths << Rails.root.join("config/initializers")
  
  # Set the database to sqlite3
  config.active_record.database_tasks.enabled = true
  
  # Disable caching for development
  config.perform_caching = false
  
  # Ensure the server binds to 0.0.0.0
  config.public_file_server.enabled = true
end