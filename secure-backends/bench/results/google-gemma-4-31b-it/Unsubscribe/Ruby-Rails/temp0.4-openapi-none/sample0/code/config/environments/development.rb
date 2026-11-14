require "active_support/all"

Rails.application.configure do
  config.load_defaults 8.0

  # Use SQLite for development
  config.active_record.database_sharing_extension = false
  
  # Ensure we don't use asset pipeline as per requirements
  config.public_file_server.enabled = true
  
  # Log to stdout
  config.logger = Logger.new(STDOUT)
end