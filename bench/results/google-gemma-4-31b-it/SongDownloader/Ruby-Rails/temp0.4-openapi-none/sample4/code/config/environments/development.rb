require_relative "../application"

Rails.application.configure do
  # Keep the development environment simple
  config.threshold = 1.day
  config.cache_store = :memory_store
  
  # Disable assets as requested
  config.public_file_server.enabled = true
  
  # Set log level
  config.log_level = :debug
end